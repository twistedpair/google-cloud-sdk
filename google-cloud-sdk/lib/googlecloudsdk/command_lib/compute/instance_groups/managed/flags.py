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
"""Flags for the compute instance groups managed commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions

DEFAULT_CREATE_OR_LIST_FORMAT = """\
    table(
      name,
      location():label=LOCATION,
      location_scope():label=SCOPE,
      baseInstanceName,
      size,
      targetSize,
      instanceTemplate.basename(),
      autoscaled
    )
"""


def AddTypeArg(parser):
  parser.add_argument(
      '--type',
      choices={
          'opportunistic': 'Do not proactively replace instances. Create new '
                           'instances and delete old on resizes of the group.',
          'proactive': 'Replace instances proactively.',
      },
      default='proactive',
      category=base.COMMONLY_USED_FLAGS,
      help='Desired update type.')


def AddMaxSurgeArg(parser):
  parser.add_argument(
      '--max-surge',
      type=str,
      help=('Maximum additional number of instances that '
            'can be created during the update process. '
            'This can be a fixed number (e.g. 5) or '
            'a percentage of size to the managed instance '
            'group (e.g. 10%). Defaults to 0 if the managed '
            'instance group has stateful configuration, or to '
            'the number of zones in which it operates otherwise.'))


def AddMaxUnavailableArg(parser):
  parser.add_argument(
      '--max-unavailable',
      type=str,
      help=('Maximum number of instances that can be '
            'unavailable during the update process. '
            'This can be a fixed number (e.g. 5) or '
            'a percentage of size to the managed instance '
            'group (e.g. 10%). Defaults to the number of zones '
            'in which the managed instance group operates.'))


def AddMinReadyArg(parser):
  parser.add_argument(
      '--min-ready',
      type=arg_parsers.Duration(lower_bound='0s'),
      help=('Minimum time for which a newly created instance '
            'should be ready to be considered available. For example `10s` '
            'for 10 seconds. See $ gcloud topic datetimes for information '
            'on duration formats.'))


def AddReplacementMethodFlag(parser):
  parser.add_argument(
      '--replacement-method',
      choices={
          'substitute':
              'Delete old instances and create instances with new names.',
          'recreate':
              'Recreate instances and preserve the instance names. '
              'The instance IDs and creation timestamps might change.',
      },
      help="Type of replacement method. Specifies what action will be taken "
           "to update instances. Defaults to ``recreate'' if the managed "
           "instance group has stateful configuration, or to ``substitute'' "
           "otherwise.")


def AddForceArg(parser):
  parser.add_argument(
      '--force',
      action='store_true',
      help=('If set, accepts any original or new version '
            'configurations without validation.'))


INSTANCE_ACTION_CHOICES_WITHOUT_NONE = collections.OrderedDict([
    ('refresh', "Apply the new configuration without stopping instances, "
                "if possible. For example, use ``refresh'' to apply changes "
                "that only affect metadata or additional disks."),
    ('restart', 'Apply the new configuration without replacing instances, '
                'if possible. For example, stopping instances and starting '
                'them again is sufficient to apply changes to machine type.'),
    ('replace', "Replace old instances according to the "
                "``--replacement-method'' flag.")
])


def _CombineOrderedChoices(choices1, choices2):
  merged = collections.OrderedDict([])
  merged.update(choices1.items())
  merged.update(choices2.items())
  return merged


INSTANCE_ACTION_CHOICES_WITH_NONE = _CombineOrderedChoices(
    {'none': 'No action'}, INSTANCE_ACTION_CHOICES_WITHOUT_NONE)


def AddMinimalActionArg(parser, choices_with_none=True, default=None):
  choices = (INSTANCE_ACTION_CHOICES_WITH_NONE if choices_with_none
             else INSTANCE_ACTION_CHOICES_WITHOUT_NONE)
  parser.add_argument(
      '--minimal-action',
      choices=choices,
      default=default,
      help="""Use this flag to minimize disruption as much as possible or to
        apply a more disruptive action than is strictly necessary.
        The MIG performs at least this action on each instance while
        updating. If the update requires a more disruptive action than
        the one specified here, then the more disruptive action is
        performed. If you omit this flag, the update uses the
        ``minimal-action'' value from the MIG\'s update policy, unless it
        is not set in which case the default is ``replace''.""")


def AddMostDisruptiveActionArg(parser, choices_with_none=True, default=None):
  choices = (INSTANCE_ACTION_CHOICES_WITH_NONE if choices_with_none
             else INSTANCE_ACTION_CHOICES_WITHOUT_NONE)
  parser.add_argument(
      '--most-disruptive-allowed-action',
      choices=choices,
      default=default,
      help="""Use this flag to prevent an update if it requires more disruption
        than you can afford. At most, the MIG performs the specified
        action on each instance while updating. If the update requires
        a more disruptive action than the one specified here, then
        the update fails and no changes are made. If you omit this flag,
        the update uses the ``most-disruptive-allowed-action'' value from
        the MIG\'s update policy, unless it is not set in which case
        the default is ``replace''.""")


def AddUpdateInstancesArgs(parser):
  """Add args for the update-instances command."""
  instance_selector_group = parser.add_group(required=True, mutex=True)
  instance_selector_group.add_argument(
      '--instances',
      type=arg_parsers.ArgList(min_length=1),
      metavar='INSTANCE',
      required=False,
      help='Names of instances to update.')
  instance_selector_group.add_argument(
      '--all-instances',
      required=False,
      action='store_true',
      help='Update all instances in the group.')
  AddMinimalActionArg(parser, True, 'none')
  AddMostDisruptiveActionArg(parser, True, 'replace')


def AddGracefulValidationArg(parser):
  help_text = """Specifies whether the request should proceed even if the
    request includes instances that are not members of the group or that are
    already being deleted or abandoned. By default, if you omit this flag and
    such an instance is specified in the request, the operation fails. The
    operation always fails if the request contains a badly formatted instance
    name or a reference to an instance that exists in a zone or region other
    than the group's zone or region."""
  parser.add_argument(
      '--skip-instances-on-validation-error',
      action='store_true',
      help=help_text)


