# Copyright 2015 Google Inc. All Rights Reserved.
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

"""A shared library for processing and validating test arguments."""

import types

from googlecloudsdk.api_lib.test import arg_file
from googlecloudsdk.api_lib.test import arg_validate
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.core import log


def AddCommonTestRunArgs(parser):
  """Register args which are common to all 'gcloud test run' commands.

  Args:
    parser: An argparse parser used to add arguments that follow a command
        in the CLI.
  """
  argspec_arg = parser.add_argument(
      'argspec', nargs='?',
      help='An ARG_FILE:ARG_GROUP_NAME pair, where ARG_FILE is the path to a '
      'file containing groups of test arguments in yaml format, and '
      'ARG_GROUP_NAME is the particular yaml object holding a group of '
      'arg:value pairs to use. Run *$ gcloud topic arg-files* for more '
      'information and examples.')
  argspec_arg.completer = arg_file.ArgSpecCompleter

  parser.add_argument(
      '--type', choices=['instrumentation', 'robo'],
      help='The type of test to run.')
  parser.add_argument(
      '--app',
      help='The path to the application binary file. The path may be in the '
      'local filesystem or in Google Cloud Storage using gs:// notation.')
  parser.add_argument(
      '--async', action='store_true',
      help='Invoke a test asynchronously without waiting for test results.')
  parser.add_argument(
      '--results-bucket',
      help='The name of a Google Cloud Storage bucket where test results will '
      'be stored (default: "test-lab-<random-UUID>").')
  parser.add_argument(
      '--results-history-name',
      help='The history name for your test results (an arbitrary string label; '
      'default: the application\'s label from the APK manifest). All tests '
      'which use the same history name will have their results grouped '
      'together in the Google Developers Console in a time-ordered test '
      'history list.')
  parser.add_argument(
      '--timeout', type=arg_validate.TIMEOUT_PARSER,
      help='The max time this test execution can run before it is cancelled '
      '(default: 15m). It does not include any time necessary to prepare and '
      'clean up the target device. The _TIMEOUT_ units can be h, m, or s. If '
      'no unit is given, seconds are assumed. Examples:\n'
      '- *--timeout 1h* is 1 hour\n'
      '- *--timeout 5m* is 5 minutes\n'
      '- *--timeout 200s* is 200 seconds\n'
      '- *--timeout 100* is 100 seconds')


def AddAndroidTestArgs(parser):
  """Register args which are specific to Android test commands.

  Args:
    parser: An argparse parser used to add arguments that follow a command in
        the CLI.
  """
  parser.add_argument(
      '--app-package',
      help='The Java package of the application under test (default: extracted '
      'from the APK manifest).')
  parser.add_argument(
      '--auto-google-login', action='store_true', default=True,
      help='Automatically log into the test device using a preconfigured '
      'Google account before beginning the test.')
  parser.add_argument(
      '--directories-to-pull',
      type=arg_parsers.ArgList(),
      metavar='DIR_TO_PULL',
      help='A list of paths that will be copied from the device\'s storage to '
      'the designated results bucket after the test is complete. (ex. '
      '--directories-to-pull /sdcard/tempDir1,/data/tempDir2)')
  parser.add_argument(
      '--environment-variables',
      type=arg_parsers.ArgDict(),
      metavar='KEY=VALUE',
      help='A comma-separated, key=value, map of environment variables and '
      'their desired values. The environment variables passed here will '
      'be mirrored on to the adb run command. For example, specify '
      '--environment-variables '
      'coverage=true,coverageFile="/sdcard/tempDir/coverage.ec" to enable code '
      'coverage and provide a file path to store the coverage results.')
  parser.add_argument(
      '--obb-files',
      type=arg_parsers.ArgList(
          min_length=1, max_length=2),
      metavar='OBB_FILE',
      help='A list of one or two Android OBB file names which will be copied '
      'to each test device before the tests will run (default: None). Each '
      'OBB file name must conform to the format as specified by Android (e.g. '
      '[main|patch].0300110.com.example.android.obb) and will be installed '
      'into <shared-storage>/Android/obb/<package-name>/ on the test device.')

  # The following args are specific to Android instrumentation tests.

  parser.add_argument(
      '--test',
      help='The path to the test binary file. The given path may be in the '
      'local filesystem or in Google Cloud Storage using gs:// notation.')
  parser.add_argument(
      '--test-package',
      help='The Java package name of the test (default: extracted from the '
      'APK manifest).')
  parser.add_argument(
      '--test-runner-class',
      help='The fully-qualified Java class name of the instrumentation test '
      'runner (default: the last name extracted from the APK manifest).')
  parser.add_argument(
      '--test-targets',
      type=arg_parsers.ArgList(min_length=1),
      metavar='TEST_TARGET',
      help='A list of one or more test targets to be run (default: all '
      'targets). Each target must be fully qualified with the package name or '
      'class name, in one of these formats:\n'
      '* "package package_name"\n'
      '* "class package_name.class_name"\n'
      '* "class package_name.class_name#method_name".')

  # The following args are specific to Android Robo tests.

  parser.add_argument(
      '--max-steps', metavar='int', type=arg_validate.NONNEGATIVE_INT_PARSER,
      help='The maximum number of steps/actions a robo test can execute '
      '(default: no limit).')
  parser.add_argument(
      '--max-depth', metavar='int', type=arg_validate.POSITIVE_INT_PARSER,
      help='The maximum depth of the traversal stack a robo test can explore. '
      'Needs to be at least 2 to make Robo explore the app beyond the first '
      'activity (default: 50).')
  parser.add_argument(
      '--app-initial-activity',
      help='The initial activity used to start the app during a robo test.')
  # TODO(user): Add link for example doc once b/30894775 is resolved.
  parser.add_argument(
      '--robo-directives',
      type=arg_parsers.ArgDict(),
      help='A comma-separated, key=value, map of robo_directives for use by '
      'Robo test. Each key should be the Android resource name of a target '
      'UI element, and each value should be the text input for that element. '
      'For example, specify "--robo-directives username_resource=username,'
      'password_resource=password" to provide custom login credentials for '
      'your app. Caution: You should only use credentials for test accounts '
      'that are not associated with real users.')


