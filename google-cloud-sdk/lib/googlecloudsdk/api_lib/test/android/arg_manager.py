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

"""A shared library for processing and validating Android test arguments."""

from googlecloudsdk.api_lib.test import arg_file
from googlecloudsdk.api_lib.test import arg_util
from googlecloudsdk.api_lib.test import arg_validate
from googlecloudsdk.calliope import exceptions


def TypedArgRules():
  """Returns the rules for Android test args which depend on the test type.

  This dict is declared in a function rather than globally to avoid garbage
  collection issues during unit tests.

  Returns:
    A dict keyed by whether shared args are required or optional, and with a
    nested dict containing any default values for those shared args.
  """
  return {
      'instrumentation': {
          'required': ['test'],
          'optional': ['test_package', 'test_runner_class', 'test_targets'],
          'defaults': {}
      },
      'robo': {
          'required': [],
          'optional': ['app_initial_activity', 'max_depth', 'max_steps',
                       'robo_directives'],
          'defaults': {
              'max_depth': 50,
              'max_steps': -1,  # interpreted as 'no limit'
          },
      },
  }


def SharedArgRules():
  """Returns the rules for Android test args which are shared by all test types.

  This dict is declared in a function rather than globally to avoid garbage
  collection issues during unit tests.

  Returns:
    A dict keyed by whether shared args are required or optional, and with a
    nested dict containing any default values for those shared args.
  """
  return {
      'required': ['type', 'app'],
      'optional': [
          'device_ids', 'os_version_ids', 'locales', 'orientations',
          'app_package', 'async', 'auto_google_login', 'obb_files',
          'results_bucket', 'results_history_name', 'timeout',
          'environment_variables', 'directories_to_pull'
      ],
      'defaults': {
          'async': False,
          'auto_google_login': False,
          'timeout': 900,  # 15 minutes
      }
  }


def AllArgsSet():
  """Returns a set containing the names of every Android test arg."""
  return arg_util.GetSetOfAllTestArgs(TypedArgRules(), SharedArgRules())


class AndroidArgsManager(object):
  """Manages test arguments for Android devices."""

  def __init__(self, catalog, typed_arg_rules=None, shared_arg_rules=None):
    """Constructs an AndroidArgsManager for a single Android test matrix.

    Args:
      catalog: the TestingEnvironmentCatalog used to find defaults for matrix
        dimension args.
      typed_arg_rules: a nested dict of dicts which are keyed first on the test
        type, then by whether args are required or optional, and what their
        default values are. If None, the default from TypedArgRules() is used.
      shared_arg_rules: a dict keyed by whether shared args are required or
        optional, and with a nested dict containing any default values for those
        shared args. If None, the default dict from SharedArgRules() is used.
    """
    self._device_catalog = catalog
    self._typed_arg_rules = typed_arg_rules or TypedArgRules()
    self._shared_arg_rules = shared_arg_rules or SharedArgRules()

  def Prepare(self, args):
    """Load, apply defaults, and perform validation on test arguments.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        gcloud command invocation (i.e. group and command arguments combined).
        Arg values from an optional arg-file and/or arg default values may be
        added to this argparse namespace.

    Raises:
      InvalidArgumentException: If an argument name is unknown, an argument does
        not contain a valid value, or an argument is not valid when used with
        the given type of test.
      RequiredArgumentException: If a required arg is missing.
    """
    all_test_args_set = arg_util.GetSetOfAllTestArgs(self._typed_arg_rules,
                                                     self._shared_arg_rules)
    args_from_file = arg_file.GetArgsFromArgFile(args.argspec,
                                                 all_test_args_set)
    arg_util.ApplyLowerPriorityArgs(args, args_from_file, True)

    test_type = self.GetTestTypeOrRaise(args)
    typed_arg_defaults = self._typed_arg_rules[test_type]['defaults']
    shared_arg_defaults = self._shared_arg_rules['defaults']
    dimension_defaults = _GetDefaultsFromAndroidCatalog(self._device_catalog)

    arg_util.ApplyLowerPriorityArgs(args, typed_arg_defaults)
    arg_util.ApplyLowerPriorityArgs(args, shared_arg_defaults)
    arg_util.ApplyLowerPriorityArgs(args, dimension_defaults)

    arg_validate.ValidateArgsForTestType(args,
                                         test_type,
                                         self._typed_arg_rules,
                                         self._shared_arg_rules,
                                         all_test_args_set)
    arg_validate.ValidateOsVersions(args, self._device_catalog)
    arg_validate.ValidateResultsBucket(args)
    arg_validate.ValidateObbFileNames(args.obb_files)
    arg_validate.ValidateRoboDirectivesList(args)
    arg_validate.ValidateEnvironmentVariablesList(args)
    arg_validate.ValidateDirectoriesToPullList(args)

  def GetTestTypeOrRaise(self, args):
    """If the test type is not user-specified, infer the most reasonable value.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        gcloud command invocation (i.e. group and command arguments combined).

    Returns:
      The type of the test to be run (e.g. 'robo' or 'instrumentation') and
      sets the 'type' arg if it was not user-specified.

    Raises:
      InvalidArgumentException if an explicit test type is invalid.
    """
    if not args.type:
      args.type = 'instrumentation' if args.test else 'robo'
    if not self._typed_arg_rules.has_key(args.type):
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
    Return value is formatted to be used with ApplyLowerPriorityArgs.

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