def GetCommonPerInstanceCommandOutputFormat(with_validation_error=False):
  if with_validation_error:
    return """
        table(project(),
              zone(),
              instanceName:label=INSTANCE,
              status,
              validationError:label=VALIDATION_ERROR)"""
  else:
    return """
        table(project(),
              zone(),
              instanceName:label=INSTANCE,
              status)"""


INSTANCE_REDISTRIBUTION_TYPES = ['NONE', 'PROACTIVE']


def AddMigInstanceRedistributionTypeFlag(parser):
  """Add --instance-redistribution-type flag to the parser."""
  parser.add_argument(
      '--instance-redistribution-type',
      metavar='TYPE',
      type=lambda x: x.upper(),
      choices=INSTANCE_REDISTRIBUTION_TYPES,
      help="""\
      Specifies the type of the instance redistribution policy. An instance
      redistribution type lets you enable or disable automatic instance
      redistribution across zones to meet the group's target distribution shape.

      An instance redistribution type can be specified only for a non-autoscaled
      regional managed instance group. By default it is set to PROACTIVE.

      The following types are available:

       * NONE - The managed instance group does not redistribute instances
         across zones.

       * PROACTIVE - The managed instance group proactively redistributes
         instances to meet its target distribution.
      """)


DISTRIBUTION_POLICY_TARGET_SHAPE_CHOICES = {
    'EVEN':
        'The group schedules VM instance creation and deletion to achieve and '
        'maintain an even number of managed instances across the selected '
        'zones. The distribution is even when the number of managed instances '
        'does not differ by more than 1 between any two zones. Recommended for'
        ' highly available serving workloads.',
    'BALANCED':
        'The group prioritizes acquisition of resources, scheduling VMs in '
        'zones where resources are available while distributing VMs as evenly '
        'as possible across selected zones to minimize the impact of zonal '
        'failure. Recommended for highly available serving or batch workloads '
        'that do not require autoscaling.',
    'ANY': 'The group picks zones for creating VM instances to fulfill the '
           'requested number of VMs within present resource constraints and to '
           'maximize utilization of unused zonal reservations. Recommended for '
           'batch workloads that do not require high availability.'
}


def AddMigDistributionPolicyTargetShapeFlag(parser):
  """Add --target-distribution-shape flag to the parser."""
  help_text = """\
      Specifies how a regional managed instance group distributes its instances
      across zones within the region. The default shape is ``EVEN''.
    """

  parser.add_argument(
      '--target-distribution-shape',
      metavar='SHAPE',
      type=lambda x: x.upper(),
      choices=DISTRIBUTION_POLICY_TARGET_SHAPE_CHOICES,
      help=help_text)


def AddFlagsForUpdateAllInstancesConfig(parser):
  """Adds args for all-instances' config update command."""
  # Add  metadata args
  metadata_argument_name = '--metadata'
  metadata_help_text = ("Add metadata to the group's all instances "
                        "configuration.")
  parser.add_argument(
      metadata_argument_name,
      type=arg_parsers.ArgDict(min_length=1),
      default={},
      action=arg_parsers.StoreOnceAction,
      metavar='KEY=VALUE',
      help=metadata_help_text)
  # Add labels args
  labels_argument_name = '--labels'
  metadata_help_text = "Add labels to the group's all instances configuration."
  parser.add_argument(
      labels_argument_name,
      type=arg_parsers.ArgDict(min_length=1),
      default={},
      action=arg_parsers.StoreOnceAction,
      metavar='KEY=VALUE',
      help=metadata_help_text)


def AddFlagsForDeleteAllInstancesConfig(parser):
  """Adds args for all-instances' config delete command."""
  # Add  metadata args
  metadata_argument_name = '--metadata'
  parser.add_argument(
      metadata_argument_name,
      metavar='KEY',
      type=arg_parsers.ArgList(min_length=1),
      help="Remove metadata keys from the group's all instances configuration."
  )
  # Add labels args
  labels_argument_name = '--labels'
  parser.add_argument(
      labels_argument_name,
      metavar='KEY',
      type=arg_parsers.ArgList(min_length=1),
      help="Remove labels keys from the group's all instances configuration.")


def ValidateRegionalMigFlagsUsage(args, regional_flags_dests, igm_ref):
  """For zonal MIGs validate that user did not supply any RMIG-specific flags.

  Can be safely called from GA track for all flags, unknowns are ignored.

  Args:
    args: provided arguments.
    regional_flags_dests: list of RMIG-specific flag dests (names of the
      attributes used to store flag values in args).
    igm_ref: resource reference of the target IGM.
  """
  if igm_ref.Collection() == 'compute.regionInstanceGroupManagers':
    return
  for dest in regional_flags_dests:
    if args.IsKnownAndSpecified(dest):
      flag_name = args.GetFlag(dest)
      error_message = ('Flag %s may be specified for regional managed instance '
                       'groups only.') % flag_name
      raise exceptions.InvalidArgumentException(
          parameter_name=flag_name, message=error_message)
