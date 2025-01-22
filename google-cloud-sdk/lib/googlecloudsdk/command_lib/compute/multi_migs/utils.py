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
"""Flags for the compute multi-migs commands."""

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.compute.resource_policies import util as resource_util
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs


def AddMultiMigNameArgToParser(parser, api_version=None):
  """Adds a multi-MIG name resource argument."""
  multi_mig_data = yaml_data.ResourceYAMLData.FromPath(
      'compute.multi_migs.multi_mig'
  )
  resource_spec = concepts.ResourceSpec.FromYaml(
      multi_mig_data.GetData(), is_positional=True, api_version=api_version
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name='multi_mig',
      concept_spec=resource_spec,
      required=True,
      group_help='Name of a multi-MIG.',
  )
  concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def MakeResourcePolicy(args, resource, messages, multi_mig_ref):
  if args.workload_policy:
    workload_policy_self_link = _MakeWorkloadPolicySelfLink(
        args.workload_policy, resource, multi_mig_ref
    )
    return messages.MultiMigResourcePolicies(
        workloadPolicy=workload_policy_self_link
    )
  return None


def _MakeWorkloadPolicySelfLink(workload_policy, resource, multi_mig_ref):
  workload_policy_ref = resource_util.ParseResourcePolicy(
      resource,
      workload_policy,
      project=multi_mig_ref.project,
      region=multi_mig_ref.region,
  )
  return workload_policy_ref.SelfLink()


DEFAULT_LIST_FORMAT = """
      table(
        name,
        resource_policies.workload_policy,
        region.basename(),
        creation_timestamp
      )"""

ALPHA_LIST_FORMAT = """
      table(
        name,
        resource_policies.workload_policy,
        region.basename(),
        status,
        creation_timestamp
      )"""
