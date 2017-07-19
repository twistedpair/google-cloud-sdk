
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

import json
import os
import posixpath
import re

from gae_ext_runtime import ext_runtime

from googlecloudsdk.api_lib.app import appengine_api_client
from googlecloudsdk.api_lib.app import cloud_build
from googlecloudsdk.api_lib.app import docker_image
from googlecloudsdk.api_lib.app import metric_names
from googlecloudsdk.api_lib.app import runtime_builders
from googlecloudsdk.api_lib.app import util
from googlecloudsdk.api_lib.app.appinfo import appinfo
from googlecloudsdk.api_lib.app.images import config
from googlecloudsdk.api_lib.app.runtimes import fingerprinter
from googlecloudsdk.api_lib.cloudbuild import build as cloudbuild_build
from googlecloudsdk.api_lib.service_management import enable_api
from googlecloudsdk.api_lib.service_management import exceptions as sm_exceptions
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.api_lib.util import exceptions as api_lib_exceptions
from googlecloudsdk.command_lib.app import exceptions as app_exc
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.credentials import creds
from googlecloudsdk.core.credentials import store as c_store
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms
from googlecloudsdk.third_party.appengine.tools import context_util

DEFAULT_DOMAIN = 'appspot.com'
DEFAULT_SERVICE = 'default'
ALT_SEPARATOR = '-dot-'
MAX_DNS_LABEL_LENGTH = 63  # http://tools.ietf.org/html/rfc2181#section-11

# https://msdn.microsoft.com/en-us/library/windows/desktop/aa365247(v=vs.85).aspx
# Technically, this should be 260 because of the drive, ':\', and a null
# terminator, but any time we're getting close we're in dangerous territory.
_WINDOWS_MAX_PATH = 256


FLEXIBLE_SERVICE_VERIFY_WARNING = (
    'Unable to verify that the Appengine Flexible API is enabled for project '
    '[{}]. You may not have permission to list enabled services on this '
    'project. If it is not enabled, this may cause problems in running your '
    'deployment. Please ask the project owner to ensure that the Appengine '
    'Flexible API has been enabled and that this account has permission to '
    'list enabled APIs.')


FLEXIBLE_SERVICE_VERIFY_WITH_SERVICE_ACCOUNT = (
    'Note: When deploying with a service account, the Service Management API '
    'needs to be enabled in order to verify that the Appengine Flexible API '
    'is enabled. Please ensure the Service Management API has been enabled '
    'on this project by the project owner.')


PREPARE_FAILURE_MSG = (
    'Enabling the Appengine Flexible API failed on project [{}]. You '
    'may not have permission to enable APIs on this project. Please ask '
    'the project owner to enable the Appengine Flexible API on this project.')


class Error(exceptions.Error):
  """Base error for this module."""


class PrepareFailureError(Error):

  def __init__(self, msg):
    super(PrepareFailureError, self).__init__(msg)


class WindowMaxPathError(Error):
  """Raised if a file cannot be read because of the MAX_PATH limitation."""

  _WINDOWS_MAX_PATH_ERROR_TEMPLATE = """\
The following file couldn't be read because its path is too long:

  [{0}]

For more information on this issue and possible workarounds, please read the
following (links are specific to Node.js, but the information is generally
applicable):

* https://github.com/Microsoft/nodejstools/issues/69
* https://github.com/Microsoft/nodejs-guidelines/blob/master/windows-environment.md#max_path-explanation-and-workarounds\
"""

  def __init__(self, filename):
    super(WindowMaxPathError, self).__init__(
        self._WINDOWS_MAX_PATH_ERROR_TEMPLATE.format(filename))


class DockerfileError(exceptions.Error):
  """Raised if a Dockerfile was found along with a non-custom runtime."""


class CloudbuildYamlError(exceptions.Error):
  """Raised if a cloudbuild.yaml was found along with a non-custom runtime."""


class CustomRuntimeFilesError(exceptions.Error):
  """Raised if a custom runtime has both a Dockerfile and a cloudbuild.yaml."""


class NoDockerfileError(exceptions.Error):
  """No Dockerfile found."""


class UnsatisfiedRequirementsError(exceptions.Error):
  """Raised if we are unable to detect the runtime."""


