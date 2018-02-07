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

"""Flags for the compute maintenance-policies commands."""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import flags as compute_flags


def MakeMaintenancePolicyArg():
  return compute_flags.ResourceArgument(
      resource_name='maintenance policy',
      regional_collection='compute.maintenancePolicies',
      region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION)


def AddCycleFrequencyArgs(parser):
  """Add Cycle Frequency args for Maintenance Policies."""
  freq_group = parser.add_argument_group('Cycle Frequency Group.')
  # More flags will be added in the future.
  freq_group.add_argument(
      '--days-in-cycle',
      type=arg_parsers.BoundedInt(1, 30, unlimited=False),
      default=1,
      # Currently the API only supports the value of 1. The flag will be
      # unhidden when more values are supported.
      hidden=True,
      required=False,
      help="""\
      Frequency in which maintenance activity runs in terms of days.
      """)


def AddCommonArgs(parser):
  parser.add_argument(
      '--description',
      help='Description of the maintenance policy.')
  parser.add_argument(
      '--start-time',
      type=arg_parsers.Datetime.Parse,
      required=True,
      help="""\
      Start time of a four-hour window in which maintenance activity should
      start in given cadence. Valid choices are 00:00, 04:00, 08:00,12:00,
      16:00 and 20:00 UTC. See $ gcloud topic datetimes for information on
      time formats. For example, `--start-time="03:00-05"`
      (which gets converted to 08:00 UTC).
      """)


def AddResourceMaintenancePolicyArgs(parser, action, required=False):
  parser.add_argument(
      # Bad name for now, but multiple policies will be supported in the future.
      '--resource-maintenance-policies',
      type=str,
      required=required,
      help=('Name of a maintenance policy to be {} the instance. '
            'The policy must exist in the same region as the instance.'
            .format(action)))
