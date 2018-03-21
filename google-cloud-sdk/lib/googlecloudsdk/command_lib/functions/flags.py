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

"""Helpers for flags in commands working with Google Cloud Functions."""

from googlecloudsdk.api_lib.functions import triggers
from googlecloudsdk.api_lib.functions import util as api_util
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.util import completers
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


API = 'cloudfunctions'
API_VERSION = 'v1'
LOCATIONS_COLLECTION = API + '.projects.locations'

SEVERITIES = ['DEBUG', 'INFO', 'ERROR']


def AddMinLogLevelFlag(parser):
  min_log_arg = base.ChoiceArgument(
      '--min-log-level',
      choices=[x.lower() for x in SEVERITIES],
      help_str='Minimum level of logs to be fetched.'
  )
  min_log_arg.AddToParser(parser)


def GetLocationsUri(resource):
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName(API, API_VERSION)
  ref = registry.Parse(
      resource.name,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection=LOCATIONS_COLLECTION)
  return ref.SelfLink()


class LocationsCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(LocationsCompleter, self).__init__(
        collection=LOCATIONS_COLLECTION,
        list_command='alpha functions regions list --uri',
        **kwargs)


def AddRegionFlag(parser, help_text):
  parser.add_argument(
      '--region',
      help=help_text,
      completer=LocationsCompleter,
      action=actions.StoreProperty(properties.VALUES.functions.region),
  )


def AddFunctionNameArg(parser):
  """Add arguments specifying function name to the parser."""
  parser.add_argument(
      'name',
      help='Name of the function to deploy.',
      type=api_util.ValidateFunctionNameOrRaise,
  )


def AddFunctionMemoryFlag(parser):
  """Add flag for specifying function memory to the parser."""
  parser.add_argument(
      '--memory',
      type=arg_parsers.BinarySize(
          suggested_binary_size_scales=['KB', 'MB', 'MiB', 'GB', 'GiB'],
          default_unit='MB'),
      help="""\
      Limit on the amount of memory the function can use.

      Allowed values are: 128MB, 256MB, 512MB, 1024MB, and 2048MB. By default,
      a new function is limited to 256MB of memory. When deploying an update to
      an existing function, the function will keep its old memory limit unless
      you specify this flag.""")


def AddFunctionTimeoutFlag(parser):
  """Add flag for specifying function timeout to the parser."""
  parser.add_argument(
      '--timeout',
      help="""\
      The function execution timeout, e.g. 30s for 30 seconds. Defaults to
      original value for existing function or 60 seconds for new functions.
      Cannot be more than 540s.
      See $ gcloud topic datetimes for information on duration formats.""",
      type=arg_parsers.Duration(lower_bound='1s', upper_bound='540s'))


def AddFunctionRetryFlag(parser):
  """Add flag for specifying function retry behavior to the parser."""
  parser.add_argument(
      '--retry',
      help=('If specified, then the function will be retried in case of a '
            'failure.'),
      action='store_true',
  )


def AddSourceFlag(parser):
  """Add flag for specifying function source code to the parser."""
  parser.add_argument(
      '--source',
      help="""\
      Location of source code to deploy.

      Location of the source can be one of the following:

      * Source code in Google Cloud Storage (must be a `.zip` archive),
      * Reference to source repository or,
      * Local filesystem path (root directory of function source).

      The value of the flag will be interpreted as a Cloud Storage location, if
      it starts with `gs://`.

      The value will be interpreted as a reference to a source repository, if it
      starts with `https://`.

      Otherwise, it will be interpreted as the local filesystem path. When
      deploying source from the local filesystem, this command skips files
      specified in the `.gcloudignore` file (see `gcloud topic gcloudignore` for
      more information). If the `.gcloudignore` file doesn't exist, the command
      will try to create it.

      The minimal source repository URL is:


      `https://source.developers.google.com/projects/${PROJECT}/repos/${REPO}`

      By using the URL above, sources from the root directory of the repository
      on the revision tagged `master` will be used.

      If you want to deploy from a revision different from `master`, append one
      of the following to the URL:

      * `/revisions/${REVISION}`,
      * `/moveable-aliases/${MOVEABLE_ALIAS}`,
      * `/fixed-aliases/${FIXED_ALIAS}`.

      If you'd like to deploy sources from a directory different from the root,
      you must specify a revision, a moveable alias, or a fixed alias, as above,
      and append `/paths/${PATH_TO_SOURCES_DIRECTORY}` to the URL.

      Overall, the URL should match the following regular expression:

      ```
      ^https://source\\.developers\\.google\\.com/projects/
      (?<accountId>[^/]+)/repos/(?<repoName>[^/]+)
      (((/revisions/(?<commit>[^/]+))|(/moveable-aliases/(?<branch>[^/]+))|
      (/fixed-aliases/(?<tag>[^/]+)))(/paths/(?<path>.*))?)?$
      ```

      If the source location is not explicitly set, new functions will deploy
      from the current directory. Existing functions keep their old source.

      """)


