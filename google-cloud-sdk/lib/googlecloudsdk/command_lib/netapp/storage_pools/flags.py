# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the Cloud NetApp Files Storage Pools commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.netapp import netapp_client
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.netapp import flags
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.command_lib.util.concepts import concept_parsers

STORAGE_POOLS_LIST_FORMAT = """\
    table(
        name.basename():label=STORAGE_POOL_NAME:sort=1,
        name.segment(3):label=LOCATION,
        serviceLevel,
        capacityGib,
        state,
        stateDetails,
        createTime.date(),
        description,
        volumeCount,
        volumeCapacityGib,
        labels
    )"""

## Helper functions to add args / flags for Storage Pools gcloud commands ##


def GetStoragePoolServiceLevelArg(messages, required=True):
  """Adds a --service-level arg to the given parser.

  Args:
    messages: The messages module.
    required: bool, whether choice arg is required or not

  Returns:
    the choice arg.
  """
  service_level_arg = (
      arg_utils.ChoiceEnumMapper(
          '--service-level',
          messages.StoragePool.ServiceLevelValueValuesEnum,
          help_str="""The service level for the Cloud NetApp Storage Pool.
       For more details, see:
       https://cloud.google.com/architecture/partners/netapp-cloud-volumes/service-levels
        """,
          custom_mappings={
              'PREMIUM': ('premium',
                          """Premium Service Level for Cloud NetApp Storage Pool.
                   The Premium Service Level has a throughput per TiB of
                   allocated volume size of 64 MiB/s."""),
              'EXTREME': ('extreme',
                          """Extreme Service Level for Cloud NetApp Storage Pool.
                  The Extreme Service Level has a throughput per TiB of
                  allocated volume size of 128 MiB/s."""),
          },
          required=required))
  return service_level_arg


def AddStoragePoolServiceLevelArg(parser, messages, required=False):
  GetStoragePoolServiceLevelArg(
      messages, required=required).choice_arg.AddToParser(parser)


def AddStoragePoolAsyncFlag(parser):
  help_text = """Return immediately, without waiting for the operation
  in progress to complete."""
  concepts.ResourceParameterAttributeConfig(name='async', help_text=help_text)
  base.ASYNC_FLAG.AddToParser(parser)


## Helper functions to combine Storage Pools args / flags for gcloud commands ##


def AddStoragePoolCreateArgs(parser, release_track):
  """Add args for creating a Storage Pool."""
  concept_parsers.ConceptParser([
      flags.GetStoragePoolPresentationSpec('The Storage Pool to create.')
  ]).AddToParser(parser)
  flags.AddResourceDescriptionArg(parser, 'Storage Pool')
  flags.AddResourceCapacityArg(parser, 'Storage Pool')
  flags.AddResourceAsyncFlag(parser)
  labels_util.AddCreateLabelsFlags(parser)
  messages = netapp_client.GetMessagesModule(release_track=release_track)
  AddStoragePoolServiceLevelArg(parser, messages=messages, required=True)


def AddStoragePoolDeleteArgs(parser):
  """Add args for deleting a Storage Pool."""
  concept_parsers.ConceptParser([
      flags.GetStoragePoolPresentationSpec('The Storage Pool to delete.')
  ]).AddToParser(parser)
  flags.AddResourceAsyncFlag(parser)


def AddStoragePoolUpdateArgs(parser):
  """Add args for updating a Storage Pool."""
  concept_parsers.ConceptParser([
      flags.GetStoragePoolPresentationSpec('The Storage Pool to update.')
  ]).AddToParser(parser)
  flags.AddResourceDescriptionArg(parser, 'Storage Pool')
  flags.AddResourceAsyncFlag(parser)
  flags.AddResourceCapacityArg(parser, 'Storage Pool', required=False)
  labels_util.AddUpdateLabelsFlags(parser)
