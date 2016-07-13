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
from googlecloudsdk.api_lib.app import cloud_storage
from googlecloudsdk.api_lib.app import deploy_app_command_util
from googlecloudsdk.api_lib.app import deploy_command_util
from googlecloudsdk.api_lib.app import metric_names
from googlecloudsdk.api_lib.app import util
from googlecloudsdk.api_lib.app import version_util
from googlecloudsdk.api_lib.app import yaml_parsing
from googlecloudsdk.calliope import actions
from googlecloudsdk.command_lib.app import exceptions
from googlecloudsdk.command_lib.app import flags
from googlecloudsdk.command_lib.app import output_helpers
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.docker import constants
from googlecloudsdk.core.docker import docker


def ArgsDeploy(parser):
  """Get arguments for this command.

  Args:
    parser: argparse.ArgumentParser, the parser for this command.
  """
  flags.SERVER_FLAG.AddToParser(parser)
  flags.IGNORE_CERTS_FLAG.AddToParser(parser)
  parser.add_argument(
      '--version', '-v',
      help='The version of the app that will be created or replaced by this '
      'deployment.  If you do not specify a version, one will be generated for '
      'you.')
  parser.add_argument(
      '--bucket',
      type=cloud_storage.GcsBucketArgument,
      help=("The Google Cloud Storage bucket used to stage files associated "
            "with the deployment. If this argument is not specified, the "
            "application's default code bucket is used."))
  parser.add_argument(
      '--docker-build',
      choices=['remote', 'local'],
      help=argparse.SUPPRESS)
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


def RunDeploy(unused_self, args, enable_endpoints=False):
  """Perform a deployment based on the given args."""
  project = properties.VALUES.core.project.Get(required=True)
  version = args.version or util.GenerateVersionId()
  flags.ValidateVersion(version)
  promote = properties.VALUES.app.promote_by_default.GetBool()
  stop_previous_version = (
      properties.VALUES.app.stop_previous_version.GetBool())
  if args.docker_build:
    raise exceptions.DeployError("""\
Docker builds now use Container Builder by default. To run a Docker build on
your own host, you can run:
  docker build -t gcr.io/<project>/<service.version> .
  gcloud docker push gcr.io/<project>/<service.version>
  gcloud app deploy --image-url=gcr.io/<project>/<service.version>
  """)

  # Parse existing app.yamls or try to generate a new one if the directory is
  # empty.
  if not args.deployables:
    log.warning('Automatic app detection is currently in Beta')
    yaml_path = deploy_command_util.EnsureAppYamlForAppDirectory(os.getcwd())
    app_config = yaml_parsing.AppConfigSet([yaml_path])
  else:
    app_config = yaml_parsing.AppConfigSet(args.deployables)

  services = app_config.Services()

  # Validate the image url if provided, and ensure there is a single service
  # being deployed.
  if args.image_url:
    if len(services) != 1:
      raise exceptions.MultiDeployError()
    for registry in constants.ALL_SUPPORTED_REGISTRIES:
      if args.image_url.startswith(registry):
        break
    else:
      raise docker.UnsupportedRegistryError(args.image_url)

  # The new API client.
  api_client = appengine_api_client.GetApiClient()
  # pylint: disable=protected-access
  log.debug('API endpoint: [{endpoint}], API version: [{version}]'.format(
      endpoint=api_client.client.url,
      version=api_client.client._VERSION))
  # The legacy admin console API client.
  ac_client = appengine_client.AppengineClient(
      args.server, args.ignore_bad_certs)

  # Tell the user what is going to happen, and ask them to confirm.
  deployed_urls = output_helpers.DisplayProposedDeployment(
      project, app_config, version, promote)
  console_io.PromptContinue(default=True, throw_if_unattended=False,
                            cancel_on_no=True)

  # Do generic app setup if deploying any services.
  if services:
    # All deployment paths for a service involve uploading source to GCS.
    code_bucket_ref = flags.GetCodeBucket(api_client, project, args.bucket)
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
  for (name, service) in services.iteritems():
    log.status.Print('Beginning deployment of service [{service}]...'
                     .format(service=name))

    # If the app has enabled Endpoints API Management features, pass
    # control to the cloud_endpoints handler.
    # The cloud_endpoints handler calls the Service Management APIs and
    # creates an endpoints/service.json file on disk which will need to
    # be bundled into the app Docker image.
    if enable_endpoints:
      cloud_endpoints.ProcessEndpointsService(service, project)

    # Build and Push the Docker image if necessary for this service.
    if service.RequiresImage():
      log.warning('Deployment of App Engine Flexible Environment apps is '
                  'currently in Beta')
      if args.image_url:
        image = args.image_url
      else:
        image = deploy_command_util.BuildAndPushDockerImage(
            project, service, version, code_bucket_ref)
    else:
      image = None

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
    else:
      manifest = None

    # Actually create the new version of the service.
    message = 'Updating service [{service}]'.format(service=name)
    new_version = version_util.Version(project, name, version)
    with console_io.ProgressTracker(message):
      api_client.DeployService(name, version, service, manifest, image)
      metrics.CustomTimedEvent(metric_names.DEPLOY_API)
      if promote:
        version_util.PromoteVersion(all_services, new_version, api_client,
                                    stop_previous_version)
      elif stop_previous_version:
        log.info('Not stopping previous version because new version was '
                 'not promoted.')

    # We don't have a deployed URL for custom-domain apps, since these are
    # not possible to predict with 100% accuracy (b/24603280).
    deployed_url = deployed_urls.get(service)
    if deployed_url:
      log.status.Print('Deployed service [{0}] to [{1}]'.format(
          name, deployed_url))
    else:
      log.status.Print('Deployed service [{0}]'.format(name))
    new_versions.append(new_version)

  # Deploy config files.
  for (name, config) in app_config.Configs().iteritems():
    message = 'Updating config [{config}]'.format(config=name)
    with console_io.ProgressTracker(message):
      ac_client.UpdateConfig(name, config.parsed)

  # Return all the things that were deployed.
  return {
      'versions': new_versions,
      'configs': app_config.Configs().keys()
  }


def EpilogDeploy(unused_self, unused_resources_were_displayed):
  """Print hints for user at the end of a deployment."""
  log.status.Print(
      '\nYou can read logs from the command line by running:\n'
      '  $ gcloud app logs read')
  log.status.Print(
      'To view your application in the web browser run:\n'
      '  $ gcloud app browse')