def _NeedsDockerfile(info, source_dir):
  """Returns True if the given directory needs a Dockerfile for this app.

  A Dockerfile is necessary when there is no Dockerfile in source_dir,
  regardless of whether we generate it here on the client-side, or in Cloud
  Container Builder server-side.

  The reason this function is more complicated than that is that it additionally
  verifies the sanity of the provided configuration by raising an exception if:

  - The runtime is "custom", but no Dockerfile is present
  - The runtime is not "custom", and a Dockerfile or cloudbuild.yaml is present
  - The runtime is "custom", and has both a cloudbuild.yaml and a Dockerfile.

  (The reason cloudbuild.yaml is tied into this method is that its use should be
  mutually exclusive with the Dockerfile.)

  Args:
    info: (googlecloudsdk.api_lib.app.yaml_parsing.ServiceYamlInfo). The
      configuration for the service.
    source_dir: str, the path to the service's source directory

  Raises:
    CloudbuildYamlError: if a cloudbuild.yaml is present, but the runtime is not
      "custom".
    DockerfileError: if a Dockerfile is present, but the runtime is not
      "custom".
    NoDockerfileError: Raised if a user didn't supply a Dockerfile and chose a
      custom runtime.
    CustomRuntimeFilesError: if a custom runtime had both a Dockerfile and a
      cloudbuild.yaml file.

  Returns:
    bool, whether Dockerfile generation is necessary.
  """
  has_dockerfile = os.path.exists(
      os.path.join(source_dir, config.DOCKERFILE))
  has_cloudbuild = os.path.exists(
      os.path.join(source_dir, runtime_builders.Resolver.CLOUDBUILD_FILE))
  if info.runtime == 'custom':
    if has_dockerfile and has_cloudbuild:
      raise CustomRuntimeFilesError(
          ('A custom runtime must have exactly one of [{}] and [{}] in the '
           'source directory; [{}] contains both').format(
               config.DOCKERFILE, runtime_builders.Resolver.CLOUDBUILD_FILE,
               source_dir))
    elif has_dockerfile:
      log.info('Using %s found in %s', config.DOCKERFILE, source_dir)
      return False
    elif has_cloudbuild:
      log.info('Not using %s because cloudbuild.yaml was found instead.',
               config.DOCKERFILE)
      return True
    else:
      raise NoDockerfileError(
          'You must provide your own Dockerfile when using a custom runtime. '
          'Otherwise provide a "runtime" field with one of the supported '
          'runtimes.')
  else:
    if has_dockerfile:
      raise DockerfileError(
          'There is a Dockerfile in the current directory, and the runtime '
          'field in {0} is currently set to [runtime: {1}]. To use your '
          'Dockerfile to build a custom runtime, set the runtime field to '
          '[runtime: custom]. To continue using the [{1}] runtime, please '
          'remove the Dockerfile from this directory.'.format(info.file,
                                                              info.runtime))
    elif has_cloudbuild:
      raise CloudbuildYamlError(
          'There is a cloudbuild.yaml in the current directory, and the '
          'runtime field in {0} is currently set to [runtime: {1}]. To use '
          'your cloudbuild.yaml to build a custom runtime, set the runtime '
          'field to [runtime: custom]. To continue using the [{1}] runtime, '
          'please remove the cloudbuild.yaml from this directory.'.format(
              info.file, info.runtime))
    log.info('Need Dockerfile to be generated for runtime %s', info.runtime)
    return True


def _GetDockerfiles(info, dockerfile_dir):
  """Returns map of in-memory Docker-related files to be packaged.

  Returns the files in-memory, so that we don't have to drop them on disk;
  instead, we include them in the archive sent to App Engine directly.

  Args:
    info: (googlecloudsdk.api_lib.app.yaml_parsing.ServiceYamlInfo)
      The service config.
    dockerfile_dir: str, path to the directory to fingerprint and generate
      Dockerfiles for.

  Raises:
    UnsatisfiedRequirementsError: Raised if the code in the directory doesn't
      satisfy the requirements of the specified runtime type.

  Returns:
    A dictionary of filename relative to the archive root (str) to file contents
    (str).
  """
  params = ext_runtime.Params(appinfo=info.parsed, deploy=True)
  configurator = fingerprinter.IdentifyDirectory(dockerfile_dir, params)
  if configurator:
    dockerfiles = configurator.GenerateConfigData()
    return {d.filename: d.contents for d in dockerfiles}
  else:
    raise UnsatisfiedRequirementsError(
        'Your application does not satisfy all of the requirements for a '
        'runtime of type [{0}].  Please correct the errors and try '
        'again.'.format(info.runtime))


