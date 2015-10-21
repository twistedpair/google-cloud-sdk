
# Copyright 2013 Google Inc. All Rights Reserved.

"""Utility methods used by the deploy command."""

import os
import re

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.docker import constants
from googlecloudsdk.core.docker import docker

from googlecloudsdk.appengine.lib.external.api import appinfo
from googlecloudsdk.appengine.lib import cloud_build
from googlecloudsdk.appengine.lib import docker_image
from googlecloudsdk.appengine.lib import fingerprinting
from googlecloudsdk.appengine.lib import metric_names
from googlecloudsdk.appengine.lib import util
from googlecloudsdk.appengine.lib.images import config
from googlecloudsdk.appengine.lib.images import docker_util
from googlecloudsdk.appengine.lib.images import util as images_util
from googlecloudsdk.appengine.lib.runtimes import fingerprinter


DEFAULT_DOMAIN = 'appspot.com'
DEFAULT_MODULE = 'default'
DEFAULT_MODULE = 'default'
ALT_SEPARATOR = '-dot-'
MAX_DNS_LABEL_LENGTH = 63  # http://tools.ietf.org/html/rfc2181#section-11

# Wait this long before displaying an additional message
_PREPARE_VM_MESSAGE_DELAY = 15


class DockerfileError(exceptions.Error):
  """Raised if a Dockerfile was found along with a non-custom runtime."""


def _GetDockerfileCreator(info):
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

  # First try the new fingerprinting based code.
  params = fingerprinting.Params(appinfo=info.parsed, deploy=True)
  configurator = fingerprinter.IdentifyDirectory(dockerfile_dir, params)
  if configurator:
    return configurator.GenerateConfigs
  # Then check if the app is runtime: custom
  elif info.runtime == 'custom' and not os.path.exists(dockerfile):
    raise images_util.NoDockerfileError(
        'You must provide your own Dockerfile when using a custom runtime.  '
        'Otherwise provide a "runtime" field with one of the supported '
        'runtimes.')
  # Then check that we can generate a Dockerfile for a non-custom runtime.
  elif info.runtime != 'custom':
    supported_runtimes = images_util.GetAllManagedVMsRuntimes()
    if info.runtime not in supported_runtimes:
      raise images_util.NoDefaultDockerfileError(
          'No default {dockerfile} for runtime [{runtime}] in the SDK. '
          'Use one of the supported runtimes: [{supported}].'.format(
              dockerfile=config.DOCKERFILE,
              runtime=info.runtime,
              supported='|'.join(supported_runtimes)))
  # Finally fall back to the old CopyDockerfile path.
  def CopyDockerfile():
    return images_util.FindOrCopyDockerfile(info.runtime, dockerfile_dir)
  return CopyDockerfile


def _GetDomainAndDisplayId(project_id):
  """Returns tuple (displayed app id, domain)."""
  l = project_id.split(':')
  if len(l) == 1:
    return l[0], None
  return l[1], l[0]


def _GetImageName(project, module, version):
  """Returns image tag according to App Engine convention."""
  display, domain = _GetDomainAndDisplayId(project)
  return (config.DOCKER_IMAGE_NAME_DOMAIN_FORMAT if domain
          else config.DOCKER_IMAGE_NAME_FORMAT).format(
              display=display, domain=domain, module=module, version=version)


