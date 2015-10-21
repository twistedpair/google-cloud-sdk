# Copyright 2015 Google Inc. All Rights Reserved.

"""A shared library for processing and validating test arguments."""

import argparse
import types

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log

from googlecloudsdk.test.lib import arg_file
from googlecloudsdk.test.lib import arg_validate


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
      '--type', '-y', choices=['instrumentation', 'monkey', 'robo'],
      help='The type of test to run '
      '(_TYPE_ may be one of: instrumentation, robo, monkey).')
  parser.add_argument(
      '--app', '-a',
      help='The path to the application binary file. The path may be in the '
      'local filesystem or in Google Cloud Storage using gs:// notation.')
  parser.add_argument(
      '--app-package', '-A',
      help='The Java package of the application under test (default: extracted '
      'from the APK manifest).')
  parser.add_argument(
      '--async', action='store_true',
      help='Invoke a test asynchronously without waiting for test results.')
  parser.add_argument(
      '--auto-google-login', action='store_true',
      help=argparse.SUPPRESS)
      # TODO(user): add this help text when ready for this to be exposed:
      # help='Automatically log into the test device using a preconfigured '
      # 'Google account before beginning the test.')


def AddSharedCommandArgs(parser):
  """Register misc args which can be shared by other gcloud test commands.

  For example, 'gcloud webtest provision' and 'gcloud test run' can share these.

  Args:
    parser: An argparse parser used to add arguments that follow a command
        in the CLI.
  """
  parser.add_argument(
      '--results-bucket', '-b',
      help='The name of a Google Cloud Storage bucket where test results will '
      'be stored (default: "cloud-test-<PROJECT-ID>").')
  parser.add_argument(
      '--results-history-name', '-H',
      help='The history name for your test results (an arbitrary string label; '
      'default: the application\'s label from the APK manifest). All tests '
      'which use the same history name will have their results grouped '
      'together in the Google Developers Console in a time-ordered test '
      'history list.')
  parser.add_argument(
      '--timeout', type=arg_validate.TIMEOUT_PARSER,
      help='The max time this test execution can run before it is cancelled '
      '(default: 15m). The _TIMEOUT_ units can be h, m, or s. If no unit is '
      'given, seconds are assumed. Examples:\n'
      '- *--timeout 1h* is 1 hour\n'
      '- *--timeout 5m* is 5 minutes\n'
      '- *--timeout 200s* is 200 seconds\n'
      '- *--timeout 100* is 100 seconds')


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
      action=arg_parsers.FloatingListValuesCatcher(),
      help='The list of DEVICE_IDs to test against (default: one device '
      'determined by Google Cloud Test Lab\'s device catalog; see TAGS listed '
      'by the *$ {parent_command} devices list* command).')
  parser.add_argument(
      '--os-version-ids', '-v',
      type=arg_parsers.ArgList(min_length=1),
      metavar='OS_VERSION_ID',
      action=arg_parsers.FloatingListValuesCatcher(),
      help='The list of OS_VERSION_IDs to test against (default: a version ID '
      'determined by Google Cloud Test Lab\'s device catalog).')
  parser.add_argument(
      '--locales', '-l',
      type=arg_parsers.ArgList(min_length=1),
      metavar='LOCALE',
      action=arg_parsers.FloatingListValuesCatcher(),
      help='The list of LOCALEs to test against (default: a single locale '
      'determined by Google Cloud Test Lab\'s device catalog).')
  orientation = parser.add_argument(
      '--orientations', '-o',
      type=arg_parsers.ArgList(min_length=1, max_length=2,
                               choices=arg_validate.ORIENTATION_LIST),
      metavar='ORIENTATION',
      action=arg_parsers.FloatingListValuesCatcher(),
      help='The device orientation(s) to test against. '
      'Choices: portrait, landscape (default: portrait).')
  orientation.completer = arg_parsers.GetMultiCompleter(OrientationsCompleter)


def OrientationsCompleter(prefix, unused_parsed_args, unused_kwargs):
  return [p for p in arg_validate.ORIENTATION_LIST if p.startswith(prefix)]


