# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""Translation rule for entrypoint."""

import logging
from os import path
from typing import Mapping, Sequence

from googlecloudsdk.command_lib.app.gae_to_cr_migration_util.common import util
from googlecloudsdk.command_lib.app.gae_to_cr_migration_util.config import feature_helper
from googlecloudsdk.core.util import files


_DEFAULT_PYTHON_ENTRYPOINT = 'gunicorn -b :$PORT main:app'
# Cloud Run service must listen on 0.0.0.0 host,
# ref https://cloud.google.com/run/docs/container-contract#port
_DEFAULT_RUBY_ENTRYPOINT = 'bundle exec ruby app.rb -o 0.0.0.0'
_DEFAULT_ENTRYPOINT_INFO_FORMAT = (
    '[Info] Default entrypoint for {runtime} is : "{entrypoint}", retry `gcloud'
    ' app migrate appengine-to-cloudrun` with the --command="{entrypoint}"'
    ' flag.'
)


def translate_entrypoint_features(
    input_data: Mapping[str, any],
    input_type: feature_helper.InputType,
    supported_features_app_yaml: Mapping[str, feature_helper.SupportedFeature],
    command: str,
) -> Sequence[str]:
  """Tranlsate entrypoint from App Engine app to entrypoint for equivalent Cloud Run app."""
  input_key_value_pairs = util.flatten_keys(input_data, '')
  if input_type is feature_helper.InputType.ADMIN_API:
    return _generate_entrypoint_admin_api(input_key_value_pairs, command)
  return _generate_entrypoint_app_yaml(
      input_key_value_pairs, supported_features_app_yaml
  )


def _generate_entrypoint_admin_api(
    input_key_value_pairs: Mapping[str, any], command: str
) -> Sequence[str]:
  """Generate entrypoint for Cloud Run based on Admin API input.

  Args:
    input_key_value_pairs: Flattened key-value pairs from the input data.
    command: The command to use as the entrypoint.

  Returns:
    A list of strings representing the entrypoint flags.
  """
  if command is None:
    logging.warning(
        'Warning: entrypoint for the app is not detected/provided, if an'
        ' entrypoint is needed to start the app, please use the `--command`'
        ' flag to specify the entrypoint for the App.'
    )
    _print_default_entrypoint_per_runtime(input_key_value_pairs)
    return []
  if 'runtime' in input_key_value_pairs:
    runtime = input_key_value_pairs['runtime']
    if runtime in util.RUNTIMES_WITH_PROCFILE_ENTRYPOINT:
      logging.info(
          'generating a procfile with runtime %s, entrypoint %s',
          runtime,
          command,
      )
      _generate_procfile(runtime, command)
      return []
  return util.generate_output_flags(['--command'], f'"{command}"')


def _generate_entrypoint_app_yaml(
    input_key_value_pairs: Mapping[str, any],
    supported_features_app_yaml: Mapping[str, feature_helper.SupportedFeature],
) -> Sequence[str]:
  """Generate entrypoint for Cloud Run based on app.yaml input.

  Args:
    input_key_value_pairs: Flattened key-value pairs from the input data.
    supported_features_app_yaml: The supported features from app.yaml.

  Returns:
    A list of strings representing the entrypoint flags.
  """
  if _should_generate_procfile(input_key_value_pairs):
    runtime = input_key_value_pairs['runtime']
    entrypoint = _get_entrypoint_from_input(input_key_value_pairs)
    # entrypoint is not specified at input, use the default entrypoint
    if not entrypoint:
      entrypoint = _get_default_entrypoint_by_runtime(input_key_value_pairs)
    _generate_procfile(runtime, entrypoint)
    return []
  feature_key = 'entrypoint'
  if feature_key in input_key_value_pairs:
    feature = supported_features_app_yaml[feature_key]
    input_value = f'"{input_key_value_pairs[feature_key]}"'
    return util.generate_output_flags(feature.flags, input_value)
  return []


def _should_generate_procfile(input_key_value_pairs: Mapping[str, any]) -> bool:
  if 'runtime' not in input_key_value_pairs:
    return False
  runtime = input_key_value_pairs['runtime']
  if runtime not in util.RUNTIMES_WITH_PROCFILE_ENTRYPOINT:
    return False
  return True


