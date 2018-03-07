# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Utilities for running Daisy builds on Google Container Builder."""

from apitools.base.py import encoding

from googlecloudsdk.api_lib.cloudbuild import cloudbuild_util
from googlecloudsdk.api_lib.cloudbuild import logs as cb_logs
from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.api_lib.services import enable_api as services_api
from googlecloudsdk.api_lib.services import services_util
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.cloudbuild import execution
from googlecloudsdk.command_lib.projects import util as projects_util
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io


_BUILDER = 'gcr.io/compute-image-tools/daisy:release'


class FailedBuildException(core_exceptions.Error):
  """Exception for builds that did not succeed."""

  def __init__(self, build):
    super(FailedBuildException, self).__init__(
        'build {id} completed with status "{status}"'.format(
            id=build.id, status=build.status))


def AddCommonDaisyArgs(parser):
  """Common arguments for Daisy builds."""
  parser.add_argument(
      '--log-location',
      help='Directory in Google Cloud Storage to hold build logs. If not '
      'set, ```gs://<project num>.cloudbuild-logs.googleusercontent.com/``` '
      'will be created and used.',
  )
  parser.add_argument(
      '--timeout',
      type=arg_parsers.Duration(),
      default='2h',
      help="""\
          Maximum time a build can last before it is failed as "TIMEOUT".
          For example, specifying ``2h'' will fail the process after  2 hours.
          See $ gcloud topic datetimes for information on duration formats.
          """
  )
  base.ASYNC_FLAG.AddToParser(parser)


def CheckIamPermissions(project_id):
  """Check for needed IAM permissions and prompt to add if missing.

  Args:
    project_id: A string with the name of the project.
  """
  project = projects_api.Get(project_id)
  # If the user's project doesn't have cloudbuild enabled yet, then the service
  # account won't even exist. If so, then ask to enable it before continuing.
  cloudbuild_service_name = 'cloudbuild.googleapis.com'
  if not services_api.IsServiceEnabled(project.projectId,
                                       cloudbuild_service_name):
    prompt_message = ('The Google Cloud Container Builder service is not '
                      'enabled for this project. It is required for this '
                      'operation.\n')
    console_io.PromptContinue(prompt_message,
                              'Would you like to enable Container Builder?',
                              throw_if_unattended=True,
                              cancel_on_no=True)
    operation = services_api.EnableServiceApiCall(project.projectId,
                                                  cloudbuild_service_name)
    # Wait for the operation to finish.
    services_util.ProcessOperationResult(operation, async=False)

  # Now that we're sure the service account exists, actually check permissions.
  service_account = 'serviceAccount:{0}@cloudbuild.gserviceaccount.com'.format(
      project.projectNumber)
  expected_permissions = {'roles/compute.admin': service_account,
                          'roles/iam.serviceAccountActor': service_account}
  permissions = projects_api.GetIamPolicy(project_id)
  for binding in permissions.bindings:
    if expected_permissions.get(binding.role) in binding.members:
      del expected_permissions[binding.role]

  if expected_permissions:
    ep_table = ['{0} {1}'.format(role, account) for role, account
                in expected_permissions.items()]
    prompt_message = (
        'The following IAM permissions are needed for this operation:\n'
        '[{0}]\n'.format('\n'.join(ep_table)))
    console_io.PromptContinue(
        message=prompt_message,
        prompt_string='Would you like to add the permissions',
        throw_if_unattended=True,
        cancel_on_no=True)

    for role, account in expected_permissions.items():
      log.info('Adding [{0}] to [{1}]'.format(account, role))
      projects_api.AddIamPolicyBinding(project_id, account, role)


