# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Utilities for `gcloud app` deployment.

Mostly created to selectively enable Cloud Endpoints in the beta/preview release
tracks.
"""
import argparse
import os

from googlecloudsdk.api_lib.app import appengine_api_client
from googlecloudsdk.api_lib.app import appengine_client
from googlecloudsdk.api_lib.app import cloud_endpoints
from googlecloudsdk.api_lib.app import deploy_app_command_util
from googlecloudsdk.api_lib.app import deploy_command_util
from googlecloudsdk.api_lib.app import exceptions as api_lib_exceptions
from googlecloudsdk.api_lib.app import metric_names
from googlecloudsdk.api_lib.app import util
from googlecloudsdk.api_lib.app import version_util
from googlecloudsdk.api_lib.app import yaml_parsing
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.app import create_util
from googlecloudsdk.command_lib.app import exceptions
from googlecloudsdk.command_lib.app import flags
from googlecloudsdk.command_lib.app import output_helpers
from googlecloudsdk.command_lib.app import staging
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import files


class VersionPromotionError(core_exceptions.Error):

  def __init__(self, err):
    super(VersionPromotionError, self).__init__(
        'Your deployment has succeeded, but promoting the new version to '
        'default failed. '
        'You may not have permissions to change traffic splits. '
        'Changing traffic splits requires the Owner, Editor, App Engine Admin, '
        'or App Engine Service Admin role. '
        'Please contact your project owner and use the '
        '`gcloud app services set-traffic --splits <version>=1` command to '
        'redirect traffic to your newly deployed version.\n\n'
        'Original error: ' + str(err))


class DeployOptions(object):
  """Values of options that affect deployment process in general.

  No deployment details (e.g. targets for a specific deployment).

  Attributes:
    promote: True if the deployed version should recieve all traffic.
    stop_previous_version: Stop previous version
    enable_endpoints: Enable Cloud Endpoints for the deployed app.
    app_create: Offer to create an app if current GCP project is appless.
  """

  def __init__(self, promote, stop_previous_version, enable_endpoints,
               app_create):
    self.promote = promote
    self.stop_previous_version = stop_previous_version
    self.enable_endpoints = enable_endpoints
    self.app_create = app_create

  @classmethod
  def FromProperties(cls, enable_endpoints, app_create):
    promote = properties.VALUES.app.promote_by_default.GetBool()
    stop_previous_version = (
        properties.VALUES.app.stop_previous_version.GetBool())
    return cls(promote, stop_previous_version, enable_endpoints, app_create)


def _UploadFiles(service, code_bucket_ref):
  """Upload files in the service being deployed, if necessary.

  "Necessary" here means that the service is not "hermetic." A hermetic service
  is an image-based (i.e. Flexible) deployment that does not also serve static
  files.

  The upload method used depends on the app.use_gsutil property.

  Args:
    service: configuration for service to upload files for
    code_bucket_ref: cloud_storage.BucketReference, the code bucket to upload to

  Returns:
    A manifest of files uploaded in the format expected by the Admin API.
  """
  manifest = None
  # "Non-hermetic" services require file upload outside the Docker image.
  if not service.is_hermetic:
    if properties.VALUES.app.use_gsutil.GetBool():
      manifest = deploy_app_command_util.CopyFilesToCodeBucket(
          service, code_bucket_ref)
      metrics.CustomTimedEvent(metric_names.COPY_APP_FILES)
    else:
      manifest = deploy_app_command_util.CopyFilesToCodeBucketNoGsUtil(
          service, code_bucket_ref)
      metrics.CustomTimedEvent(metric_names.COPY_APP_FILES_NO_GSUTIL)
  return manifest


class ServiceDeployer(object):
  """Coordinator (reusable) for deployment of one service at a time.

  Attributes:
    api_client: api_lib.app.appengine_api_client.AppengineClient, App Engine
        Admin API client.
    stager: command_lib.app.staging.Stager, the object used to potentially stage
        applications with matching runtime/environment combinations.
    deploy_options: DeployOptions, the options to use for services deployed by
        this ServiceDeployer.
  """

  def __init__(self, api_client, stager, deploy_options):
    self.api_client = api_client
    self.stager = stager
    self.deploy_options = deploy_options

  def _PossiblyConfigureEndpoints(self, service, new_version):
    """Configures endpoints for this service (if enabled).

    If the app has enabled Endpoints API Management features, pass control to
    the cloud_endpoints handler.

    The cloud_endpoints handler calls the Service Management APIs and creates an
    endpoints/service.json file on disk which will need to be bundled into the
    app Docker image.

    Args:
      service: yaml_parsing.ServiceYamlInfo, service configuration to be
        deployed
      new_version: version_util.Version describing where to deploy the service

    Returns:
      EndpointsServiceInfo, or None if endpoints were not created.
    """
    if self.deploy_options.enable_endpoints:
      return cloud_endpoints.ProcessEndpointsService(service,
                                                     new_version.project)
    return None

  def _PossiblyBuildAndPush(self, new_version, service, image, code_bucket_ref):
    """Builds and Pushes the Docker image if necessary for this service.

    Args:
      new_version: version_util.Version describing where to deploy the service
      service: yaml_parsing.ServiceYamlInfo, service configuration to be
        deployed
      image: str or None, the URL for the Docker image to be deployed (if image
        already exists).
      code_bucket_ref: cloud_storage.BucketReference where the service's files
        have been uploaded

    Returns:
      str, The name of the pushed or given container image or None if the
        service does not require an image.
    """
    if service.RequiresImage():
      if service.env == util.Environment.FLEXIBLE:
        log.warning('Deployment of App Engine Flexible Environment apps is '
                    'currently in Beta')
      if not image:
        image = deploy_command_util.BuildAndPushDockerImage(
            new_version.project, service, new_version.id, code_bucket_ref)
    else:
      image = None
    return image

  def _PossiblyPromote(self, all_services, new_version):
    """Promotes the new version to default (if specified by the user).

    Args:
      all_services: dict of service ID to service_util.Service objects
        corresponding to all pre-existing services (used to determine how to
        promote this version to receive all traffic, if applicable).
      new_version: version_util.Version describing where to deploy the service

    Raises:
      VersionPromotionError: if the version could not successfully promoted
    """
    if self.deploy_options.promote:
      try:
        version_util.PromoteVersion(
            all_services, new_version, self.api_client,
            self.deploy_options.stop_previous_version)
      except calliope_exceptions.HttpException as err:
        raise VersionPromotionError(err)
    elif self.deploy_options.stop_previous_version:
      log.info('Not stopping previous version because new version was '
               'not promoted.')

  def Deploy(self, service, new_version, code_bucket_ref, image, all_services):
    """Deploy the given service.

    Performs all deployment steps for the given service (if applicable):
    * Enable endpoints (for beta deployments)
    * Build and push the Docker image (Flex only, if image_url not provided)
    * Upload files (non-hermetic deployments)
    * Create the new version
    * Promote the version to receieve all traffic (if --promote given (default))
    * Stop the previous version (if new version promoted and
      --stop-previous-version given (default))

    Args:
      service: yaml_parsing.ServiceYamlInfo, service configuration to be
        deployed
      new_version: version_util.Version describing where to deploy the service
      code_bucket_ref: cloud_storage.BucketReference where the service's files
        have been uploaded
      image: str or None, the URL for the Docker image to be deployed (if image
        already exists).
      all_services: dict of service ID to service_util.Service objects
        corresponding to all pre-existing services (used to determine how to
        promote this version to receive all traffic, if applicable).
    """
    log.status.Print('Beginning deployment of service [{service}]...'
                     .format(service=new_version.service))

    with self.stager.Stage(service.file, service.runtime,
                           service.env) as app_yaml:
      if app_yaml:
        app_dir = os.path.dirname(app_yaml)
      else:
        app_dir = os.getcwd()
      with files.ChDir(app_dir):
        endpoints_info = self._PossiblyConfigureEndpoints(service, new_version)
        image = self._PossiblyBuildAndPush(new_version, service, image,
                                           code_bucket_ref)
        manifest = _UploadFiles(service, code_bucket_ref)

        # Actually create the new version of the service.
        message = 'Updating service [{service}]'.format(
            service=new_version.service)
        with console_io.ProgressTracker(message):
          self.api_client.DeployService(new_version.service, new_version.id,
                                        service, manifest, image,
                                        endpoints_info)
          metrics.CustomTimedEvent(metric_names.DEPLOY_API)
          self._PossiblyPromote(all_services, new_version)


def ArgsDeploy(parser):
  """Get arguments for this command.

  Args:
    parser: argparse.ArgumentParser, the parser for this command.
  """
  flags.SERVER_FLAG.AddToParser(parser)
  flags.IGNORE_CERTS_FLAG.AddToParser(parser)
  flags.DOCKER_BUILD_FLAG.AddToParser(parser)
  parser.add_argument(
      '--version', '-v',
      help='The version of the app that will be created or replaced by this '
      'deployment.  If you do not specify a version, one will be generated for '
      'you.')
  parser.add_argument(
      '--bucket',
      type=storage_util.BucketReference.Argument,
      help=("The Google Cloud Storage bucket used to stage files associated "
            "with the deployment. If this argument is not specified, the "
            "application's default code bucket is used."))
  deployables = parser.add_argument(
      'deployables', nargs='*',
      help='The yaml files for the services or configurations you want to '
      'deploy.')
  deployables.detailed_help = (
      'The yaml files for the services or configurations you want to deploy. '
      'If not given, defaults to `app.yaml` in the current directory. '
      'If that is not found, attempts to automatically generate necessary '
      'configuration files (such as app.yaml) in the current directory.')
  parser.add_argument(
      '--stop-previous-version',
      action=actions.StoreBooleanProperty(
          properties.VALUES.app.stop_previous_version),
      help='Stop the previously running version when deploying a new version '
           'that receives all traffic.')
  parser.add_argument(
      '--image-url',
      help='Deploy with a specific Docker image.  Docker url must be from one '
      'of the valid gcr hostnames.')
  promote = parser.add_argument(
      '--promote',
      action=actions.StoreBooleanProperty(
          properties.VALUES.app.promote_by_default),
      help='Promote the deployed version to receive all traffic.')
  promote.detailed_help = (
      'Promote the deployed version to receive all traffic.\n\n'
      'True by default. To change the default behavior for your current '
      'environment, run:\n\n'
      '    $ gcloud config set app/promote_by_default false')
  parser.add_argument(
      '--skip-staging',
      action='store_true',
      default=False,
      help=argparse.SUPPRESS)
  # For internal use only
  parser.add_argument(
      '--skip-image-url-validation',
      action='store_true',
      default=False,
      help=argparse.SUPPRESS)


def RunDeploy(unused_self, args, enable_endpoints=False, app_create=False):
  """Perform a deployment based on the given args."""
  version_id = args.version or util.GenerateVersionId()
  flags.ValidateVersion(version_id)
  project = properties.VALUES.core.project.Get(required=True)
  deploy_options = DeployOptions.FromProperties(enable_endpoints, app_create)

  # Parse existing app.yamls or try to generate a new one if the directory is
  # empty.
  if not args.deployables:
    yaml_path = deploy_command_util.DEFAULT_DEPLOYABLE
    if not os.path.exists(deploy_command_util.DEFAULT_DEPLOYABLE):
      log.warning('Automatic app detection is currently in Beta')
      yaml_path = deploy_command_util.CreateAppYamlForAppDirectory(os.getcwd())
    app_config = yaml_parsing.AppConfigSet([yaml_path])
  else:
    app_config = yaml_parsing.AppConfigSet(args.deployables)

  services = app_config.Services()

  if not args.skip_image_url_validation:
    flags.ValidateImageUrl(args.image_url, services)

  # The new API client.
  api_client = appengine_api_client.GetApiClient()
  # pylint: disable=protected-access
  log.debug('API endpoint: [{endpoint}], API version: [{version}]'.format(
      endpoint=api_client.client.url,
      version=api_client.client._VERSION))
  # The legacy admin console API client.
  # The Admin Console API existed long before the App Engine Admin API, and
  # isn't being improved. We're in the process of migrating all of the calls
  # over to the Admin API, but a few things (notably config deployments) haven't
  # been ported over yet.
  ac_client = appengine_client.AppengineClient(
      args.server, args.ignore_bad_certs)

  app = _PossiblyCreateApp(api_client, project, deploy_options.app_create)

  # Tell the user what is going to happen, and ask them to confirm.
  deployed_urls = output_helpers.DisplayProposedDeployment(
      app, project, app_config, version_id, deploy_options.promote)
  console_io.PromptContinue(cancel_on_no=True)
  if services:
    # Do generic app setup if deploying any services.
    # All deployment paths for a service involve uploading source to GCS.
    code_bucket_ref = args.bucket or flags.GetCodeBucket(app, project)
    metrics.CustomTimedEvent(metric_names.GET_CODE_BUCKET)
    log.debug('Using bucket [{b}].'.format(b=code_bucket_ref.ToBucketUrl()))

    # Prepare Flex if any service is going to deploy an image.
    if any([m.RequiresImage() for m in services.values()]):
      deploy_command_util.DoPrepareManagedVms(ac_client)

    all_services = dict([(s.id, s) for s in api_client.ListServices()])
  else:
    code_bucket_ref = None
    all_services = {}

  new_versions = []
  stager = staging.GetNoopStager() if args.skip_staging else staging.GetStager()
  deployer = ServiceDeployer(api_client, stager, deploy_options)
  for (name, service) in services.iteritems():
    new_version = version_util.Version(project, name, version_id)
    deployer.Deploy(service, new_version, code_bucket_ref, args.image_url,
                    all_services)
    new_versions.append(new_version)
    log.status.Print('Deployed service [{0}] to [{1}]'.format(
        name, deployed_urls[name]))

  # Deploy config files.
  for (name, config) in app_config.Configs().iteritems():
    message = 'Updating config [{config}]'.format(config=name)
    with console_io.ProgressTracker(message):
      ac_client.UpdateConfig(name, config.parsed)

  updated_configs = app_config.Configs().keys()

  PrintPostDeployHints(new_versions, updated_configs)

  # Return all the things that were deployed.
  return {
      'versions': new_versions,
      'configs': updated_configs
  }


# TODO(b/30632016): Move to Epilog() when we have a good way to pass
# information about the deployed versions
def PrintPostDeployHints(new_versions, updated_configs):
  """Print hints for user at the end of a deployment."""
  if yaml_parsing.ConfigYamlInfo.CRON in updated_configs:
    log.status.Print('\nCron jobs have been updated.')
    if yaml_parsing.ConfigYamlInfo.QUEUE not in updated_configs:
      log.status.Print('\nThe Cloud Platform Console Task Queues page has a '
                       'tab that shows the tasks that are running cron jobs.')
  if yaml_parsing.ConfigYamlInfo.DISPATCH in updated_configs:
    log.status.Print('\nCustom routings have been updated.')
  if yaml_parsing.ConfigYamlInfo.DOS in updated_configs:
    log.status.Print('\nDoS protection has been updated.'
                     '\n\nTo delete all blacklist entries, change the dos.yaml '
                     'file to just contain:'
                     '\n    blacklist:'
                     'and redeploy it.')
  if yaml_parsing.ConfigYamlInfo.QUEUE in updated_configs:
    log.status.Print('\nTask queues have been updated.')
    log.status.Print('\nThe Cloud Platform Console Task Queues page has a tab '
                     'that shows the tasks that are running cron jobs.')
  if yaml_parsing.ConfigYamlInfo.INDEX in updated_configs:
    log.status.Print('\nIndexes are being rebuilt. This may take a moment.')

  if not new_versions:
    return
  elif len(new_versions) > 1:
    service_hint = ' -s <service>'
  elif new_versions[0].service == 'default':
    service_hint = ''
  else:
    service = new_versions[0].service
    service_hint = ' -s {svc}'.format(svc=service)
  log.status.Print(
      '\nYou can read logs from the command line by running:\n'
      '  $ gcloud app logs read')
  log.status.Print(
      '\nTo view your application in the web browser run:\n'
      '  $ gcloud app browse' + service_hint)


def _PossiblyCreateApp(api_client, project, app_create):
  """Returns an app resource, and creates it if the stars are aligned.

  App creation happens only if the current project is app-less,
  app_create is True, we are running in interactive mode and the user
  explicitly wants to.

  Args:
    api_client: Admin API client.
    project: The GCP project/app id.
    app_create: True if interactive app creation should be allowed.

  Returns:
    An app object (never returns None).

  Raises:
    MissingApplicationError: If an app does not exist and cannot be created.
  """
  try:
    return api_client.GetApplication()
  except api_lib_exceptions.NotFoundError:
    # Invariant: GCP Project does exist but (singleton) GAE app is not yet
    # created. Offer to create one if the following conditions are true:
    # 1. `app_create` is True (currently `beta` only)
    # 2. We are currently running in interactive mode
    msg = output_helpers.CREATE_APP_PROMPT.format(project=project)
    if (app_create and console_io.CanPrompt() and
        console_io.PromptContinue(message=msg)):
      # Equivalent to running `gcloud beta app create`
      create_util.CreateAppInteractively(api_client, project)
      # App resource must be fetched again
      return api_client.GetApplication()
    raise exceptions.MissingApplicationError(project)