def _GetSourceContextsForUpload(source_dir):
  """Gets source context file information.

  Args:
    source_dir: str, path to the service's source directory
  Returns:
    A dict of filename to (str) source context file contents.
  """
  source_contexts = {}
  # Error message in case of failure.
  m = ('Could not generate [{name}]: {error}\n'
       'Stackdriver Debugger may not be configured or enabled on this '
       'application. See https://cloud.google.com/debugger/ for more '
       'information.')
  try:
    contexts = context_util.CalculateExtendedSourceContexts(source_dir)
    source_contexts[context_util.EXT_CONTEXT_FILENAME] = json.dumps(contexts)
  except context_util.GenerateSourceContextError as e:
    log.info(m.format(name=context_util.EXT_CONTEXT_FILENAME, error=e))
    # It's OK if source contexts can't be found, we just stop looking.
    return source_contexts
  try:
    context = context_util.BestSourceContext(contexts)
    source_contexts[context_util.CONTEXT_FILENAME] = json.dumps(context)
  except KeyError as e:
    log.info(m.format(name=context_util.CONTEXT_FILENAME, error=e))
  return source_contexts


def _GetDomainAndDisplayId(project_id):
  """Returns tuple (displayed app id, domain)."""
  l = project_id.split(':')
  if len(l) == 1:
    return l[0], None
  return l[1], l[0]


def _GetImageName(project, service, version, gcr_domain):
  """Returns image tag according to App Engine convention."""
  display, domain = _GetDomainAndDisplayId(project)
  return (config.DOCKER_IMAGE_NAME_DOMAIN_FORMAT if domain
          else config.DOCKER_IMAGE_NAME_FORMAT).format(
              gcr_domain=gcr_domain,
              display=display,
              domain=domain,
              service=service,
              version=version)


def BuildAndPushDockerImage(
    project, service, source_dir, version_id, code_bucket_ref, gcr_domain,
    runtime_builder_strategy=runtime_builders.RuntimeBuilderStrategy.NEVER):
  """Builds and pushes a set of docker images.

  Args:
    project: str, The project being deployed to.
    service: ServiceYamlInfo, The parsed service config.
    source_dir: str, path to the service's source directory
    version_id: The version id to deploy these services under.
    code_bucket_ref: The reference to the GCS bucket where the source will be
      uploaded.
    gcr_domain: str, Cloud Registry domain, determines the physical location
      of the image. E.g. `us.gcr.io`.
    runtime_builder_strategy: runtime_builders.RuntimeBuilderStrategy, whether
      to use the new CloudBuild-based runtime builders (alternative is old
      externalized runtimes).

  Returns:
    str, The name of the pushed container image.

  Raises:
    DockerfileError: if a Dockerfile is present, but the runtime is not
      "custom".
    NoDockerfileError: Raised if a user didn't supply a Dockerfile and chose a
      custom runtime.
    UnsatisfiedRequirementsError: Raised if the code in the directory doesn't
      satisfy the requirements of the specified runtime type.
  """
  needs_dockerfile = _NeedsDockerfile(service, source_dir)
  use_runtime_builders = runtime_builder_strategy.ShouldUseRuntimeBuilders(
      service.runtime, needs_dockerfile)

  # Nothing to do if this is not an image-based deployment.
  if not service.RequiresImage():
    return None
  log.status.Print(
      'Building and pushing image for service [{service}]'
      .format(service=service.module))

  gen_files = dict(_GetSourceContextsForUpload(source_dir))
  if needs_dockerfile and not use_runtime_builders:
    # The runtime builders will generate a Dockerfile in the Cloud, so we only
    # need to do this if use_runtime_builders is True
    gen_files.update(_GetDockerfiles(service, source_dir))

  image = docker_image.Image(
      dockerfile_dir=source_dir,
      repo=_GetImageName(project, service.module, version_id, gcr_domain),
      nocache=False,
      tag=config.DOCKER_IMAGE_TAG)

  metrics.CustomTimedEvent(metric_names.CLOUDBUILD_UPLOAD_START)
  object_ref = storage_util.ObjectReference(code_bucket_ref, image.tagged_repo)

  if files.IsDirAncestorOf(source_dir, service.file):
    relative_yaml_path = os.path.relpath(service.file, source_dir)
  else:
    yaml_contents = files.GetFileContents(service.file)
    checksum = files.Checksum().AddContents(yaml_contents).HexDigest()
    relative_yaml_path = checksum + '.yaml'
    gen_files[relative_yaml_path] = yaml_contents

  try:
    cloud_build.UploadSource(image.dockerfile_dir, object_ref,
                             gen_files=gen_files,
                             skip_files=service.parsed.skip_files.regex)
  except (OSError, IOError) as err:
    if platforms.OperatingSystem.IsWindows():
      if err.filename and len(err.filename) > _WINDOWS_MAX_PATH:
        raise WindowMaxPathError(err.filename)
    raise
  metrics.CustomTimedEvent(metric_names.CLOUDBUILD_UPLOAD)

  if use_runtime_builders:
    builder_reference = runtime_builders.FromServiceInfo(service, source_dir)
    log.info('Using runtime builder [%s]', builder_reference.build_file_uri)
    builder_reference.WarnIfDeprecated()
    yaml_path = posixpath.join(*relative_yaml_path.split(os.sep))
    build = builder_reference.LoadCloudBuild(
        {'_OUTPUT_IMAGE': image.tagged_repo,
         '_GAE_APPLICATION_YAML_PATH': yaml_path})
    # TODO(b/37542869) Remove this hack once the API can take the gs:// path
    # as a runtime name.
    service.runtime = builder_reference.runtime
    service.parsed.SetEffectiveRuntime(builder_reference.runtime)
  else:
    build = cloud_build.GetDefaultBuild(image.tagged_repo)

  metrics.CustomTimedEvent(metric_names.CLOUDBUILD_EXECUTE_START)
  cloudbuild_build.CloudBuildClient().ExecuteCloudBuild(
      cloud_build.FixUpBuild(build, object_ref), project=project)
  metrics.CustomTimedEvent(metric_names.CLOUDBUILD_EXECUTE)

  return image.tagged_repo