def BuildAndPushDockerImages(module_configs, version_id, gae_client,
                             cloudbuild_client, code_bucket, cli, remote):
  """Builds and pushes a set of docker images.

  Args:
    module_configs: A map of module name to parsed config.
    version_id: The version id to deploy these modules under.
    gae_client: An App Engine API client.
    cloudbuild_client: An instance of the cloudbuild.CloudBuildV1 api client.
    code_bucket: The name of the GCS bucket where the source will be uploaded.
    cli: calliope.cli.CLI, The CLI object representing this command line tool.
    remote: Whether the user specified a remote build.

  Returns:
    A dictionary mapping modules to the name of the pushed container image.
  """
  project = properties.VALUES.core.project.Get(required=True)
  use_cloud_build = properties.VALUES.app.use_cloud_build.GetBool()

  # Prepare temporary dockerfile creators for all modules that need them
  # before doing the heavy lifting so we can fail fast if there are errors.
  modules = [
      (name, info, _GetDockerfileCreator(info))
      for (name, info) in module_configs.iteritems()
      if info.RequiresImage()]
  if not modules:
    # No images need to be built.
    return {}

  log.status.Print('Verifying that Managed VMs are enabled and ready.')
  _DoPrepareManagedVms(gae_client)

  if use_cloud_build:
    return _BuildImagesWithCloudBuild(project, modules, version_id,
                                      code_bucket, cloudbuild_client)

  # Update docker client's credentials.
  for registry_host in constants.ALL_SUPPORTED_REGISTRIES:
    docker.UpdateDockerCredentials(registry_host)
    metrics.CustomTimedEvent(metric_names.DOCKER_UPDATE_CREDENTIALS)

  # Build docker images.
  images = {}
  with docker_util.DockerHost(cli, version_id, remote) as docker_client:
    # Build and push all images.
    for module, info, ensure_dockerfile in modules:
      log.status.Print(
          'Building and pushing image for module [{module}]'
          .format(module=module))
      cleanup = ensure_dockerfile()
      try:
        image_name = _GetImageName(project, module, version_id)
        images[module] = BuildAndPushDockerImage(
            info.file, docker_client, image_name)
      finally:
        cleanup()
  metric_name = (metric_names.DOCKER_REMOTE_BUILD if remote
                 else metric_names.DOCKER_BUILD)
  metrics.CustomTimedEvent(metric_name)
  return images


def _DoPrepareManagedVms(gae_client):
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


def _BuildImagesWithCloudBuild(project, modules, version_id, code_bucket,
                               cloudbuild_client):
  """Build multiple modules with Cloud Build."""
  images = {}
  for module, info, ensure_dockerfile in modules:
    log.status.Print(
        'Building and pushing image for module [{module}]'
        .format(module=module))
    cleanup = ensure_dockerfile()
    try:
      image = docker_image.Image(
          dockerfile_dir=os.path.dirname(info.file),
          tag=_GetImageName(project, module, version_id),
          nocache=False)
      source_gcs_uri = '/'.join([code_bucket.rstrip('/'), image.tag])
      cloud_build.UploadSource(image.dockerfile_dir, source_gcs_uri)
      metrics.CustomTimedEvent(metric_names.CLOUDBUILD_UPLOAD)
      cloud_build.ExecuteCloudBuild(project, source_gcs_uri, image.repo_tag,
                                    cloudbuild_client)
      metrics.CustomTimedEvent(metric_names.CLOUDBUILD_EXECUTE)
      images[module] = image.repo_tag
    finally:
      cleanup()
  return images


def _DoPrepareManagedVms(gae_client):
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
    appyaml_path: str, Path to the app.yaml for the module.
        Dockerfile must be located in the same directory.
    docker_client: docker.Client instance.
    image_name: str, The name to build the image as.

  Returns:
    The name of the pushed image.
  """
  dockerfile_dir = os.path.dirname(appyaml_path)

  image = docker_image.Image(dockerfile_dir=dockerfile_dir, tag=image_name,
                             nocache=False)
  image.Build(docker_client)
  image.Push(docker_client)
  return image.repo_tag


def UseSsl(handlers):
  for handler in handlers:
    try:
      if re.match(handler.url + '$', '/'):
        return handler.secure
    except re.error:
      # AppEngine uses POSIX Extended regular expressions, which are not 100%
      # compatible with Python's re module.
      pass
  return appinfo.SECURE_HTTP


def GetAppHostname(app_id, module=None, version=None,
                   use_ssl=appinfo.SECURE_HTTP):
  if not app_id:
    msg = 'Must provide a valid app ID to construct a hostname.'
    raise exceptions.Error(msg)
  version = version or ''
  module = module or ''
  if module == DEFAULT_MODULE:
    module = ''

  domain = DEFAULT_DOMAIN
  if ':' in app_id:
    domain, app_id = app_id.split(':')

  if module == DEFAULT_MODULE:
    module = ''

  # Normally, AppEngine URLs are of the form
  # 'http[s]://version.module.app.appspot.com'. However, the SSL certificate for
  # appspot.com is not valid for subdomains of subdomains of appspot.com (e.g.
  # 'https://app.appspot.com/' is okay; 'https://module.app.appspot.com/' is
  # not). To deal with this, AppEngine recognizes URLs like
  # 'http[s]://version-dot-module-dot-app.appspot.com/'.
  #
  # This works well as long as the domain name part constructed in this fashion
  # is less than 63 characters long, as per the DNS spec. If the domain name
  # part is longer than that, we are forced to use the URL with an invalid
  # certificate.
  #
  # We've tried to do the best possible thing in every case here.
  subdomain_parts = filter(bool, [version, module, app_id])
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
        msg = ('Most browsers will reject the SSL certificate for module {0}. '
               'Please verify that the certificate corresponds to the parent '
               'domain of your application when you connect.').format(module)
        log.warn(msg)
        scheme = 'https'

  return '{0}://{1}.{2}'.format(scheme, subdomain, domain)


CHANGING_PROMOTION_BEHAVIOR_WARNING = """\
Soon, deployments will set the deployed version to receive all traffic by
default.

