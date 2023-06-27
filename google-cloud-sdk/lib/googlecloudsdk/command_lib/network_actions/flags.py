# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Common flags for network-actions resources."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import textwrap

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.network_actions import util
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs


def AddWasmPluginResource(parser, api_version):
  wasm_plugin_data = yaml_data.ResourceYAMLData.FromPath(
      'network_actions.wasmPlugin')
  concept_parsers.ConceptParser(
      [
          presentation_specs.ResourcePresentationSpec(
              'wasm_plugin',
              concepts.ResourceSpec.FromYaml(
                  wasm_plugin_data.GetData(),
                  api_version=api_version,
              ),
              'The ID of the WasmPlugin to create.',
              required=True,
          )
      ],
  ).AddToParser(parser)


def AddDescriptionFlag(parser):
  parser.add_argument(
      '--description',
      help='Provides an optional, human-'
      'readable description of the service.')


def AddLogConfigFlag(parser):
  parser.add_argument(
      '--log-config',
      action='append',
      type=util.LogConfig(),
      required=False,
      metavar='LOG_CONFIG',
      help=textwrap.dedent("""\
        Logging options for the activity performed by this WasmPlugin.
        Following options can be set:
        * enable - whether to enable logging. If log-config flag is set,
          enable option is required.

        * sample-rate - configures the sampling rate of activity logs, where
          1.0 means all logged activity is reported and 0.0 means no activity
          is reported. The default value is 1.0, and the value of the field
          must be in [0, 1].

        * min-log-level - specificies the lowest level of the logs which
          should be exported to Cloud Logging. The default value is INFO.

        Example usage:
        --log-config=enable=True,sample-rate=0.5,min-log-level=INFO
        --log_config=enable=False
        """),
  )


def AddVersionFlag(parser):
  parser.add_argument(
      '--main-version',
      help=textwrap.dedent("""\
          ID of the WasmPluginVersion that will be created for that
          WasmPlugin and that will be set as the current main version."""),
  )


def AddImageFlag(parser):
  parser.add_argument(
      '--image',
      help=textwrap.dedent("""\
          URI of the container image containing the Wasm module, stored in the
          Artifact Registry."""),
  )


def AddWasmPluginVersionArgs(parser):
  wasm_plugin_version_group = parser.add_group(mutex=False, required=False)
  AddVersionFlag(wasm_plugin_version_group)
  AddImageFlag(wasm_plugin_version_group)