def DoPrepareManagedVms(gae_client):
  """Call an API to prepare the for App Engine Flexible."""
  metrics.CustomTimedEvent(metric_names.PREPARE_ENV_START)
  try:
    message = 'If this is your first deployment, this may take a while'
    with progress_tracker.ProgressTracker(message):
      # Note: this doesn't actually boot the VM, it just prepares some stuff
      # for the project via an undocumented Admin API.
      gae_client.PrepareVmRuntime()
    log.status.Print()
  except util.RPCError as err:
    # Any failures later due to an unprepared project will be noisy, so it's
    # okay not to fail here.
    log.warn(
        ("We couldn't validate that your project is ready to deploy to App "
         'Engine Flexible Environment. If deployment fails, please check the '
         'following message and try again:\n') + str(err))
  metrics.CustomTimedEvent(metric_names.PREPARE_ENV)


def PossiblyEnableFlex(project):
  """Attempts to enable the Flexible Environment API on the project.

  Possible scenarios:
  -If Flexible Environment is already enabled, success.
  -If Flexible Environment API is not yet enabled, attempts to enable it. If
   that succeeds, success.
  -If the account doesn't have permissions to confirm that the Flexible
   Environment API is or isn't enabled on this project, succeeds with a warning.
     -If the account is a service account, adds an additional warning that
      the Service Management API may need to be enabled.
  -If the Flexible Environment API is not enabled on the project and the attempt
   to enable it fails, raises PrepareFailureError.

  Args:
    project: str, the project ID.

  Raises:
    PrepareFailureError: if enabling the API fails with a 403 or 404 error code.
    googlecloudsdk.api_lib.util.exceptions.HttpException: miscellaneous errors
        returned by server.
  """
  try:
    log.warn('Checking the status of the Appengine Flexible Environment API '
             'during Appengine Flexible deployments is currently in beta.')
    enable_api.EnableServiceIfDisabled(project,
                                       'appengineflex.googleapis.com')
  except sm_exceptions.ListServicesPermissionDeniedException:
    # If we can't find out whether the Flexible API is enabled, proceed with
    # a warning.
    warning = FLEXIBLE_SERVICE_VERIFY_WARNING.format(project)
    # If user is using a service account, add more info about what might
    # have gone wrong.
    credential = c_store.LoadIfEnabled()
    if credential:
      account_type = creds.CredentialType.FromCredentials(credential)
      if account_type in (creds.CredentialType.SERVICE_ACCOUNT,
                          creds.CredentialType.P12_SERVICE_ACCOUNT):
        warning += '\n\n{}'.format(FLEXIBLE_SERVICE_VERIFY_WITH_SERVICE_ACCOUNT)
    log.warn(warning)
  except sm_exceptions.EnableServicePermissionDeniedException:
    # If enabling the Flexible API fails due to a permissions error, the
    # deployment fails.
    raise PrepareFailureError(PREPARE_FAILURE_MSG.format(project))
  except api_lib_exceptions.HttpException as err:
    # The deployment should also fail if there are unforeseen errors in
    # enabling the Flexible API. If so, display detailed information.
    err.error_format = ('Error [{status_code}] {status_message}'
                        '{error.details?'
                        '\nDetailed error information:\n{?}}')
    raise err


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


