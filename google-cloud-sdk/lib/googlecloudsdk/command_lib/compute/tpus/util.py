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


from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.services import exceptions
from googlecloudsdk.api_lib.services import peering
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.projects import util as projects_command_util
from googlecloudsdk.command_lib.util.apis import resource_arg_schema
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs as presentation_specs_lib
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
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


_PROJECT_LOOKUP_ERROR = ('Error determining VPC peering status '
                         'for network [{}]: [{}]')
_PEERING_VALIDATION_ERROR = ('Network [{}] is invalid for use '
                             'with Service Networking')


class ServiceNetworkingException(core_exceptions.Error):
  """Exception for creation failures involving Service Networking/Peering."""


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


def _ParseProjectNumberFromNetwork(network, user_project):
  """Retrieves the project field from the provided network value."""
  try:
    registry = resources.REGISTRY.Clone()
    network_ref = registry.Parse(network,
                                 collection='compute.networks')
    project_identifier = network_ref.project
  except resources.Error:
    # If not a parseable resource string, then use user_project
    project_identifier = user_project

  return projects_command_util.GetProjectNumber(project_identifier)


def CreateValidateVPCHook(ref, args, request):
  """Validates that supplied network has been peered to a GoogleOrganization.

     Uses the Service Networking API to check if the network specified via
     --network flag has been peered to Google Organization. If it has, proceeds
     with TPU create operation otherwise will raise ServiceNetworking exception.
     Check is only valid if --use-service-networking has been specified
     otherwise check will return immediately.

  Args:
    ref: Reference to the TPU Node resource to be created.
    args: Argument namespace.
    request: TPU Create requests message.

  Returns:
    request: Passes requests through if args pass validation

  Raises:
    ServiceNetworkingException: if network is not properly peered
  """
  del ref
  service_networking_enabled = args.use_service_networking
  if service_networking_enabled:
    project = args.project or properties.VALUES.core.project.Get(required=True)
    try:
      network_project_number = _ParseProjectNumberFromNetwork(args.network,
                                                              project)

      lookup_result = peering.ListConnections(
          network_project_number, 'servicenetworking.googleapis.com',
          args.network)
    except (exceptions.ListConnectionsPermissionDeniedException,
            apitools_exceptions.HttpError) as e:
      raise ServiceNetworkingException(
          _PROJECT_LOOKUP_ERROR.format(args.network, project, e))

    if not lookup_result:
      raise ServiceNetworkingException(
          _PEERING_VALIDATION_ERROR.format(args.network))

  return request
