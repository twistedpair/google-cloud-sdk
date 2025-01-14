# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the Cloud NetApp Files Volume Replications commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.netapp import flags
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.concepts import concept_parsers


## Helper functions to add args / flags for Replications gcloud commands ##


def AddReplicationVolumeArg(parser, reverse_op=False):
  group_help = (
      'The Volume that the Replication is based on'
      if not reverse_op
      else 'The source Volume to reverse the Replication direction of'
  )
  concept_parsers.ConceptParser.ForResource(
      '--volume',
      flags.GetVolumeResourceSpec(positional=False),
      group_help=group_help,
      flag_name_overrides={'location': ''},
  ).AddToParser(parser)


def AddReplicationForceArg(parser):
  """Adds the --force arg to the arg parser."""
  parser.add_argument(
      '--force',
      action='store_true',
      help="""Indicates whether to stop replication forcefully while data transfer is in progress.
      Warning! if force is true, this will abort any current transfers and can lead to data loss due to partial transfer.
      If force is false, stop replication will fail while data transfer is in progress and you will need to retry later.
      """,
  )


def GetReplicationReplicationScheduleEnumFromArg(choice, messages):
  """Returns the Choice Enum for Replication Schedule.

  Args:
    choice: The choice for replication schedule input as string.
    messages: The messages module.

  Returns:
    The replication schedule enum.
  """
  return arg_utils.ChoiceToEnum(
      choice=choice,
      enum_type=messages.Replication.ReplicationScheduleValueValuesEnum,
  )


def AddReplicationReplicationScheduleArg(parser, required=True):
  """Adds the Replication Schedule (--replication-schedule) arg to the given parser.

  Args:
    parser: Argparse parser.
    required: If the Replication Schedule is required. E.g. it is required by
      Create, but not required by Update.
  """
  parser.add_argument(
      '--replication-schedule',
      type=str,
      required=required,
      help='The schedule for the Replication.',
  )


def AddReplicationDestinationVolumeParametersArg(parser, messages):
  """Adds the Destination Volume Parameters (--destination-volume-parameters) arg to the given parser.

  Args:
    parser: Argparse parser.
    messages: The messages module.
  """
  destination_volume_parameters_spec = {
      'storage_pool': str,
      'volume_id': str,
      'share_name': str,
      'description': str,
      'tiering_policy': arg_parsers.ArgObject(
          spec={
              'tier-action': messages.TieringPolicy.TierActionValueValuesEnum,
              'cooling-threshold-days': int,
          },
          enable_shorthand=False,
      ),
  }

  destination_volume_parameters_help = """\
      """

  parser.add_argument(
      '--destination-volume-parameters',
      type=arg_parsers.ArgObject(
          spec=destination_volume_parameters_spec,
          required_keys=['storage_pool'],
      ),
      required=True,
      help=destination_volume_parameters_help,
  )


def AddReplicationClusterLocationArg(parser, hidden=False):
  """Adds the Cluster Location (--cluster-location) arg to the given parser.

  Args:
    parser: Argparse parser.
    hidden: If the Cluster Location is hidden.
  """
  parser.add_argument(
      '--cluster-location',
      type=str,
      required=False,
      help='Location of the user cluster.',
      hidden=hidden,
  )


def AddReplicationPeerClusterNameArg(parser, required=True):
  """Adds the Peer Cluster Name (--peer-cluster-name) arg to the given parser.

  Args:
    parser: Argparse parser.
    required: Required to establish both cluster and svm peering.
  """
  parser.add_argument(
      '--peer-cluster-name',
      type=str,
      required=required,
      help="""Name of the destination cluster to be peered with the source cluster.""",
  )


def AddReplicationPeerSvmNameArg(parser, required=True):
  """Adds the Peer SVM Name (--peer-svm-name) arg to the given parser.

  Args:
    parser: Argparse parser.
    required: Required to establish both cluster and svm peering.
  """
  parser.add_argument(
      '--peer-svm-name',
      type=str,
      required=required,
      help="""Name of the local source vserver svm to be peered with the destination cluster.""",
  )


def AddReplicationPeerVolumeNameArg(parser, required=True):
  """Adds the Peer Volume Name (--peer-volume-name) arg to the given parser.

  Args:
    parser: Argparse parser.
    required: Required to establish both cluster and svm peering.
  """
  parser.add_argument(
      '--peer-volume-name',
      type=str,
      required=required,
      help="""Name of the source volume to be peered with the destination volume.""",
  )


def AddReplicationPeerIpAddressesArg(parser):
  """Adds the Peer IP Addresses (--peer-ip-addresses) arg to the given parser.

  Args:
    parser: Argparse parser.

  Not required for svm peering.
  """
  parser.add_argument(
      '--peer-ip-addresses',
      type=arg_parsers.ArgList(min_length=1, element_type=str),
      metavar='PEER_IP_ADDRESS',
      help='List of ip addresses to be used for peering.',
  )