def AddStageBucketFlag(parser):
  """Add flag for specifying stage bucket to the parser."""
  parser.add_argument(
      '--stage-bucket',
      help=('When deploying a function from a local directory, this flag\'s '
            'value is the name of the Google Cloud Storage bucket in which '
            'source code will be stored.'),
      type=api_util.ValidateAndStandarizeBucketUriOrRaise)


def AddEntryPointFlag(parser):
  """Add flag for specifying entry point to the parser."""
  parser.add_argument(
      '--entry-point',
      type=api_util.ValidateEntryPointNameOrRaise,
      help="""\
      By default when a Google Cloud Function is triggered, it executes a
      JavaScript function with the same name. Or, if it cannot find a
      function with the same name, it executes a function named `function`.
      You can use this flag to override the default behavior, by specifying
      the name of a JavaScript function that will be executed when the
      Google Cloud Function is triggered."""
  )


def AddTriggerFlagGroup(parser):
  """Add arguments specyfying functions trigger to the parser."""
  # You can also use --trigger-provider but it is hidden argument so not
  # mentioning it for now.
  trigger_group = parser.add_mutually_exclusive_group(
      help=(
          ' If you don\'t specify a trigger when deploying an update to an '
          'existing function it will keep its current trigger. You must specify'
          ' `--trigger-topic`, `--trigger-bucket`, `--trigger-http` or '
          '(`--trigger-event` AND `--trigger-resource`) when deploying a '
          'new function.'))
  trigger_group.add_argument(
      '--trigger-topic',
      help=('Name of Pub/Sub topic. Every message published in this topic '
            'will trigger function execution with message contents passed as '
            'input data.'),
      type=api_util.ValidatePubsubTopicNameOrRaise)
  trigger_group.add_argument(
      '--trigger-bucket',
      help=('Google Cloud Storage bucket name. Every change in files in this '
            'bucket will trigger function execution.'),
      type=api_util.ValidateAndStandarizeBucketUriOrRaise)
  trigger_group.add_argument(
      '--trigger-http', action='store_true',
      help="""\
      Function will be assigned an endpoint, which you can view by using
      the `describe` command. Any HTTP request (of a supported type) to the
      endpoint will trigger function execution. Supported HTTP request
      types are: POST, PUT, GET, DELETE, and OPTIONS.""")

  trigger_provider_spec_group = trigger_group.add_argument_group()
  # check later as type of applicable input depends on options above
  trigger_provider_spec_group.add_argument(
      '--trigger-event',
      metavar='EVENT_TYPE',
      choices=sorted(triggers.INPUT_TRIGGER_PROVIDER_REGISTRY.AllEventLabels()),
      help=('Specifies which action should trigger the function. For a '
            'list of acceptable values, call `functions event_types list`.')
  )
  trigger_provider_spec_group.add_argument(
      '--trigger-resource',
      metavar='RESOURCE',
      help=('Specifies which resource from `--trigger-event` is being '
            'observed. E.g. if `--trigger-event` is  '
            '`providers/cloud.storage/eventTypes/object.change`, '
            '`--trigger-resource` must be a bucket name. For a list of '
            'expected resources, call `functions event_types list`.'),
  )
