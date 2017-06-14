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

"""Flags and helpers for the compute commitments commands."""

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags as compute_flags

VALID_PLANS = ['12-month', '36-month']
_REQUIRED_RESOURCES = sorted(['VCPU', 'MEMORY'])


def _GetFlagToPlanMap(messages):
  return {
      '12-month': messages.Commitment.PlanValueValuesEnum.TWELVE_MONTH,
      '36-month': messages.Commitment.PlanValueValuesEnum.THIRTY_SIX_MONTH,
  }


def TranslatePlanArg(messages, plan_arg):
  return _GetFlagToPlanMap(messages)[plan_arg]


def ValidateResourcesArg(resources_arg):
  if (resources_arg is None or
      sorted(resources_arg.keys()) != _REQUIRED_RESOURCES):
    raise exceptions.InvalidArgumentException(
        '--resources', 'You must specify the following resources: {}.'.format(
            ', '.join(_REQUIRED_RESOURCES)))


def TranslateResourcesArg(messages, resources_arg):
  return [
      messages.ResourceCommitment(
          amount=resources_arg['VCPU'],
          type=messages.ResourceCommitment.TypeValueValuesEnum.VCPU,
      ),
      # Arg is in B API accepts values in MB.
      messages.ResourceCommitment(
          amount=resources_arg['MEMORY'] / (1024 * 1024),
          type=messages.ResourceCommitment.TypeValueValuesEnum.MEMORY,
      ),
  ]


def MakeCommitmentArg(plural):
  return compute_flags.ResourceArgument(
      resource_name='commitment',
      completion_resource_id='compute.regionCommitments',
      plural=plural,
      name='commitment',
      regional_collection='compute.regionCommitments',
      region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION)