To keep the current behavior (where new deployments do not receive any traffic),
use the `--no-promote` flag or run the following command:

  $ gcloud config set app/promote_by_default false

To adopt the new behavior early, use the `--promote` flag or run the following
command:

  $ gcloud config set app/promote_by_default true

Either passing one of the new flags or setting one of these properties will
silence this message.
"""


def GetPromoteFromArgs(args):
  """Returns whether to promote deployment, based on environment and arguments.

  Whether to promote is determined based on the following (in decreasing
  precedence order):
  1. if a command-line flag is set
  2. if the `promote_by_default` property is set
  3. the default: False (for now)

  Issues appropriate warnings:
  * if the user gives no indication of having seen the warning (i.e. no
    `--[no-]promote` flag and no `promote_by_default` property set, issue a
    comprehensive warning about changes coming and what to do about it.
  * if the user uses the `--set-default` flag, warn that it is deprecated.

  Args:
    args: the parsed command-line arguments for the command invocation.

  Returns:
    bool, whether to promote the deployment
  """
  promote_by_default = properties.VALUES.app.promote_by_default.GetBool()

  # Always issue applicable warnings
  if args.set_default:
    log.warn('The `--set-default` flag is deprecated. Please use the '
             '`--promote` flag instead.')
  if args.promote is None and promote_by_default is None:
    log.warn(CHANGING_PROMOTION_BEHAVIOR_WARNING)

  # 1. Check command-line flags
  if args.promote or args.set_default:
    return True
  elif args.promote is False:
    return False

  # 2. Check `promote_by_default` property
  if promote_by_default:
    return True
  if promote_by_default is False:
    return False

  # 3. Default value
  return False


def GetStopPreviousVersionFromArgs(args):
  """Returns whether to stop previous version, based on environment/arguments.

  Whether to stop is determined based on the following (in decreasing
  precedence order):
  1. if a command-line flag is set
  2. if the `stop_previous_version` property is set
  3. the default: True

  Issues appropriate warnings:
  * if the user gives no indication of having seen the warning (i.e. no
    `--[no-]stop_previous_version` flag and no `stop_previous_version` property
    set, issue a comprehensive warning about changes coming and what to do about
    it.

  Args:
    args: the parsed command-line arguments for the command invocation.

  Returns:
    bool, whether to promote the deployment
  """
  # 1. Check command-line flags
  stop_previous_version = properties.VALUES.app.stop_previous_version.GetBool()
  if args.stop_previous_version is not None:
    return args.stop_previous_version

  # 2. Check `stop_previous_version` property
  if stop_previous_version is not None:
    return stop_previous_version

  # 3. Default value
  log.warn('In a future Cloud SDK release, deployments that promote the new '
           'version to receive all traffic will stop the previous version by '
           'default.\n\n'
           'To keep the current behavior (where deployments do not stop the '
           'previous version, pass the `--no-stop-previous-version` flag, or '
           'run the following command:'
           '\n\n  $ gcloud config set app/stop_previous_version false')
  return True
