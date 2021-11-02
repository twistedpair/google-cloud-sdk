# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Flags for data-catalog commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import sys

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs


FILTER_FLAG_NO_SORTBY_DOC = base.Argument(
    '--filter',
    metavar='EXPRESSION',
    require_coverage_in_tests=False,
    category=base.LIST_COMMAND_FLAGS,
    help="""\
    Apply a Boolean filter _EXPRESSION_ to each resource item to be listed.
    If the expression evaluates `True`, then that item is listed. For more
    details and examples of filter expressions, run $ gcloud topic filters. This
    flag interacts with other flags that are applied in this order: *--flatten*,
    *--filter*, *--limit*.""")


LIMIT_FLAG_NO_SORTBY_DOC = base.Argument(
    '--limit',
    type=arg_parsers.BoundedInt(1, sys.maxsize, unlimited=True),
    require_coverage_in_tests=False,
    category=base.LIST_COMMAND_FLAGS,
    help="""\
    Maximum number of resources to list. The default is *unlimited*.
    This flag interacts with other flags that are applied in this order:
    *--flatten*, *--filter*, *--limit*.
    """)


def AddInstanceArgToParser(parser, positional=False):
  """Sets up an argument for the instance resource."""
  if positional:
    name = 'instance'
  else:
    name = '--instance'
  instance_data = yaml_data.ResourceYAMLData.FromPath(
      'bms.instance')
  resource_spec = concepts.ResourceSpec.FromYaml(instance_data.GetData())
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=True,
      group_help='instance.')
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddRegionArgToParser(parser, positional=False):
  """Parses region flag."""
  region_data = yaml_data.ResourceYAMLData.FromPath('bms.region')
  resource_spec = concepts.ResourceSpec.FromYaml(region_data.GetData())
  if positional:
    name = 'region'
  else:
    name = '--region'
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=False,
      group_help='region.')
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)

def AddVolumeArgToParser(parser, positional=False):
  """Sets up an argument for the instance resource."""
  if positional:
    name = 'volume'
  else:
    name = '--volume'
  volume_data = yaml_data.ResourceYAMLData.FromPath(
      'bms.volume')
  resource_spec = concepts.ResourceSpec.FromYaml(volume_data.GetData())
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=True,
      group_help='volume.')
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddSnapshotSchedulePolicyArgToParser(parser, positional=False):
  """Sets up an argument for the snapshot schedule policy resource."""
  if positional:
    name = 'snapshot_schedule_policy'
  else:
    name = '--snapshot-schedule-policy'
  policy_data = yaml_data.ResourceYAMLData.FromPath(
      'bms.snapshot_schedule_policy')
  resource_spec = concepts.ResourceSpec.FromYaml(policy_data.GetData())
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=True,
      flag_name_overrides={'region': ''},
      group_help='snapshot_schedule_policy.')
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddNetworkArgToParser(parser, positional=False):
  """Sets up an argument for the network resource."""
  if positional:
    name = 'network'
  else:
    name = '--network'
  policy_data = yaml_data.ResourceYAMLData.FromPath(
      'bms.network')
  resource_spec = concepts.ResourceSpec.FromYaml(policy_data.GetData())
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=True,
      group_help='network.')

  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddLunArgToParser(parser):
  """Sets up an argument for a volume snapshot policy."""
  name = 'lun'
  snapshot_data = yaml_data.ResourceYAMLData.FromPath('bms.lun')
  resource_spec = concepts.ResourceSpec.FromYaml(snapshot_data.GetData())
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name=name,
      concept_spec=resource_spec,
      required=True,
      group_help='lun.')
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)
