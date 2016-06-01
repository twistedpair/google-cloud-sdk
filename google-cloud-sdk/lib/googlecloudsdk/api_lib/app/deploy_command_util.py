
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility methods used by the deploy command."""

import os
import re

from gae_ext_runtime import ext_runtime

from googlecloudsdk.api_lib.app import cloud_build
from googlecloudsdk.api_lib.app import docker_image
from googlecloudsdk.api_lib.app import metric_names
from googlecloudsdk.api_lib.app import util
from googlecloudsdk.api_lib.app.images import config
from googlecloudsdk.api_lib.app.images import docker_util
from googlecloudsdk.api_lib.app.runtimes import fingerprinter
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.docker import constants
from googlecloudsdk.core.docker import docker
from googlecloudsdk.third_party.appengine.api import appinfo
from googlecloudsdk.third_party.appengine.tools import context_util

DEFAULT_DOMAIN = 'appspot.com'
DEFAULT_SERVICE = 'default'
ALT_SEPARATOR = '-dot-'
MAX_DNS_LABEL_LENGTH = 63  # http://tools.ietf.org/html/rfc2181#section-11

# Wait this long before displaying an additional message
_PREPARE_VM_MESSAGE_DELAY = 15


class DockerfileError(exceptions.Error):
  """Raised if a Dockerfile was found along with a non-custom runtime."""


class NoDockerfileError(exceptions.Error):
  """No Dockerfile found."""


class UnsatisfiedRequirementsError(exceptions.Error):
  """Raised if we are unable to detect the runtime."""


def _GetDockerfileCreator(info, config_cleanup=None):
  """Returns a function to create a dockerfile if the user doesn't have one.

  Args:
    info: (googlecloudsdk.api_lib.app.yaml_parsing.ServiceYamlInfo)
      The service config.
    config_cleanup: (callable() or None) If a temporary Dockerfile has already
      been created during the course of the deployment, this should be a
      callable that deletes it.

  Raises:
    DockerfileError: Raised if a user supplied a Dockerfile and a non-custom
      runtime.
    NoDockerfileError: Raised if a user didn't supply a Dockerfile and chose a
      custom runtime.
    UnsatisfiedRequirementsError: Raised if the code in the directory doesn't
      satisfy the requirements of the specified runtime type.
  Returns:
    callable(), a function that can be used to create the correct Dockerfile
    later on.
  """
  # Use the path to app.yaml (info.file) to determine the location of the
  # Dockerfile.
  dockerfile_dir = os.path.dirname(info.file)
  dockerfile = os.path.join(dockerfile_dir, 'Dockerfile')

  if config_cleanup:
    # Dockerfile has already been generated. It still needs to be cleaned up.
    # This must be before the other conditions, since it's a special case.
    return lambda: config_cleanup

  if info.runtime != 'custom' and os.path.exists(dockerfile):
    raise DockerfileError(
        'There is a Dockerfile in the current directory, and the runtime field '
        'in {0} is currently set to [runtime: {1}]. To use your Dockerfile to '
        'build a custom runtime, set the runtime field in {0} to '
        '[runtime: custom]. To continue using the [{1}] runtime, please omit '
        'the Dockerfile from this directory.'.format(info.file, info.runtime))

  # If we're "custom" there needs to be a Dockerfile.
  if info.runtime == 'custom':
    if os.path.exists(dockerfile):
      log.info('Using %s found in %s', config.DOCKERFILE, dockerfile_dir)
      def NullGenerator():
        return lambda: None
      return NullGenerator
    else:
      raise NoDockerfileError(
          'You must provide your own Dockerfile when using a custom runtime.  '
          'Otherwise provide a "runtime" field with one of the supported '
          'runtimes.')

  # Check the fingerprinting based code.
  params = ext_runtime.Params(appinfo=info.parsed, deploy=True)
  configurator = fingerprinter.IdentifyDirectory(dockerfile_dir, params)
  if configurator:
    return configurator.GenerateConfigs
  # Then throw an error.
  else:
    raise UnsatisfiedRequirementsError(
        'Your application does not satisfy all of the requirements for a '
        'runtime of type [{0}].  Please correct the errors and try '
        'again.'.format(info.runtime))


def _GetDomainAndDisplayId(project_id):
  """Returns tuple (displayed app id, domain)."""
  l = project_id.split(':')
  if len(l) == 1:
    return l[0], None
  return l[1], l[0]


def _GetImageName(project, service, version):
  """Returns image tag according to App Engine convention."""
  display, domain = _GetDomainAndDisplayId(project)
  return (config.DOCKER_IMAGE_NAME_DOMAIN_FORMAT if domain
          else config.DOCKER_IMAGE_NAME_FORMAT).format(
              display=display, domain=domain, service=service, version=version)


def BuildAndPushDockerImages(service_configs,
                             version_id,
                             cloudbuild_client,
                             storage_client,
                             code_bucket_ref,
                             cli,
                             remote,
                             source_contexts,
                             config_cleanup):
  """Builds and pushes a set of docker images.

  Args:
    service_configs: A map of service name to parsed config.
    version_id: The version id to deploy these services under.
    cloudbuild_client: An instance of the cloudbuild.CloudBuildV1 api client.
    storage_client: An instance of the storage_v1.StorageV1 client.
    code_bucket_ref: The reference to the GCS bucket where the source will be
      uploaded.
    cli: calliope.cli.CLI, The CLI object representing this command line tool.
    remote: Whether the user specified a remote build.
    source_contexts: A list of json-serializable source contexts to place in
      the application directory for each config.
    config_cleanup: (callable() or None) If a temporary Dockerfile has already
      been created during the course of the deployment, this should be a
      callable that deletes it.

  Returns:
    A dictionary mapping services to the name of the pushed container image.
  """
  project = properties.VALUES.core.project.Get(required=True)
  use_cloud_build = properties.VALUES.app.use_cloud_build.GetBool(required=True)

  # Prepare temporary dockerfile creators for all services that need them
  # before doing the heavy lifting so we can fail fast if there are errors.
  services = []
  for (name, info) in service_configs.iteritems():
    if info.RequiresImage():
      context_creator = context_util.GetSourceContextFilesCreator(
          os.path.dirname(info.file), source_contexts)
      services.append((name, info, _GetDockerfileCreator(info, config_cleanup),
                       context_creator))
  if not services:
    # No images need to be built.
    return {}

  log.status.Print('Verifying that Managed VMs are enabled and ready.')

  if use_cloud_build and remote:
    return _BuildImagesWithCloudBuild(project, services, version_id,
                                      code_bucket_ref, cloudbuild_client,
                                      storage_client)

  # Update docker client's credentials.
  for registry_host in constants.ALL_SUPPORTED_REGISTRIES:
    docker.UpdateDockerCredentials(registry_host)
    metrics.CustomTimedEvent(metric_names.DOCKER_UPDATE_CREDENTIALS)

  # Build docker images.
  images = {}
  with docker_util.DockerHost(
      cli, version_id, remote, project) as docker_client:
    # Build and push all images.
    for service, info, ensure_dockerfile, ensure_context in services:
      log.status.Print(
          'Building and pushing image for service [{service}]'
          .format(service=service))
      cleanup_dockerfile = ensure_dockerfile()
      cleanup_context = ensure_context()
      try:
        image_name = _GetImageName(project, service, version_id)
        images[service] = BuildAndPushDockerImage(
            info.file, docker_client, image_name)
      finally:
        cleanup_dockerfile()
        cleanup_context()
  metric_name = (metric_names.DOCKER_REMOTE_BUILD if remote
                 else metric_names.DOCKER_BUILD)
  metrics.CustomTimedEvent(metric_name)
  return images


def _BuildImagesWithCloudBuild(project, services, version_id, code_bucket_ref,
                               cloudbuild_client, storage_client):
  """Build multiple services with Cloud Build."""
  images = {}
  for service, info, ensure_dockerfile, ensure_context in services:
    log.status.Print(
        'Building and pushing image for service [{service}]'
        .format(service=service))
    cleanup_dockerfile = ensure_dockerfile()
    cleanup_context = ensure_context()
    try:
      image = docker_image.Image(
          dockerfile_dir=os.path.dirname(info.file),
          repo=_GetImageName(project, service, version_id),
          nocache=False,
          tag=config.DOCKER_IMAGE_TAG)
      cloud_build.UploadSource(image.dockerfile_dir, code_bucket_ref,
                               image.tagged_repo, storage_client)
      metrics.CustomTimedEvent(metric_names.CLOUDBUILD_UPLOAD)
      cloud_build.ExecuteCloudBuild(project, code_bucket_ref, image.tagged_repo,
                                    image.tagged_repo, cloudbuild_client)
      metrics.CustomTimedEvent(metric_names.CLOUDBUILD_EXECUTE)
      images[service] = image.tagged_repo
    finally:
      cleanup_dockerfile()
      cleanup_context()
  return images


def DoPrepareManagedVms(gae_client):
  """Call an API to prepare the for managed VMs."""
  try:
    message = 'If this is your first deployment, this may take a while'
    with console_io.DelayedProgressTracker(message,
                                           _PREPARE_VM_MESSAGE_DELAY):
      # Note: this doesn't actually boot the VM, it just prepares some stuff
      # for the project via an undocumented Admin API.
      gae_client.PrepareVmRuntime()
    log.status.Print()
  except util.RPCError:
    log.warn('If this is your first deployment, please try again.')
    raise


def BuildAndPushDockerImage(appyaml_path, docker_client, image_name):
  """Builds Docker image and pushes it onto Google Cloud Storage.

  Workflow:
      Connects to Docker daemon.
      Builds user image.
      Pushes an image to GCR.

  Args:
    appyaml_path: str, Path to the app.yaml for the service.
        Dockerfile must be located in the same directory.
    docker_client: docker.Client instance.
    image_name: str, The name to build the image as.

  Returns:
    The name of the pushed image.
  """
  dockerfile_dir = os.path.dirname(appyaml_path)

  image = docker_image.Image(dockerfile_dir=dockerfile_dir, repo=image_name,
                             tag=config.DOCKER_IMAGE_TAG, nocache=False)
  image.Build(docker_client)
  image.Push(docker_client)
  return image.tagged_repo


def UseSsl(handlers):
  """Returns whether the root URL for an application is served over HTTPS.

  More specifically, returns the 'secure' setting of the handler that will serve
  the application. This can be 'always', 'optional', or 'never', depending on
  when the URL is served over HTTPS.

  Will miss a small number of cases, but HTTP is always okay (an HTTP URL to an
  HTTPS-only service will result in a redirect).

  Args:
    handlers: List of googlecloudsdk.third_party.appengine.api.appinfo.URLMap,
    the configured URL handlers for the application
  Returns:
    str, the 'secure' setting of the handler for the root URL.
  """
  for handler in handlers:
    try:
      if re.match(handler.url + '$', '/'):
        return handler.secure
    except re.error:
      # AppEngine uses POSIX Extended regular expressions, which are not 100%
      # compatible with Python's re module.
      pass
  return appinfo.SECURE_HTTP


def GetAppHostname(app_id, service=None, version=None,
                   use_ssl=appinfo.SECURE_HTTP):
  """Returns the hostname of the given version of the deployed app.

  Args:
    app_id: str, project ID.
    service: str, the (optional) service being deployed
    version: str, the deployed version ID (omit to get the default version URL).
    use_ssl: bool, whether to construct an HTTPS URL.
  Returns:
    str. Constructed URL.
  Raises:
    googlecloudsdk.core.exceptions.Error: if an invalid app_id is supplied.
  """
  if not app_id:
    msg = 'Must provide a valid app ID to construct a hostname.'
    raise exceptions.Error(msg)
  version = version or ''
  service = service or ''
  if service == DEFAULT_SERVICE:
    service = ''

  domain = DEFAULT_DOMAIN
  if ':' in app_id:
    domain, app_id = app_id.split(':')

  if service == DEFAULT_SERVICE:
    service = ''

  # Normally, AppEngine URLs are of the form
  # 'http[s]://version.service.app.appspot.com'. However, the SSL certificate
  # for appspot.com is not valid for subdomains of subdomains of appspot.com
  # (e.g. 'https://app.appspot.com/' is okay; 'https://service.app.appspot.com/'
  # is not). To deal with this, AppEngine recognizes URLs like
  # 'http[s]://version-dot-service-dot-app.appspot.com/'.
  #
  # This works well as long as the domain name part constructed in this fashion
  # is less than 63 characters long, as per the DNS spec. If the domain name
  # part is longer than that, we are forced to use the URL with an invalid
  # certificate.
  #
  # We've tried to do the best possible thing in every case here.
  subdomain_parts = filter(bool, [version, service, app_id])
  scheme = 'http'
  if use_ssl == appinfo.SECURE_HTTP:
    subdomain = '.'.join(subdomain_parts)
    scheme = 'http'
  else:
    subdomain = ALT_SEPARATOR.join(subdomain_parts)
    if len(subdomain) <= MAX_DNS_LABEL_LENGTH:
      scheme = 'https'
    else:
      subdomain = '.'.join(subdomain_parts)
      if use_ssl == appinfo.SECURE_HTTP_OR_HTTPS:
        scheme = 'http'
      elif use_ssl == appinfo.SECURE_HTTPS:
        msg = ('Most browsers will reject the SSL certificate for service {0}. '
               'Please verify that the certificate corresponds to the parent '
               'domain of your application when you connect.').format(service)
        log.warn(msg)
        scheme = 'https'

  return '{0}://{1}.{2}'.format(scheme, subdomain, domain)