def _generate_procfile(runtime: str, entrypoint: str) -> None:
  """Generate a Procfile for the given runtime and entrypoint.

  If a Procfile does not exist, it will be created with the provided entrypoint.
  If a Procfile exists, and it does not contain the provided entrypoint,
  a warning will be printed to the console.

  Args:
    runtime: The runtime of the app.
    entrypoint: The entrypoint to use in the Procfile.
  """
  if not _procfile_exists():
    with files.FileWriter('Procfile', 'w') as file:
      file.write(f'web: {entrypoint}')
      logging.info(
          '[Info] A Procfile is created with entrypoint "%s", this'
          ' is needed to deploy Apps from source with %s runtime to'
          ' Cloud Run using Buildpacks.',
          entrypoint,
          runtime,
      )
    return

  if not _procfile_contains_entrypoint(entrypoint):
    logging.warning(
        '[Warning] Entrypoint "%s" is not found at existing'
        ' Procfile, please add "web: %s" to the existing Procfile.',
        entrypoint,
        entrypoint,
    )


def _procfile_exists() -> bool:
  return path.exists('Procfile')


def _procfile_contains_entrypoint(entrypoint: str) -> bool:
  if not _procfile_exists():
    return False
  with files.FileReader('Procfile') as file:
    procfile_content = file.read()
    if entrypoint in procfile_content:
      return True
  return False


def _get_entrypoint_from_input(input_key_value_pairs: Mapping[str, any]) -> str:
  for key in util.ENTRYPOINT_FEATURE_KEYS:
    if key in input_key_value_pairs:
      return input_key_value_pairs[key]
  return ''


def _get_default_entrypoint_by_runtime(
    input_key_value_pairs: Mapping[str, any],
)-> str:
  if 'runtime' in input_key_value_pairs:
    runtime = input_key_value_pairs['runtime']
    if runtime.startswith('python'):
      # Check if requirements.txt exists and contains gunicorn as a dependency
      _generate_requirement_file()
      return _DEFAULT_PYTHON_ENTRYPOINT
    if runtime.startswith('ruby'):
      return _DEFAULT_RUBY_ENTRYPOINT
  return ''


def _generate_requirement_file() -> None:
  """Generate a requirements.txt file if it does not exist."""
  file_exist = path.exists('requirements.txt')
  if file_exist:
    with files.FileReader('requirements.txt') as file:
      file_content = file.read()
    if 'gunicorn' not in file_content:
      logging.warning(
          '[Warning] gunicorn is not found at requirements.txt, please add'
          ' "gunicorn" to the existing requirements.txt in order to deploy Apps'
          ' from source to Cloud Run using Buildpacks.'
      )
  else:
    with files.FileWriter('requirements.txt', 'w') as file:
      file.write('gunicorn')
      logging.info(
          '[Info] A requirements.txt is created with gunicorn as a dependency,'
          ' this is needed to deploy Apps from source with python runtime to'
          ' Cloud Run using Buildpacks.'
      )


def _print_default_entrypoint_per_runtime(
    input_key_value_pairs: Mapping[str, any],
) -> None:
  """Print the default entrypoint for the given runtime.

  Args:
    input_key_value_pairs: Flattened key-value pairs from the input data.

  Returns:
    None

  Prints the default entrypoint for the given runtime to the console.
  """
  if 'runtime' in input_key_value_pairs:
    runtime = input_key_value_pairs['runtime']
    if runtime.startswith('python'):
      logging.info(
          _DEFAULT_ENTRYPOINT_INFO_FORMAT,
          runtime,
          _DEFAULT_PYTHON_ENTRYPOINT,
      )
      logging.info(
          'Add "gunicorn" as a dependency to requirements.txt because'
          " it is used for the %s's default entrypoint '%s'", runtime,
          _DEFAULT_PYTHON_ENTRYPOINT,
      )
    if runtime.startswith('ruby'):
      logging.info(
          _DEFAULT_ENTRYPOINT_INFO_FORMAT,
          runtime,
          _DEFAULT_RUBY_ENTRYPOINT
      )
