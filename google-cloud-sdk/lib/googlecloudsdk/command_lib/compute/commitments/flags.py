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

"""Flags and helpers for the compute commitments commands."""

from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.util.apis import arg_utils

VALID_PLANS = ['12-month', '36-month']
_REQUIRED_RESOURCES = sorted(['VCPU', 'MEMORY'])


class RegionCommitmentsCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(RegionCommitmentsCompleter, self).__init__(
        collection='compute.regionCommitments',
        list_command='alpha compute commitments list --uri',
        **kwargs)


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
          amount=resources_arg['MEMORY'] // (1024 * 1024),
          type=messages.ResourceCommitment.TypeValueValuesEnum.MEMORY,
      ),
  ]


def MakeCommitmentArg(plural):
  return compute_flags.ResourceArgument(
      resource_name='commitment',
      completer=RegionCommitmentsCompleter,
      plural=plural,
      name='commitment',
      regional_collection='compute.regionCommitments',
      region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION)


def AddCreateFlags(parser):
  """Add general arguments for `commitments create` flag."""
  parser.add_argument('--plan',
                      required=True,
                      choices=VALID_PLANS,
                      help=('Duration of the commitment.'))
  resources_help = """\
  Resources to be included in the commitment commitment:
  * MEMORY should include unit (eg. 3072MB or 9GB). If no units are specified,
    GB is assumed.
  * VCPU is number of committed cores.
  Ratio between number of VCPU cores and memory must conform to limits
  described on:
  https://cloud.google.com/compute/docs/instances/creating-instance-with-custom-machine-type"""
  parser.add_argument('--resources',
                      required=True,
                      help=resources_help,
                      metavar='RESOURCE=COMMITMENT',
                      type=arg_parsers.ArgDict(spec={
                          'VCPU': int,
                          'MEMORY': arg_parsers.BinarySize(),
                      }))


def GetTypeMapperFlag(messages):
  """Helper to get a choice flag from the commitment type enum."""
  return arg_utils.ChoiceEnumMapper(
      '--type',
      messages.Commitment.TypeValueValuesEnum,
      help_str=(
          'Type of commitment. `memory-optimized` indicates that the '
          'commitment is for memory-optimized VMs.'),
      default='general-purpose',
      include_filter=lambda x: x != 'TYPE_UNSPECIFIED')