def AddInstrumentationTestArgs(parser):
  """Register args which are specific to java Instrumentation tests.

  Args:
    parser: An argparse parser used to add arguments that follow a command
        in the CLI.
  """
  parser.add_argument(
      '--test', '-t',
      help='The path to the test binary file. The given path may be in the '
      'local filesystem or in Google Cloud Storage using gs:// notation.')
  parser.add_argument(
      '--test-package', '-T',
      help='The Java package name of the test (default: extracted from the '
      'APK manifest).')
  parser.add_argument(
      '--test-runner-class', '-r',
      help='The fully-qualified Java class name of the instrumentation test '
      'runner (default: the last name extracted from the APK manifest).')
  parser.add_argument(
      '--test-targets',
      type=arg_parsers.ArgList(min_length=1),
      metavar='TEST_TARGET',
      action=arg_parsers.FloatingListValuesCatcher(),
      help='A list of one or more test targets to be run (default: all '
      'targets). Each target must be fully qualified with the package name or '
      'class name, in one of these formats:\n'
      '* "package package_name"\n'
      '* "class package_name.class_name"\n'
      '* "class package_name.class_name#method_name".')


def AddMonkeyTestArgs(parser):
  """Register args which are specific to Android Monkey tests.

  Args:
    parser: An argparse parser used to add arguments that follow a command
        in the CLI.
  """
  parser.add_argument(
      '--event-count', metavar='int', type=arg_validate.POSITIVE_INT_PARSER,
      help='Number of simulated user events to create during a monkey test '
      '(default: 1000).')
  parser.add_argument(
      '--event-delay', metavar='int', type=arg_validate.NONNEGATIVE_INT_PARSER,
      help='Fixed delay in milliseconds inserted between simulated events in '
      'a monkey test (default: 0).')
  parser.add_argument(
      '--random-seed', metavar='int', type=int,
      help='Seed value for the pseudo-random number generator used during a '
      'monkey test (default: 0).')


def AddRoboTestArgs(parser):
  """Register args which are specific to Android Robo tests.

  Args:
    parser: An argparse parser used to add arguments that follow a command
        in the CLI.
  """
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


def Prepare(args, catalog):
  """Load, apply defaults, and perform validation on test CLI arguments.

  Args:
    args: an argparse namespace. All the arguments that were provided to the
      command invocation (i.e. group and command arguments combined).
    catalog: the TestingEnvironmentCatalog used to find dimension defaults.

  Raises:
    InvalidArgumentException: An argument does not contain a valid value or is
        not valid when used with the given type of test.
  """
  all_test_args_set = _GetSetOfAllTestArgs(_TEST_TYPE_ARG_RULES,
                                           _SHARED_ARG_RULES)
  args_from_file = arg_file.GetArgsFromArgFile(args.argspec, all_test_args_set)
  _ApplyArgDefaults(args, args_from_file, True)

  test_type = _GetTestTypeOrRaise(args, _TEST_TYPE_ARG_RULES)
  _ApplyArgDefaults(args, _TEST_TYPE_ARG_RULES[test_type]['defaults'])
  _ApplyArgDefaults(args, _SHARED_ARG_RULES['defaults'])
  _ApplyArgDefaults(args, _GetDefaultsFromAndroidCatalog(catalog))
  arg_validate.ValidateArgsForTestType(args,
                                       test_type,
                                       _TEST_TYPE_ARG_RULES,
                                       _SHARED_ARG_RULES,
                                       all_test_args_set)
  arg_validate.ValidateResultsBucket(args)
  # Note: Duration args are converted to an int in seconds (e.g. --timeout 5m
  # becomes args.timeout with value 300). Duration proto fields are converted
  # to strings during discovery doc creation, so we have to convert the int
  # timeout back into a string-formatted Duration (i.e. append an 's') before
  # passing it to the Testing Service.
  args.timeout = '{secs}s'.format(secs=args.timeout)


# These nested dictionaries define which test args are required, optional, or
# have specific default values based on the test type. These are critical for
# validating args loaded from an argument file because they bypass the CLI flag
# validations performed by the argparse package.
_TEST_TYPE_ARG_RULES = {
    'instrumentation': {
        'required': ['test'],
        'optional': ['test_package', 'test_runner_class', 'test_targets'],
        'defaults': {}
    },
    'monkey': {
        'required': [],
        'optional': ['event_count', 'event_delay', 'random_seed'],
        'defaults': {
            'event_count': 1000,
            'event_delay': 0,
            'random_seed': 0,
        },
    },
    'robo': {
        'required': [],
        'optional': ['app_initial_activity', 'max_depth', 'max_steps'],
        'defaults': {
            'max_depth': 50,
            'max_steps': -1,  # interpreted as 'no limit'
        },
    },
}


