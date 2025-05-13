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
"""Flags and helpers for the Developer Connect CLI."""
from googlecloudsdk.calliope import arg_parsers


# Flags
def AddDiscoveryArgument(parser):
  """Creates state argument."""
  parser.add_argument(
      '--run-discovery',
      action='store_true',
      help=(
          'Sets the state of the insight config to PENDING and kicks off the'
          ' discovery flow.'
      ),
  )


def AddArtifactArgument(parser):
  """Creates artifact argument."""
  parser.add_argument(
      '--artifact-uri',
      metavar='ARTIFACT_URI',
      dest='artifact_uri',
      required=True,
      help=(
          'Identifier for the specific artifact you want to update'
      ),
  )


def AddBuildProjectArgument(parser):
  """Creates build project argument."""
  parser.add_argument(
      '--build-project',
      metavar='BUILD_PROJECT',
      dest='build_project',
      required=True,
      help=(
          'The project ID of the project to where the artifact is built.'
      ),
  )


def AddAppHubApplicationArgument(parser):
  """Creates app hub application argument."""
  parser.add_argument(
      '--app-hub-application',
      metavar='APP_HUB_APPLICATION',
      dest='app_hub_application',
      required=True,
      help='The App Hub application to which the insight config is associated.',
  )


# Helper function for ArtifactConfigType
def RemoveOuterBrackets(input_string):
  """Removes outer brackets from a string."""
  if input_string.startswith('[') and input_string.endswith(']'):
    stripped_string = input_string[1:-1]
  elif input_string.startswith('[') or input_string.endswith(']'):
    raise arg_parsers.ArgumentTypeError(
        f"Invalid artifact config string: '{input_string}'. Inconsistent"
        ' brackets.'
    )
  else:
    stripped_string = input_string
  # Split the string by the delimiter "]["
  parts = stripped_string.split('][')
  return parts


def ArtifactConfigType(item_string):
  """Parses a single artifact configuration string.

  Args:
    item_string: The string to parse. The string can be in a custom key-value
      format (e.g. 'key1=val1.)

  Returns:
    A dictionary of artifact configuration key-value pairs.
  """

  if not item_string:
    return {}

  final_dict = {}
  artifact_configs = RemoveOuterBrackets(item_string)
  if not artifact_configs:
    raise arg_parsers.ArgumentTypeError(
        f"Invalid artifact config string: '{item_string}'. "
        'Expected format like: '
        "'uri={REGION}-docker.pkg.dev/my-project/my-repo/my-image,buildProject=my-project' "
        "or '[uri={REGION}-docker.pkg.dev/my-project/my-repo/my-image,buildProject=my-project]'."
    )

  for artifact_config in artifact_configs:
    aritfact_config_props = artifact_config.strip().split(',')
    result_dict = {}
    for prop in aritfact_config_props:
      # Split by key-value pairs: key=val
      parts = prop.split('=', 1)
      if len(parts) != 2:
        raise arg_parsers.ArgumentTypeError(
            f"Invalid key-value pair format: '{prop}' within"
            f" '{item_string}'. Expected"
            " 'uri={REGION}-docker.pkg.dev/my-project/my-repo/my-image or"
            " buildProject=my-project'."
        )
      key = parts[0].strip()
      value_str = parts[1].strip()
      result_dict[key] = value_str
    if 'uri' not in result_dict or 'buildProject' not in result_dict:
      raise arg_parsers.ArgumentTypeError(
          f"Invalid artifact config string: '{item_string}'. Expected format like: "
          '--artifact-config=uri={REGION}-docker.pkg.dev/my-project/my-repo/my-image,buildProject=my-project'
      )
    final_dict[result_dict['uri']] = result_dict['buildProject']

  return final_dict


def AddArtifactConfigsArgument(parser):
  """Creates artifact config argument."""
  parser.add_argument(
      '--artifact-config',
      metavar='ARTIFACT_CONFIG_ITEM',
      dest='artifact_configs',
      type=ArtifactConfigType,
      action='append',
      help="""\
Specifies a single artifact configuration. This flag can be repeated for
multiple configurations.

Each configuration can be provided in a key-value format.

Format examples:
`--artifact-config=uri={REGION}-docker.pkg.dev/my-project/my-repo/my-image,buildProject=my-project`
`--artifact-config=[uri={REGION}-docker.pkg.dev/my-project/my-repo/my-image,buildProject=my-project]`

Supported keys within a configuration:
- `buildProject`: String, e.g., `my-project`
- `uri`: String, e.g., `{REGION}-docker.pkg.dev/my-project/my-repo/my-image`
""",
  )
