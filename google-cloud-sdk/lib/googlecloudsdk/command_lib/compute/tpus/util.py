# -*- coding: utf-8 -*- #
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
"""CLI Utilities for cloud tpu commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from collections import OrderedDict
import copy

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.util.apis import resource_arg_schema
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs as presentation_specs_lib
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import pkg_resources


TPU_NODE_COLLECTION = 'tpu.projects.locations.nodes'
TPU_LOCATION_COLLECTION = 'tpu.projects.locations'
TPU_OPERATION_COLLECTION = 'tpu.projects.locations.operations'
# Note: the URI segment which contains the zone is at position -3
LIST_FORMAT = """
      table(
      name.basename(),
      name.segment(-3):label=ZONE,
      acceleratorType.basename():label=ACCELERATOR_TYPE,
      networkEndpoints.map().extract(ipAddress,port).map().join(':').join(','):label=NETWORK_ENDPOINTS,
      network.basename():label=NETWORK,
      cidrBlock:label=RANGE,
      state:label=STATUS
      )
"""

TPU_YAML_RESOURCE_PATH = 'googlecloudsdk.command_lib.compute.tpus.resources'

TPU_YAML_SPEC_TEMPLATE = OrderedDict({
    'tpu': {
        'help_text': 'The name of the Cloud TPU.',
        'is_positional': True,
        'is_parent_resource': False,
        'removed_flags': [],
        'flag_name': 'tpu_id'
    },
    'tensorflowversion': {
        'help_text': 'The Tensorflow version to Reimage Cloud TPU with.',
        'is_positional': False,
        'is_parent_resource': False,
        'removed_flags': ['zone'],
        'flag_name': '--version'
    },
    'location': {
        'help_text': 'The zone the Cloud TPU lives in.',
        'is_positional': True,
        'is_parent_resource': False,
        'removed_flags': [],
        'flag_name': 'zone'
    }
})


def GetMessagesModule(version='v1'):
  return apis.GetMessagesModule('tpu', version)


def StartRequestHook(ref, args, request):
  """Declarative request hook for TPU Start command."""
  del ref
  del args
  start_request = GetMessagesModule().StartNodeRequest()
  request.startNodeRequest = start_request
  return request


def StopRequestHook(ref, args, request):
  """Declarative request hook for TPU Stop command."""
  del ref
  del args
  stop_request = GetMessagesModule().StopNodeRequest()
  request.stopNodeRequest = stop_request
  return request


def LoadTPUResourceSpecs(custom_help=None):
  """Read Yaml resource file and return a dict mapping name to resource spec."""
  resource_file_contents = pkg_resources.GetResource(TPU_YAML_RESOURCE_PATH,
                                                     'resources.yaml')
  if not resource_file_contents:
    raise calliope_exceptions.BadFileException(
        'Resources not found in path [{}]'.format(TPU_YAML_RESOURCE_PATH))

  resource_dict = yaml.load(resource_file_contents)
  resource_specs = []
  for resource_name in TPU_YAML_SPEC_TEMPLATE:
    spec = resource_dict.get(resource_name, None)
    if not spec:
      raise ValueError(
          'Resource spec [{}] not found in resource spec {}.yaml'.format(
              resource_name, TPU_YAML_RESOURCE_PATH))

    # Don't modify template
    temp_spec = copy.deepcopy(TPU_YAML_SPEC_TEMPLATE[resource_name])

    temp_spec['spec'] = spec
    if custom_help and custom_help.get(resource_name):
      temp_spec['help_text'] = custom_help[resource_name]
    resource_specs.append(resource_arg_schema.YAMLResourceArgument.FromData(
        temp_spec))
  return resource_specs


def AddReimageResourcesToParser(parser):
  """Add TPU resource args to parser for reimage command."""
  custom_help = {
      'tpu': 'The Cloud TPU to reimage.'
  }

  resource_specs = LoadTPUResourceSpecs(custom_help)
  presentation_specs = []
  for arg in (spec for spec in resource_specs if spec.name in custom_help):
    presentation_specs.append(presentation_specs_lib.ResourcePresentationSpec(
        TPU_YAML_SPEC_TEMPLATE[arg.name]['flag_name'],
        arg.GenerateResourceSpec(),
        arg.group_help,
        flag_name_overrides={
            n: '' for n in TPU_YAML_SPEC_TEMPLATE[arg.name]['removed_flags']
        },
        required=True))
  concept_parsers.ConceptParser(presentation_specs).AddToParser(parser)
  # Not using Tensorflow resource arg here due to parsing conflict with zone
  # attribute and its ultimately passed only as string to API
  base.Argument(
      '--version',
      required=True,
      help='The Tensorflow version to Reimage Cloud TPU with.').AddToParser(
          parser)