def GetAppHostname(app=None, app_id=None, service=None, version=None,
                   use_ssl=appinfo.SECURE_HTTP, deploy=True):
  """Returns the hostname of the given version of the deployed app.

  Args:
    app: Application resource. One of {app, app_id} must be given.
    app_id: str, project ID. One of {app, app_id} must be given. If both are
      provided, the hostname from app is preferred.
    service: str, the (optional) service being deployed
    version: str, the deployed version ID (omit to get the default version URL).
    use_ssl: bool, whether to construct an HTTPS URL.
    deploy: bool, if this is called during a deployment.

  Returns:
    str. Constructed URL.

  Raises:
    TypeError: if neither an app nor an app_id is provided
  """
  if not app and not app_id:
    raise TypeError('Must provide an application resource or application ID.')
  version = version or ''
  service_name = service or ''
  if service == DEFAULT_SERVICE:
    service_name = ''

  domain = DEFAULT_DOMAIN
  if not app and ':' in app_id:
    api_client = appengine_api_client.GetApiClient()
    app = api_client.GetApplication()
  if app:
    app_id, domain = app.defaultHostname.split('.', 1)

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
  subdomain_parts = filter(bool, [version, service_name, app_id])
  scheme = 'http'
  if use_ssl == appinfo.SECURE_HTTP:
    subdomain = '.'.join(subdomain_parts)
    scheme = 'http'
  else:
    subdomain = ALT_SEPARATOR.join(subdomain_parts)
    if len(subdomain) <= MAX_DNS_LABEL_LENGTH:
      scheme = 'https'
    else:
      if deploy:
        format_parts = ['$VERSION_ID', '$SERVICE_ID', '$APP_ID']
        subdomain_format = ALT_SEPARATOR.join(
            [j for (i, j) in zip([version, service_name, app_id], format_parts)
             if i])
        msg = ('This deployment will result in an invalid SSL certificate for '
               'service [{0}]. The total length of your subdomain in the '
               'format {1} should not exceed {2} characters. Please verify '
               'that the certificate corresponds to the parent domain of your '
               'application when you connect.').format(service,
                                                       subdomain_format,
                                                       MAX_DNS_LABEL_LENGTH)
        log.warn(msg)
      subdomain = '.'.join(subdomain_parts)
      if use_ssl == appinfo.SECURE_HTTP_OR_HTTPS:
        scheme = 'http'
      elif use_ssl == appinfo.SECURE_HTTPS:
        if not deploy:
          msg = ('Most browsers will reject the SSL certificate for '
                 'service [{0}].').format(service)
          log.warn(msg)
        scheme = 'https'

  return '{0}://{1}.{2}'.format(scheme, subdomain, domain)


DEFAULT_DEPLOYABLE = 'app.yaml'


def CreateAppYamlForAppDirectory(directory):
  """Ensures that an app.yaml exists or creates it if necessary.

  Attempt to fingerprint the directory and create one. This is an interactive
  process. If this does not raise an error, the app.yaml is guaranteed to exist
  once this is done.

  Args:
    directory: str, The path to the directory to create the app.yaml in.

  Raises:
    NoAppIdentifiedError, If the application type could not be identified, or
        if a yaml file could not be generated based on the state of the source.

  Returns:
    str, The path to the created app.yaml file.
  """
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
  yaml_path = os.path.join(directory, DEFAULT_DEPLOYABLE)
  if not os.path.exists(yaml_path):
    raise app_exc.NoAppIdentifiedError(
        'Failed to create an app.yaml for your app.\n\n'
        'Please prepare an app.yaml file for your application manually '
        'and deploy again.')
  return yaml_path

