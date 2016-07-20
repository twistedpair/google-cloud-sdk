
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
from googlecloudsdk.api_lib.app.runtimes import fingerprinter
from googlecloudsdk.command_lib.app import exceptions as app_exc
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core.console import console_io
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


def _GetDockerfileCreator(info):
  """Returns a function to create a dockerfile if the user doesn't have one.

  Args:
    info: (googlecloudsdk.api_lib.app.yaml_parsing.ServiceYamlInfo)
      The service config.

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


def BuildAndPushDockerImage(project, service, version_id, code_bucket_ref):
  """Builds and pushes a set of docker images.

  Args:
    project: str, The project being deployed to.
    service: ServiceYamlInfo, The parsed service config.
    version_id: The version id to deploy these services under.
    code_bucket_ref: The reference to the GCS bucket where the source will be
      uploaded.

  Returns:
    str, The name of the pushed container image.
  """
  #  Nothing to do if this is not an image based deployment.
  if not service.RequiresImage():
    return None

  dockerfile_creator = _GetDockerfileCreator(service)
  context_creator = context_util.GetSourceContextFilesCreator(
      os.path.dirname(service.file), None)

  log.status.Print(
      'Building and pushing image for service [{service}]'
      .format(service=service.module))

  cleanup_dockerfile = dockerfile_creator()
  cleanup_context = context_creator()
  try:
    image = docker_image.Image(
        dockerfile_dir=os.path.dirname(service.file),
        repo=_GetImageName(project, service.module, version_id),
        nocache=False,
        tag=config.DOCKER_IMAGE_TAG)
    cloud_build.UploadSource(image.dockerfile_dir, code_bucket_ref,
                             image.tagged_repo)
    metrics.CustomTimedEvent(metric_names.CLOUDBUILD_UPLOAD)
    cloud_build.ExecuteCloudBuild(project, code_bucket_ref, image.tagged_repo,
                                  image.tagged_repo)
    metrics.CustomTimedEvent(metric_names.CLOUDBUILD_EXECUTE)
    return image.tagged_repo
  finally:
    cleanup_dockerfile()
    cleanup_context()


def DoPrepareManagedVms(gae_client):
  """Call an API to prepare the for App Engine Flexible."""
  try:
    message = 'If this is your first deployment, this may take a while'
    with console_io.DelayedProgressTracker(message,
                                           _PREPARE_VM_MESSAGE_DELAY):
      # Note: this doesn't actually boot the VM, it just prepares some stuff
      # for the project via an undocumented Admin API.
      gae_client.PrepareVmRuntime()
    log.status.Print()
  except util.RPCError:
    # Any failures due to an unprepared project will be noisy
    log.warn(
        "We couldn't validate that your project is ready to deploy to App "
        'Engine Flexible Environment. If deployment fails, please try again.')


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


DEFAULT_DEPLOYABLE = 'app.yaml'


def EnsureAppYamlForAppDirectory(directory):
  """Ensures that an app.yaml exists or creates it if necessary.

  If the app.yaml exists, just use it.  If it does not exist, attempt to
  fingerprint the directory and create one.  This is an interactive process.
  If this does not raise an error, the app.yaml is guaranteed to exist once this
  is done.

  Args:
    directory: str, The path to the directory to create the app.yaml in.

  Raises:
    NoAppIdentifiedError, If the application type could not be identified, or
        if a yaml file could not be generated based on the state of the source.

  Returns:
    str, The path to the created or existing app.yaml file.
  """
  yaml_path = os.path.join(directory, DEFAULT_DEPLOYABLE)
  if os.path.exists(yaml_path):
    return yaml_path
  console_io.PromptContinue(
      'Deployment to Google App Engine requires an app.yaml file. '
      'This command will run `gcloud beta app gen-config` to generate an '
      'app.yaml file for you in the current directory (if the current '
      'directory does not contain an App Engine service, please answer '
      '"no").', cancel_on_no=True)
  # This indicates we don't have an app.yaml, we do not want to generate
  # docker files (we will do that in a single place later), and that we don't
  # want to persist the dockerfiles.
  params = ext_runtime.Params(appinfo=None, deploy=False, custom=False)
  configurator = fingerprinter.IdentifyDirectory(directory, params=params)
  if configurator is None:
    raise app_exc.NoAppIdentifiedError(
        'Could not identify an app in the current directory.\n\n'
        'Please prepare an app.yaml file for your application manually '
        'and deploy again.')
  configurator.MaybeWriteAppYaml()
  if not os.path.exists(yaml_path):
    raise app_exc.NoAppIdentifiedError(
        'Failed to create an app.yaml for your app.\n\n'
        'Please prepare an app.yaml file for your application manually '
        'and deploy again.')
  return yaml_path
