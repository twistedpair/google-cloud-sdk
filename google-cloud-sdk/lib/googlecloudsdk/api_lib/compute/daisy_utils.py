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
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.cloudbuild import execution
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


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
          Valid units for this flag are ``s'' for seconds, ``m'' for minutes,
          and ``h'' for hours. If no unit is specified, seconds is assumed.
          """
  )
  base.ASYNC_FLAG.AddToParser(parser)


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


def RunDaisyBuild(args, workflow, variables):
  """Run a build with Daisy on Google Cloud Builder.

  Args:
    args: an argparse namespace. All the arguments that were provided to this
      command invocation.
    workflow: The path to the Daisy workflow to run.
    variables: A string of key-value pairs to pass to Daisy.

  Returns:
    A build object that either streams the output or is displayed as a
    link to the build.

  Raises:
    FailedBuildException: If the build is completed and not 'SUCCESS'.
  """
  client = cloudbuild_util.GetClientInstance()
  messages = cloudbuild_util.GetMessagesModule()

  timeout_str = '{0}s'.format(args.timeout)

  # First, create the build request.
  build_config = messages.Build(
      steps=[
          messages.BuildStep(
              name=_BUILDER,
              args=['-variables={0}'.format(variables),
                    workflow,
                   ],
          ),
      ],
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