def AddMatrixArgs(parser):
  """Register the repeatable args which define the the axes for a test matrix.

  Args:
    parser: An argparse parser used to add arguments that follow a command
        in the CLI.
  """
  parser.add_argument(
      '--device-ids', '-d',
      type=arg_parsers.ArgList(min_length=1),
      metavar='DEVICE_ID',
      help='The list of DEVICE_IDs to test against (default: one device '
      'determined by the Firebase Test Lab device catalog; see TAGS listed '
      'by the *$ {parent_command} devices list* command).')
  parser.add_argument(
      '--os-version-ids', '-v',
      type=arg_parsers.ArgList(min_length=1),
      metavar='OS_VERSION_ID',
      help='The list of OS_VERSION_IDs to test against (default: a version ID '
      'determined by the Firebase Test Lab device catalog).')
  parser.add_argument(
      '--locales', '-l',
      type=arg_parsers.ArgList(min_length=1),
      metavar='LOCALE',
      help='The list of LOCALEs to test against (default: a single locale '
      'determined by the Firebase Test Lab device catalog).')
  orientation = parser.add_argument(
      '--orientations', '-o',
      metavar='ORIENTATION',
      type=arg_parsers.ArgList(min_length=1, max_length=2,
                               choices=arg_validate.ORIENTATION_LIST),
      default='portrait',
      help='The device orientation(s) to test against.')
  orientation.completer = arg_parsers.GetMultiCompleter(OrientationsCompleter)


def OrientationsCompleter(prefix, unused_parsed_args, unused_kwargs):
  return [p for p in arg_validate.ORIENTATION_LIST if p.startswith(prefix)]


def GetSetOfAllTestArgs(type_rules, shared_rules):
  """Build a set of all possible 'gcloud test run' args.

  We need this set to test for invalid arg combinations because gcloud core
  adds many args to our args.Namespace that we don't care about and don't want
  to validate. We also need this to validate args coming from an arg-file.

  Args:
    type_rules: a nested dictionary defining the required and optional args
      per type of test, plus any default values.
    shared_rules: a nested dictionary defining the required and optional args
      shared among all test types, plus any default values.

  Returns:
    A set of strings for every gcloud-test argument.
  """
  all_test_args_list = shared_rules['required'] + shared_rules['optional']
  for type_dict in type_rules.values():
    all_test_args_list += type_dict['required'] + type_dict['optional']
  return set(all_test_args_list)


def ApplyLowerPriorityArgs(args, lower_pri_args, issue_cli_warning=False):
  """Apply lower-priority arg values from a dictionary to args without values.

  May be used to apply arg default values, or to merge args from another source,
  such as an arg-file. Args which already have a value are never modified by
  this function. Thus, if there are multiple sets of lower-priority args, they
  should be applied in order from highest-to-lowest precedence.

  Args:
    args: the existing argparse.Namespace. All the arguments that were provided
      to the command invocation (i.e. group and command arguments combined),
      plus any arg defaults already applied to the namespace. These args have
      higher priority than the lower_pri_args.
    lower_pri_args: a dict mapping lower-priority arg names to their values.
    issue_cli_warning: (boolean) issue a warning if an arg already has a value
      from the command line and we do not apply the lower-priority arg value
      (used for arg-files where any args specified in the file are lower in
      priority than the CLI args.).
  """
  for arg in lower_pri_args:
    if getattr(args, arg, None) is None:
      log.debug('Applying default {0}: {1}'
                .format(arg, str(lower_pri_args[arg])))
      setattr(args, arg, lower_pri_args[arg])
    elif issue_cli_warning and getattr(args, arg) != lower_pri_args[arg]:
      ext_name = arg_validate.ExternalArgNameFrom(arg)
      log.warning(
          'Command-line argument "--{0} {1}" overrides file argument "{2}: {3}"'
          .format(ext_name, _FormatArgValue(getattr(args, arg)),
                  ext_name, _FormatArgValue(lower_pri_args[arg])))


def _FormatArgValue(value):
  if type(value) == types.ListType:
    return ' '.join(value)
  else:
    return str(value)