# Define the test args which are shared among all test types.
_SHARED_ARG_RULES = {
    'required': ['type', 'app'],
    'optional': ['device_ids', 'os_version_ids', 'locales', 'orientations',
                 'app_package', 'async', 'auto_google_login',
                 'results_bucket', 'results_history_name', 'timeout'],
    'defaults': {
        'async': False,
        'auto_google_login': False,
        'timeout': 900,  # 15 minutes
    }
}


def _GetTestTypeOrRaise(args, type_rules):
  """If the test type is not user-specified, infer the most reasonable value.

  Args:
    args: an argparse namespace. All the arguments that were provided to the
      command invocation (i.e. group and command arguments combined).
    type_rules: a nested dictionary defining the required and optional args
      per type of test, plus any default values.

  Returns:
    The type of the test to be run (e.g. 'monkey' or 'instrumentation')

  Raises:
    InvalidArgumentException if an explicit test type is invalid.
  """
  if not args.type:
    args.type = 'instrumentation' if args.test else 'robo'
  if not type_rules.has_key(args.type):
    raise exceptions.InvalidArgumentException(
        'type', "'{0}' is not a valid test type.".format(args.type))
  return args.type


def _GetDefaultsFromAndroidCatalog(catalog):
  """Builds a default dimensions dictionary using the environment catalog.

  Args:
    catalog: the Android environment catalog.

  Returns:
    A dictionary containing the default dimensions. If there is more than one
    dimension value marked as default (a bug), the first one found is used.
    Return value is formatted to be used with _ApplyArgDefaults.

  Raises:
    exceptions.UnknownArgumentException: if the default argument could not be
      detected from the catalog response.
  """
  catalog_by_dimension = {
      'device_ids': catalog.models,
      'os_version_ids': catalog.versions,
      'locales': catalog.runtimeConfiguration.locales,
      'orientations': catalog.runtimeConfiguration.orientations
  }
  defaults = {
      'device_ids': None,
      'os_version_ids': None,
      'locales': None,
      'orientations': None
  }

  for dimension_name in catalog_by_dimension:
    for dimension in catalog_by_dimension[dimension_name]:
      if 'default' in dimension.tags:
        defaults[dimension_name] = [dimension.id]
        break
    if defaults[dimension_name] is None:
      raise exceptions.UnknownArgumentException(
          dimension_name,
          'Testing service failed to provide a default argument.')

  return defaults


def _GetSetOfAllTestArgs(type_rules, shared_rules):
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


def _ApplyArgDefaults(args, defaults_dict, issue_warning=False):
  """Apply default values from a dictionary to args with no values.

  Args which already have a value are never modified by this function. Thus,
  if there are multiple sets of default args, they should be applied in order
  from highest-to-lowest precedence.

  Args:
    args: an argparse namespace. All the arguments that were provided to the
      command invocation (i.e. group and command arguments combined), plus any
      arg defaults already applied to the namespace.
    defaults_dict: a map of arg names to their default values.
    issue_warning: (boolean) issue a warning if an arg already has a value and
      we do not apply the provided default (used for arg-files where any args
      specified in the file are lower-priority than the CLI args.).
  """
  for arg in defaults_dict:
    if getattr(args, arg, None) is None:
      log.debug('Applying default {0}: {1}'
                .format(arg, str(defaults_dict[arg])))
      setattr(args, arg, defaults_dict[arg])
    elif issue_warning and getattr(args, arg) != defaults_dict[arg]:
      ext_name = arg_validate.ExternalArgNameFrom(arg)
      log.warning(
          'Command-line argument "--{0} {1}" overrides file argument "{2}: {3}"'
          .format(ext_name, _FormatArgValue(getattr(args, arg)),
                  ext_name, _FormatArgValue(defaults_dict[arg])))


def _FormatArgValue(value):
  if type(value) == types.ListType:
    return ' '.join(value)
  else:
    return str(value)
