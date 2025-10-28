# -*- coding: utf-8 -*- #
# Copyright 2017 Google LLC. All Rights Reserved.
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

import datetime

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute import scope as compute_scope
from googlecloudsdk.command_lib.compute.instances import flags as instance_flags
from googlecloudsdk.command_lib.compute.reservations import flags as reservation_flags
from googlecloudsdk.command_lib.compute.reservations import resource_args
from googlecloudsdk.command_lib.util.apis import arg_utils
import pytz


VALID_PLANS = ['12-month', '36-month']
EXTENDED_VALID_PLANS = ['12-month', '24-month', '36-month', '60-month']
VALID_UPDATE_PLANS = ['36-month']
EXTENDED_VALID_UPDATE_PLANS = ['24-month', '36-month', '60-month']
RFC3339_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
DATE_ONLY_FORMAT = '%Y-%m-%d'
_REQUIRED_RESOURCES = sorted(['vcpu', 'memory'])


class RegionCommitmentsCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(RegionCommitmentsCompleter, self).__init__(
        collection='compute.regionCommitments',
        list_command='alpha compute commitments list --uri',
        **kwargs
    )


def _GetFlagToPlanMap(messages):
  result = {
      '12-month': messages.Commitment.PlanValueValuesEnum.TWELVE_MONTH,
      '36-month': messages.Commitment.PlanValueValuesEnum.THIRTY_SIX_MONTH,
  }
  if hasattr(messages.Commitment.PlanValueValuesEnum, 'TWENTY_FOUR_MONTH'):
    result['24-month'] = (
        messages.Commitment.PlanValueValuesEnum.TWENTY_FOUR_MONTH
    )
  if hasattr(messages.Commitment.PlanValueValuesEnum, 'SIXTY_MONTH'):
    result['60-month'] = messages.Commitment.PlanValueValuesEnum.SIXTY_MONTH
  return result


def TranslatePlanArg(messages, plan_arg):
  return _GetFlagToPlanMap(messages)[plan_arg]


def TranslateAutoRenewArgForCreate(args):
  if args.IsSpecified('auto_renew'):
    return args.auto_renew
  return False


def TranslateAutoRenewArgForUpdate(args):
  if args.IsSpecified('auto_renew'):
    return args.auto_renew
  return None


def TranslateCustomEndTimeArg(args):
  """Translates the custom end time arg to a RFC3339 format."""
  if args.IsSpecified('custom_end_time'):
    # make sure if along with the RFC3339 format.
    try_date_only_parse = False
    final_date_time = None
    try:
      datetime.datetime.strptime(args.custom_end_time, RFC3339_FORMAT)
      final_date_time = args.custom_end_time
    except ValueError:
      # Swallow the exception and try to parse the date string in the format of
      # YYYY-MM-DD
      try_date_only_parse = True

    if try_date_only_parse:
      try:
        # try to parse the date string in the format of YYYY-MM-DD
        tz = pytz.timezone('America/Los_Angeles')
        midnight_date_time_mtv = tz.localize(
            datetime.datetime.strptime(args.custom_end_time, DATE_ONLY_FORMAT)
        )
        final_date_time = midnight_date_time_mtv.astimezone(pytz.utc).strftime(
            RFC3339_FORMAT
        )
      except ValueError:
        # Swallow the exception and throw canonical one.
        pass

    if not final_date_time:
      raise ValueError(
          'Invalid custom end time. Expected format: YYYY-MM-DD or'
          ' YYYY-MM-DDTHH:MM:SSZ'
      )

    return final_date_time

  return None


def TranslateResourcesArg(messages, resources_arg):
  return [
      messages.ResourceCommitment(
          amount=resources_arg['vcpu'],
          type=messages.ResourceCommitment.TypeValueValuesEnum.VCPU,
      ),
      # Arg is in B API accepts values in MB.
      messages.ResourceCommitment(
          amount=resources_arg['memory'] // (1024 * 1024),
          type=messages.ResourceCommitment.TypeValueValuesEnum.MEMORY,
      ),
  ]


def TranslateResourcesArgGroup(messages, args):
  """Util functions to parse ResourceCommitments."""
  resources_arg = args.resources
  resources = TranslateResourcesArg(messages, resources_arg)

  if 'local-ssd' in resources_arg.keys():
    resources.append(
        messages.ResourceCommitment(
            amount=resources_arg['local-ssd'],
            type=messages.ResourceCommitment.TypeValueValuesEnum.LOCAL_SSD,
        )
    )

  if args.IsSpecified('resources_accelerator'):
    accelerator_arg = args.resources_accelerator
    resources.append(
        messages.ResourceCommitment(
            amount=accelerator_arg['count'],
            acceleratorType=accelerator_arg['type'],
            type=messages.ResourceCommitment.TypeValueValuesEnum.ACCELERATOR,
        )
    )

  return resources