def _CreateCloudBuild(build_config, client, messages):
  """Create a build in cloud build.

  Args:
    build_config: A cloud build Build message.
    client: The cloud build api client.
    messages: The cloud build api messages module.

  Returns:
    Tuple containing a cloud build build object and the resource reference
    for that build.
  """
  log.debug('submitting build: {0}'.format(repr(build_config)))
  op = client.projects_builds.Create(
      messages.CloudbuildProjectsBuildsCreateRequest(
          build=build_config,
          projectId=properties.VALUES.core.project.Get()))
  json = encoding.MessageToJson(op.metadata)
  build = encoding.JsonToMessage(messages.BuildOperationMetadata, json).build

  build_ref = resources.REGISTRY.Create(
      collection='cloudbuild.projects.builds',
      projectId=build.projectId,
      id=build.id)

  log.CreatedResource(build_ref)

  if build.logUrl:
    log.status.Print('Logs are available at [{0}].'.format(build.logUrl))
  else:
    log.status.Print('Logs are available in the Cloud Console.')

  return build, build_ref


def GetAndCreateDaisyBucket(bucket_name=None, storage_client=None):
  """Determine the name of the GCS bucket to use and create if necessary.

  Args:
    bucket_name: A string containing a bucket name to use, otherwise the
      bucket will be named based on the project id.
    storage_client: The storage_api client object.

  Returns:
    A string containing the name of the GCS bucket to use.
  """
  project = properties.VALUES.core.project.GetOrFail()
  safe_project = project.replace(':', '-')
  safe_project = safe_project.replace('.', '-')
  bucket_name = bucket_name or '{0}-daisy-bkt'.format(safe_project)
  safe_bucket_name = bucket_name.replace('google', 'elgoog')

  if not storage_client:
    storage_client = storage_api.StorageClient()

  storage_client.CreateBucketIfNotExists(safe_bucket_name)

  return safe_bucket_name


def RunDaisyBuild(args, workflow, variables, daisy_bucket=None, tags=None):
  """Run a build with Daisy on Google Cloud Builder.

  Args:
    args: an argparse namespace. All the arguments that were provided to this
      command invocation.
    workflow: The path to the Daisy workflow to run.
    variables: A string of key-value pairs to pass to Daisy.
    daisy_bucket: A string containing the name of the GCS bucket that daisy
      should use.
    tags: A list of strings for adding tags to the Argo build.

  Returns:
    A build object that either streams the output or is displayed as a
    link to the build.

  Raises:
    FailedBuildException: If the build is completed and not 'SUCCESS'.
  """
  client = cloudbuild_util.GetClientInstance()
  messages = cloudbuild_util.GetMessagesModule()
  project_id = projects_util.ParseProject(
      properties.VALUES.core.project.GetOrFail())

  CheckIamPermissions(project_id)

  timeout_str = '{0}s'.format(args.timeout)

  daisy_bucket = daisy_bucket or GetAndCreateDaisyBucket()

  daisy_args = ['-gcs_path=gs://{0}/'.format(daisy_bucket),
                '-variables={0}'.format(variables),
                workflow,
               ]

  build_tags = ['gce-daisy']
  if tags:
    build_tags.extend(tags)

  # First, create the build request.
  build_config = messages.Build(
      steps=[
          messages.BuildStep(
              name=_BUILDER,
              args=daisy_args,
          ),
      ],
      tags=build_tags,
      timeout=timeout_str,
  )
  if args.log_location:
    gcs_log_dir = resources.REGISTRY.Parse(
        args.log_location, collection='storage.objects')

    build_config.logsBucket = (
        'gs://{0}/{1}'.format(gcs_log_dir.bucket, gcs_log_dir.object))

  # Start the build.
  build, build_ref = _CreateCloudBuild(build_config, client, messages)

  # If the command is run --async, we just print out a reference to the build.
  if args.async:
    return build

  mash_handler = execution.MashHandler(
      execution.GetCancelBuildHandler(client, messages, build_ref))

  # Otherwise, logs are streamed from GCS.
  with execution_utils.CtrlCSection(mash_handler):
    build = cb_logs.CloudBuildClient(client, messages).Stream(build_ref)

  if build.status == messages.Build.StatusValueValuesEnum.TIMEOUT:
    log.status.Print(
        'Your build timed out. Use the [--timeout=DURATION] flag to change '
        'the timeout threshold.')

  if build.status != messages.Build.StatusValueValuesEnum.SUCCESS:
    raise FailedBuildException(build)

  return build
