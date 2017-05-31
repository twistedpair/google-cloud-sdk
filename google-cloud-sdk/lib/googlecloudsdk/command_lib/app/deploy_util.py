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
from googlecloudsdk.api_lib.app import runtime_builders
from googlecloudsdk.api_lib.app import util
from googlecloudsdk.api_lib.app import version_util
from googlecloudsdk.api_lib.app import yaml_parsing
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.api_lib.util import exceptions as core_api_exceptions
from googlecloudsdk.calliope import actions
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
from googlecloudsdk.core.console import progress_tracker


class Error(core_exceptions.Error):
  """Base error for this module."""


class VersionPromotionError(Error):

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


class StoppedApplicationError(Error):
  """Error if deployment fails because application is stopped/disabled."""

  def __init__(self, app):
    super(StoppedApplicationError, self).__init__(
        'Unable to deploy to application [{}] with status [{}]: Deploying '
        'to stopped apps is not allowed.'.format(app.id, app.servingStatus))


class DeployOptions(object):
  """Values of options that affect deployment process in general.

  No deployment details (e.g. targets for a specific deployment).

  Attributes:
    promote: True if the deployed version should recieve all traffic.
    stop_previous_version: Stop previous version
    enable_endpoints: Enable Cloud Endpoints for the deployed app.
    runtime_builder_strategy: runtime_builders.RuntimeBuilderStrategy, when to
      use the new CloudBuild-based runtime builders (alternative is old
      externalized runtimes).
  """

  def __init__(self, promote, stop_previous_version, enable_endpoints,
               runtime_builder_strategy):
    self.promote = promote
    self.stop_previous_version = stop_previous_version
    self.enable_endpoints = enable_endpoints
    self.runtime_builder_strategy = runtime_builder_strategy

  @classmethod
  def FromProperties(cls, enable_endpoints, runtime_builder_strategy):
    promote = properties.VALUES.app.promote_by_default.GetBool()
    stop_previous_version = (
        properties.VALUES.app.stop_previous_version.GetBool())
    return cls(promote, stop_previous_version, enable_endpoints,
               runtime_builder_strategy)


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

  def _PossiblyConfigureEndpoints(self, service, source_dir, new_version):
    """Configures endpoints for this service (if enabled).

    If the app has enabled Endpoints API Management features, pass control to
    the cloud_endpoints handler.

    The cloud_endpoints handler calls the Service Management APIs and creates an
    endpoints/service.json file on disk which will need to be bundled into the
    app Docker image.

    Args:
      service: yaml_parsing.ServiceYamlInfo, service configuration to be
        deployed
      source_dir: str, path to the service's source directory
      new_version: version_util.Version describing where to deploy the service

    Returns:
      EndpointsServiceInfo, or None if endpoints were not created.
    """
    if self.deploy_options.enable_endpoints:
      return cloud_endpoints.ProcessEndpointsService(service, source_dir,
                                                     new_version.project)
    return None

  def _PossiblyBuildAndPush(self, new_version, service, source_dir, image,
                            code_bucket_ref, gcr_domain):
    """Builds and Pushes the Docker image if necessary for this service.

    Args:
      new_version: version_util.Version describing where to deploy the service
      service: yaml_parsing.ServiceYamlInfo, service configuration to be
        deployed
      source_dir: str, path to the service's source directory
      image: str or None, the URL for the Docker image to be deployed (if image
        already exists).
      code_bucket_ref: cloud_storage.BucketReference where the service's files
        have been uploaded
      gcr_domain: str, Cloud Registry domain, determines the physical location
        of the image. E.g. `us.gcr.io`.
    Returns:
      str, The name of the pushed or given container image or None if the
        service does not require an image.
    """
    if service.RequiresImage():
      if not image:
        image = deploy_command_util.BuildAndPushDockerImage(
            new_version.project, service, source_dir, new_version.id,
            code_bucket_ref, gcr_domain,
            self.deploy_options.runtime_builder_strategy)
      elif service.parsed.skip_files.regex:
        log.warning('Deployment of service [{0}] will ignore the skip_files '
                    'field in the configuration file, because the image has '
                    'already been built.'.format(new_version.service))
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
      except core_api_exceptions.HttpException as err:
        raise VersionPromotionError(err)
    elif self.deploy_options.stop_previous_version:
      log.info('Not stopping previous version because new version was '
               'not promoted.')

  def Deploy(self, service, new_version, code_bucket_ref, image, all_services,
             gcr_domain):
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
      gcr_domain: str, Cloud Registry domain, determines the physical location
        of the image. E.g. `us.gcr.io`.
    """
    log.status.Print('Beginning deployment of service [{service}]...'
                     .format(service=new_version.service))

    with self.stager.Stage(service.file, service.runtime,
                           service.env) as staging_dir:
      source_dir = staging_dir or os.path.dirname(service.file)
      endpoints_info = self._PossiblyConfigureEndpoints(
          service, source_dir, new_version)
      image = self._PossiblyBuildAndPush(
          new_version, service, source_dir, image, code_bucket_ref, gcr_domain)
      manifest = None
      # "Non-hermetic" services require file upload outside the Docker image.
      if not service.is_hermetic:
        manifest = deploy_app_command_util.CopyFilesToCodeBucket(
            service, source_dir, code_bucket_ref)

      # Actually create the new version of the service.
      message = 'Updating service [{service}]'.format(
          service=new_version.service)
      with progress_tracker.ProgressTracker(message):
        metrics.CustomTimedEvent(metric_names.DEPLOY_API_START)
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
      '--version', '-v', type=flags.VERSION_TYPE,
      help='The version of the app that will be created or replaced by this '
      'deployment.  If you do not specify a version, one will be generated for '
      'you.')
  parser.add_argument(
      '--bucket',
      type=storage_util.BucketReference.FromArgument,
      help=("The Google Cloud Storage bucket used to stage files associated "
            "with the deployment. If this argument is not specified, the "
            "application's default code bucket is used."))
  parser.add_argument(
      'deployables', nargs='*',
      help="""\
      The yaml files for the services or configurations you want to deploy.
      If not given, defaults to `app.yaml` in the current directory.
      If that is not found, attempts to automatically generate necessary
      configuration files (such as app.yaml) in the current directory.""")
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
  parser.add_argument(
      '--promote',
      action=actions.StoreBooleanProperty(
          properties.VALUES.app.promote_by_default),
      help="""\
      Promote the deployed version to receive all traffic.

      True by default. To change the default behavior for your current
      environment, run:

          $ gcloud config set app/promote_by_default false""")
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


def RunDeploy(
    args, enable_endpoints=False, use_beta_stager=False,
    runtime_builder_strategy=runtime_builders.RuntimeBuilderStrategy.NEVER,
    use_service_management=False, check_for_stopped=False):
  """Perform a deployment based on the given args.

  Args:
    args: argparse.Namespace, An object that contains the values for the
        arguments specified in the ArgsDeploy() function.
    enable_endpoints: Enable Cloud Endpoints for the deployed app.
    use_beta_stager: Use the stager registry defined for the beta track rather
        than the default stager registry.
    runtime_builder_strategy: runtime_builders.RuntimeBuilderStrategy, when to
      use the new CloudBuild-based runtime builders (alternative is old
      externalized runtimes).
    use_service_management: bool, whether to use servicemanagement API to
      enable the Appengine Flexible API for a Flexible deployment.
    check_for_stopped: bool, whether to check if the app is stopped before
      deploying.

  Returns:
    A dict on the form `{'versions': new_versions, 'configs': updated_configs}`
    where new_versions is a list of version_util.Version, and updated_configs
    is a list of config file identifiers, see yaml_parsing.ConfigYamlInfo.
  """
  project = properties.VALUES.core.project.Get(required=True)
  deploy_options = DeployOptions.FromProperties(
      enable_endpoints, runtime_builder_strategy=runtime_builder_strategy)

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

  # If applicable, sort services by order they were passed to the command.
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

  app = _PossiblyCreateApp(api_client, project)
  if check_for_stopped:
    _RaiseIfStopped(api_client, app)
  app = _PossiblyRepairApp(api_client, app)

  # Tell the user what is going to happen, and ask them to confirm.
  version_id = args.version or util.GenerateVersionId()
  deployed_urls = output_helpers.DisplayProposedDeployment(
      app, project, app_config, version_id, deploy_options.promote)
  console_io.PromptContinue(cancel_on_no=True)
  if services:
    # Do generic app setup if deploying any services.
    # All deployment paths for a service involve uploading source to GCS.
    metrics.CustomTimedEvent(metric_names.GET_CODE_BUCKET_START)
    code_bucket_ref = args.bucket or flags.GetCodeBucket(app, project)
    metrics.CustomTimedEvent(metric_names.GET_CODE_BUCKET)
    log.debug('Using bucket [{b}].'.format(b=code_bucket_ref.ToBucketUrl()))

    # Prepare Flex if any service is going to deploy an image.
    if any([m.RequiresImage() for m in services.values()]):
      if use_service_management:
        deploy_command_util.PossiblyEnableFlex(project)
      else:
        deploy_command_util.DoPrepareManagedVms(ac_client)

    all_services = dict([(s.id, s) for s in api_client.ListServices()])
  else:
    code_bucket_ref = None
    all_services = {}
  new_versions = []
  if args.skip_staging:
    stager = staging.GetNoopStager()
  elif use_beta_stager:
    stager = staging.GetBetaStager()
  else:
    stager = staging.GetStager()
  deployer = ServiceDeployer(api_client, stager, deploy_options)

  # Track whether a service has been deployed yet, for metrics.
  service_deployed = False
  for name, service in services.iteritems():
    if not service_deployed:
      metrics.CustomTimedEvent(metric_names.FIRST_SERVICE_DEPLOY_START)
    new_version = version_util.Version(project, name, version_id)
    deployer.Deploy(service, new_version, code_bucket_ref, args.image_url,
                    all_services, app.gcrDomain)
    new_versions.append(new_version)
    log.status.Print('Deployed service [{0}] to [{1}]'.format(
        name, deployed_urls[name]))
    if not service_deployed:
      metrics.CustomTimedEvent(metric_names.FIRST_SERVICE_DEPLOY)
    service_deployed = True

  # Deploy config files.
  if app_config.Configs():
    metrics.CustomTimedEvent(metric_names.UPDATE_CONFIG_START)
  for (name, config) in app_config.Configs().iteritems():
    message = 'Updating config [{config}]'.format(config=name)
    with progress_tracker.ProgressTracker(message):
      ac_client.UpdateConfig(name, config.parsed)
  if app_config.Configs():
    metrics.CustomTimedEvent(metric_names.UPDATE_CONFIG)

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
      log.status.Print('\nVisit the Cloud Platform Console Task Queues page '
                       'to view your queues and cron jobs.')
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
    log.status.Print('\nVisit the Cloud Platform Console Task Queues page '
                     'to view your queues and cron jobs.')
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
      '\nYou can stream logs from the command line by running:\n'
      '  $ gcloud app logs tail' + (service_hint or ' -s default'))
  log.status.Print(
      '\nTo view your application in the web browser run:\n'
      '  $ gcloud app browse' + service_hint)


def _PossiblyCreateApp(api_client, project):
  """Returns an app resource, and creates it if the stars are aligned.

  App creation happens only if the current project is app-less, we are running
  in interactive mode and the user explicitly wants to.

  Args:
    api_client: Admin API client.
    project: The GCP project/app id.

  Returns:
    An app object (never returns None).

  Raises:
    MissingApplicationError: If an app does not exist and cannot be created.
  """
  try:
    return api_client.GetApplication()
  except api_lib_exceptions.NotFoundError:
    # Invariant: GCP Project does exist but (singleton) GAE app is not yet
    # created.
    #
    # Check for interactive mode, since this action is irreversible and somewhat
    # surprising. CreateAppInteractively will provide a cancel option for
    # interactive users, and MissingApplicationException includes instructions
    # for non-interactive users to fix this.
    log.debug('No app found:', exc_info=True)
    if console_io.CanPrompt():

      # Equivalent to running `gcloud app create`
      create_util.CreateAppInteractively(api_client, project)
      # App resource must be fetched again
      return api_client.GetApplication()
    raise exceptions.MissingApplicationError(project)
  except core_api_exceptions.HttpException as e:
    if e.payload.status_code == 403:
      raise core_api_exceptions.HttpException(
          ('Permissions error fetching application [{}]. Please '
           'make sure you are using the correct project ID and that '
           'you have permission to view applications on the project.'.format(
               api_client._FormatApp())))  # pylint: disable=protected-access
    raise


def _PossiblyRepairApp(api_client, app):
  """Repairs the app if necessary and returns a healthy app object.

  An app is considered unhealthy if the codeBucket field is missing.
  This may include more conditions in the future.

  Args:
    api_client: Admin API client.
    app: App object (with potentially missing resources).

  Returns:
    An app object (either the same or a new one), which contains the right
    resources, including code bucket.
  """
  if not app.codeBucket:
    with progress_tracker.ProgressTracker('Initializing App Engine resources'):
      api_client.RepairApplication()
      app = api_client.GetApplication()
  return app


def _RaiseIfStopped(api_client, app):
  """Checks if app is disabled and raises error if so.

  Deploying to a disabled app is not allowed.

  Args:
    api_client: Admin API client.
    app: App object (including status).

  Raises:
    StoppedApplicationError: if the app is currently disabled.
  """
  if api_client.IsStopped(app):
    raise StoppedApplicationError(app)