def TranslateMergeArg(arg):
  """List arguments are delineated by a comma."""
  return arg.split(',') if arg else []


def MakeCommitmentArg(plural):
  return compute_flags.ResourceArgument(
      resource_name='commitment',
      completer=RegionCommitmentsCompleter,
      plural=plural,
      name='commitment',
      regional_collection='compute.regionCommitments',
      region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION,
  )


def AddCreateFlags(
    parser,
    support_share_setting=False,
    support_stable_fleet=False,
    support_existing_reservation=False,
    support_reservation_sharing_policy=False,
    support_60_month_plan=False,
    support_24_month_plan=False,
):
  """Add general arguments for `commitments create` flag."""
  AddPlanForCreate(parser, support_60_month_plan, support_24_month_plan)
  AddReservationArgGroup(
      parser,
      support_share_setting,
      support_stable_fleet,
      support_existing_reservation,
      support_reservation_sharing_policy,
  )
  AddResourcesArgGroup(parser)
  AddSplitSourceCommitment(parser)
  AddMergeSourceCommitments(parser)
  AddCustomEndTime(parser)


def AddUpdateFlags(
    parser, support_60_month_plan=False, support_24_month_plan=False
):
  """Add general arguments for `commitments update` flag."""
  AddAutoRenew(parser)
  AddPlanForUpdate(parser, support_60_month_plan, support_24_month_plan)


def AddPlanForCreate(parser, support_60_month_plan, support_24_month_plan):
  return parser.add_argument(
      '--plan',
      required=True,
      choices=EXTENDED_VALID_PLANS
      if support_60_month_plan or support_24_month_plan
      else VALID_PLANS,
      help='Duration of the commitment.',
  )


def AddPlanForUpdate(parser, support_60_month_plan, support_24_month_plan):
  return parser.add_argument(
      '--plan',
      required=False,
      choices=EXTENDED_VALID_UPDATE_PLANS
      if support_60_month_plan or support_24_month_plan
      else VALID_UPDATE_PLANS,
      help='Duration of the commitment.',
  )


def AddAutoRenew(parser):
  return parser.add_argument(
      '--auto-renew',
      action='store_true',
      default=False,
      help='Enable auto renewal for the commitment.',
  )


def AddLicenceBasedFlags(parser):
  """Add license based flags for `commitments create` flag."""
  parser.add_argument(
      '--license',
      required=True,
      help=(
          'Applicable license URI. For example: '
          '`https://www.googleapis.com/compute/v1/projects/suse-sap-cloud/global/licenses/sles-sap-12`'
      ),
  )  #  pylint:disable=line-too-long
  parser.add_argument(
      '--cores-per-license',
      required=False,
      type=str,
      help=(
          'Core range of the instance. Must be one of: `1-2`,'
          ' `3-4`, `5+`. Required for SAP licenses.'
      ),
  )
  parser.add_argument(
      '--amount', required=True, type=int, help='Number of licenses purchased.'
  )
  AddPlanForCreate(
      parser, support_60_month_plan=False, support_24_month_plan=False
  )


def AddSplitSourceCommitment(parser):
  return parser.add_argument(
      '--split-source-commitment',
      required=False,
      help=(
          'Creates the new commitment by splitting the specified '
          'source commitment and redistributing the specified resources.'
      ),
  )


def AddMergeSourceCommitments(parser):
  return parser.add_argument(
      '--merge-source-commitments',
      required=False,
      help=(
          'Creates the new commitment by merging the specified '
          'source commitments and combining their resources.'
      ),
  )


def AddCustomEndTime(parser):
  return parser.add_argument(
      '--custom-end-time',
      required=False,
      type=str,
      help=(
          "Specifies a custom future end date and extends the commitment's"
          ' ongoing term.'
      ),
  )


def AddResourcesArgGroup(parser):
  """Add the argument group for ResourceCommitment support in commitment."""
  resources_group = parser.add_group(
      'Manage the commitment for particular resources.', required=True
  )

  resources_help = """\
Resources to be included in the commitment. For details and examples of valid
specifications, refer to the
[custom machine type guide](https://cloud.google.com/compute/docs/instances/creating-instance-with-custom-machine-type#specifications).
*memory*::: The size of the memory, should include units (e.g. 3072MB or 9GB). If no units are specified, GB is assumed.
*vcpu*::: The number of the vCPU cores.
*local-ssd*::: The size of local SSD.
"""

  resources_group.add_argument(
      '--resources',
      help=resources_help,
      type=arg_parsers.ArgDict(
          spec={
              'vcpu': int,
              'local-ssd': int,
              'memory': arg_parsers.BinarySize(),
          }
      ),
  )
  accelerator_help = """\
Manage the configuration of the type and number of accelerator cards to include in the commitment.
*count*::: The number of accelerators to include.
*type*::: The specific type (e.g. nvidia-tesla-k80 for NVIDIA Tesla K80) of the accelerator. Use `gcloud compute accelerator-types list` to learn about all available accelerator types.
"""
  resources_group.add_argument(
      '--resources-accelerator',
      help=accelerator_help,
      type=arg_parsers.ArgDict(spec={'count': int, 'type': str}),
  )


def GetTypeMapperFlag(messages):
  """Helper to get a choice flag from the commitment type enum."""
  return arg_utils.ChoiceEnumMapper(
      '--type',
      messages.Commitment.TypeValueValuesEnum,
      help_str=(
          'Type of commitment. `memory-optimized` indicates that the '
          'commitment is for memory-optimized VMs.'
      ),
      default='general-purpose',
      include_filter=lambda x: x != 'TYPE_UNSPECIFIED',
  )


def AddUpdateReservationGroup(parser):
  """Add reservation arguments to the update-reservations command."""
  parent_reservations_group = parser.add_group(
      'Manage reservations that are attached to the commitment.', mutex=True
  )
  AddReservationsFromFileFlag(
      parent_reservations_group,
      custom_text="Path to a YAML file of two reservations' configuration.",
  )
  reservations_group = parent_reservations_group.add_group(
      'Specify source and destination reservations configuration.'
  )
  AddReservationArguments(reservations_group)
  reservation_flags.GetAcceleratorFlag('--source-accelerator').AddToParser(
      reservations_group
  )
  reservation_flags.GetAcceleratorFlag('--dest-accelerator').AddToParser(
      reservations_group
  )
  reservation_flags.GetLocalSsdFlag('--source-local-ssd').AddToParser(
      reservations_group
  )
  reservation_flags.GetLocalSsdFlag('--dest-local-ssd').AddToParser(
      reservations_group
  )

  # Add share-setting and share-with flags.
  reservation_flags.GetSharedSettingFlag('--source-share-setting').AddToParser(
      reservations_group
  )
  reservation_flags.GetShareWithFlag('--source-share-with').AddToParser(
      reservations_group
  )
  reservation_flags.GetSharedSettingFlag('--dest-share-setting').AddToParser(
      reservations_group
  )
  reservation_flags.GetShareWithFlag('--dest-share-with').AddToParser(
      reservations_group
  )
  return parser


def AddReservationArguments(parser):
  """Add --source-reservation and --dest-reservation arguments to parser."""
  help_text = """
{0} reservation configuration.
*reservation*::: Name of the {0} reservation to operate on.
*reservation-zone*:::  Zone of the {0} reservation to operate on.
*vm-count*::: The number of VM instances that are allocated to this reservation.
The value of this field must be an int in the range [1, 1000].
*machine-type*:::  The type of machine (name only) which has a fixed number of
vCPUs and a fixed amount of memory. This also includes specifying custom machine
type following `custom-number_of_CPUs-amount_of_memory` pattern, e.g. `custom-32-29440`.
*min-cpu-platform*::: Optional minimum CPU platform of the reservation to create.
*require-specific-reservation*::: Indicates whether the reservation can be consumed by VMs with "any reservation"
defined. If enabled, then only VMs that target this reservation by name using
`--reservation-affinity=specific` can consume from this reservation.
"""
  reservation_spec = {
      'reservation': str,
      'reservation-zone': str,
      'vm-count': int,
      'machine-type': str,
      'min-cpu-platform': str,
      'require-specific-reservation': bool,
  }

  parser.add_argument(
      '--source-reservation',
      type=arg_parsers.ArgDict(spec=reservation_spec),
      help=help_text.format('source'),
      required=True,
  )
  parser.add_argument(
      '--dest-reservation',
      type=arg_parsers.ArgDict(spec=reservation_spec),
      help=help_text.format('destination'),
      required=True,
  )
  return parser


def AddReservationsFromFileFlag(parser, custom_text=None):
  help_text = (
      custom_text
      if custom_text
      else "Path to a YAML file of multiple reservations' configuration."
  )
  return parser.add_argument(
      '--reservations-from-file',
      type=arg_parsers.FileContents(),
      help=help_text,
  )


def AddExistingReservationFlag(parser):
  """Add --existing-reservation argument to parser."""
  help_text = """
  Details of the existing on-demand reservation or auto-created future
  reservation that you want to attach to your commitment. Specify a new instance
  of this flag for every existing reservation that you want to attach. The
  reservations must be in the same region as the commitment.
  *name*::: The name of the reservation.
  *zone*::: The zone of the reservation.
  For example, to attach an existing reservation named reservation-name in the
  zone reservation-zone, use the following text:
  --existing-reservation=name=reservation-name,zone=reservation-zone
  """
  return parser.add_argument(
      '--existing-reservation',
      type=arg_parsers.ArgDict(
          spec={'name': str, 'zone': str}, required_keys=['name', 'zone']
      ),
      action='append',
      help=help_text,
  )


def ResolveExistingReservationArgs(args, resources):
  """Method to translate existing-reservations args into URLs."""
  resolver = compute_flags.ResourceResolver.FromMap(
      'reservation', {compute_scope.ScopeEnum.ZONE: 'compute.reservations'}
  )
  existing_reservations = getattr(args, 'existing_reservation', None)
  if existing_reservations is None:
    return []
  reservation_urls = []
  for reservation in existing_reservations:
    reservation_ref = resolver.ResolveResources(
        [reservation['name']],
        compute_scope.ScopeEnum.ZONE,
        reservation['zone'],
        resources,
    )[0]
    reservation_urls.append(reservation_ref.SelfLink())
  return reservation_urls


def AddReservationArgGroup(
    parser,
    support_share_setting=False,
    support_stable_fleet=False,
    support_existing_reservations=False,
    support_reservation_sharing_policy=False,
):
  """Adds all flags needed for reservations creation."""
  reservations_manage_group = parser.add_group(
      'Manage the reservations to be created with the commitment.', mutex=True
  )

  AddReservationsFromFileFlag(reservations_manage_group)
  if support_existing_reservations:
    AddExistingReservationFlag(reservations_manage_group)

  single_reservation_group = reservations_manage_group.add_argument_group(
      help='Manage the reservation to be created with the commitment.'
  )
  resource_args.GetReservationResourceArg(positional=False).AddArgument(
      single_reservation_group
  )
  single_reservation_group.add_argument(
      '--reservation-type',
      hidden=True,
      choices=['specific'],
      default='specific',
      help='The type of the reservation to be created.',
  )

  specific_sku_reservation_group = single_reservation_group.add_argument_group(
      help='Manage the specific SKU reservation properties to create.'
  )
  AddFlagsToSpecificSkuGroup(
      specific_sku_reservation_group, support_stable_fleet
  )

  if support_share_setting:
    share_setting_reservation_group = (
        single_reservation_group.add_argument_group(
            help='Manage the properties of a shared reservation to create',
            required=False,
        )
    )
    AddFlagsToShareSettingGroup(share_setting_reservation_group)

  if support_reservation_sharing_policy:
    reservation_sharing_policy_group = single_reservation_group.add_argument_group(
        help='Manage the properties of a reservation sharing policy to create',
        required=False,
    )
    AddFlagsToReservationSharingPolicyGroup(reservation_sharing_policy_group)


def AddFlagsToReservationSharingPolicyGroup(group):
  """Adds flags needed for a reservation sharing policy."""
  args = [
      reservation_flags.GetReservationSharingPolicyFlag(),
  ]
  for arg in args:
    arg.AddToParser(group)


def AddFlagsToSpecificSkuGroup(group, support_stable_fleet=False):
  """Adds flags needed for a specific sku zonal allocation."""
  args = [
      reservation_flags.GetRequireSpecificAllocation(),
      reservation_flags.GetVmCountFlag(required=False),
      reservation_flags.GetMinCpuPlatform(),
      reservation_flags.GetMachineType(required=False),
      reservation_flags.GetLocalSsdFlag(),
      reservation_flags.GetAcceleratorFlag(),
      reservation_flags.GetResourcePolicyFlag(),
  ]

  if support_stable_fleet:
    args.append(instance_flags.AddMaintenanceInterval())

  for arg in args:
    arg.AddToParser(group)


def AddFlagsToShareSettingGroup(group):
  """Adds flags needed for an allocation with share setting."""
  args = [
      reservation_flags.GetSharedSettingFlag(),
      reservation_flags.GetShareWithFlag(),
  ]

  for arg in args:
    arg.AddToParser(group)
