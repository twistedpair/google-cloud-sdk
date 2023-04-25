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
"""Utility file that contains helpers for Queued Resources."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.compute import metadata_utils
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.core.util import times

import six


def GetMessagesModule(version='v2alpha1'):
  return apis.GetMessagesModule('tpu', version)


# TODO(b/276933950) Consider merging this MergeMetadata with
# googlecloudsdk.command_lib.compute.tpus.tpu_vm.util.MergeMetadata by moving
# it to googlecloudsdk.command_lib.compute.tpus.util
def MergeMetadata(args):
  """Creates the metadata for the Node.

  Based on googlecloudsdk.command_lib.compute.tpus.tpu_vm.util.MergeMetadata.

  Args:
    args:  The gcloud args

  Returns:
    The constructed MetadataValue.
  """
  metadata_dict = metadata_utils.ConstructMetadataDict(
      args.metadata, args.metadata_from_file
  )
  tpu_messages = GetMessagesModule()
  metadata = tpu_messages.Node.MetadataValue()
  for key, value in six.iteritems(metadata_dict):
    metadata.additionalProperties.append(
        tpu_messages.Node.MetadataValue.AdditionalProperty(key=key, value=value)
    )
  return metadata


def CreateNodeSpec(ref, args, request):
  """Creates the repeated structure nodeSpec from args."""
  tpu_messages = GetMessagesModule()
  if request.queuedResource is None:
    request.queuedResource = tpu_messages.QueuedResource()
  if request.queuedResource.tpu is None:
    request.queuedResource.tpu = tpu_messages.Tpu()

  request.queuedResource.tpu.nodeSpec = []
  node_spec = tpu_messages.NodeSpec()
  node_spec.parent = ref.Parent().RelativeName()

  node_spec.node = tpu_messages.Node()
  if args.accelerator_type:
    node_spec.node.acceleratorType = args.accelerator_type
  else:
    node_spec.node.acceleratorConfig = tpu_messages.AcceleratorConfig()
    node_spec.node.acceleratorConfig.topology = args.topology
    node_spec.node.acceleratorConfig.type = arg_utils.ChoiceToEnum(
        args.type, tpu_messages.AcceleratorConfig.TypeValueValuesEnum
    )

  node_spec.node.runtimeVersion = args.runtime_version
  if args.data_disk:
    node_spec.node.dataDisks = []
    for data_disk in args.data_disk:
      attached_disk = tpu_messages.AttachedDisk(
          sourceDisk=data_disk.sourceDisk, mode=data_disk.mode
      )
      node_spec.node.dataDisks.append(attached_disk)
  if args.description:
    node_spec.node.description = args.description
  if args.labels:
    node_spec.node.labels = tpu_messages.Node.LabelsValue()
    node_spec.node.labels.additionalProperties = []
    for key, value in args.labels.items():
      node_spec.node.labels.additionalProperties.append(
          tpu_messages.Node.LabelsValue.AdditionalProperty(key=key, value=value)
      )
  if args.range:
    node_spec.node.cidrBlock = args.range
  if args.shielded_secure_boot:
    node_spec.node.shieldedInstanceConfig = tpu_messages.ShieldedInstanceConfig(
        enableSecureBoot=True
    )

  node_spec.node.networkConfig = tpu_messages.NetworkConfig()
  node_spec.node.serviceAccount = tpu_messages.ServiceAccount()
  if args.network:
    node_spec.node.networkConfig.network = args.network
  if args.subnetwork:
    node_spec.node.networkConfig.subnetwork = args.subnetwork
  if args.service_account:
    node_spec.node.serviceAccount.email = args.service_account
  if args.scopes:
    node_spec.node.serviceAccount.scope = args.scopes
  if args.tags:
    node_spec.node.tags = args.tags
  node_spec.node.networkConfig.enableExternalIps = not args.internal_ips

  node_spec.node.metadata = MergeMetadata(args)

  if args.node_prefix and not args.node_count:
    raise exceptions.ConflictingArgumentsException(
        'Can only specify --node-prefix if --node-count is also specified.'
    )

  if args.node_id:
    node_spec.nodeId = args.node_id
  elif args.node_count:
    node_spec.multiNodeParams = tpu_messages.MultiNodeParams()
    node_spec.multiNodeParams.nodeCount = args.node_count
    if args.node_prefix:
      node_spec.multiNodeParams.nodeIdPrefix = args.node_prefix
  request.queuedResource.tpu.nodeSpec = [node_spec]

  return request


def VerifyNodeCount(ref, args, request):
  del ref  # unused
  if args.node_count and args.node_count <= 1:
    raise exceptions.InvalidArgumentException(
        '--node-count', 'Node count must be greater than 1'
    )
  return request


def SetBestEffort(ref, args, request):
  """Creates an empty BestEffort structure if arg flag is set."""
  del ref  # unused
  if args.best_effort:
    tpu_messages = GetMessagesModule()
    if request.queuedResource is None:
      request.queuedResource = tpu_messages.QueuedResource()
    if request.queuedResource.bestEffort is None:
      request.queuedResource.bestEffort = tpu_messages.BestEffort()

  return request


def SetGuaranteed(ref, args, request):
  """Creates an empty Guaranteed structure if arg flag is set."""
  del ref  # unused
  if args.guaranteed:
    tpu_messages = GetMessagesModule()
    if request.queuedResource is None:
      request.queuedResource = tpu_messages.QueuedResource()
    if request.queuedResource.guaranteed is None:
      request.queuedResource.guaranteed = tpu_messages.Guaranteed()

  return request


def SetValidInterval(ref, args, request):
  """Combine multiple timing constraints into a valid_interval."""
  del ref  # unused
  if (args.valid_after_duration and args.valid_after_time) or (
      args.valid_until_duration and args.valid_until_time
  ):
    raise exceptions.ConflictingArgumentsException(
        'Only one timing constraint for each of (start, end) time is permitted'
    )
  tpu_messages = GetMessagesModule()
  current_time = times.Now()

  start_time = None
  if args.valid_after_time:
    start_time = args.valid_after_time
  elif args.valid_after_duration:
    start_time = args.valid_after_duration.GetRelativeDateTime(current_time)

  end_time = None
  if args.valid_until_time:
    end_time = args.valid_until_time
  elif args.valid_until_duration:
    end_time = args.valid_until_duration.GetRelativeDateTime(current_time)

  if start_time and end_time:
    valid_interval = tpu_messages.Interval()
    valid_interval.startTime = times.FormatDateTime(start_time)
    valid_interval.endTime = times.FormatDateTime(end_time)

    if request.queuedResource is None:
      request.queuedResource = tpu_messages.QueuedResource()
    # clear all other queueing policies
    request.queuedResource.queueingPolicy = tpu_messages.QueueingPolicy()
    request.queuedResource.queueingPolicy.validInterval = valid_interval
  return request


def CreateReservationName(ref, args, request):
  """Create the target reservation name from args."""
  del ref  # unused
  if (
      (args.reservation_host_project and args.reservation_host_folder)
      or (args.reservation_host_folder and args.reservation_host_organization)
      or (args.reservation_host_organization and args.reservation_host_project)
  ):
    raise exceptions.ConflictingArgumentsException(
        'Only one reservation host is permitted'
    )
  pattern = '{}/{}/locations/{}/reservations/-'
  reservation_name = None
  if args.reservation_host_project:
    reservation_name = pattern.format(
        'projects', args.reservation_host_project, args.zone
    )
  elif args.reservation_host_folder:
    reservation_name = pattern.format(
        'folders', args.reservation_host_folder, args.zone
    )
  elif args.reservation_host_organization:
    reservation_name = pattern.format(
        'organizations', args.reservation_host_organization, args.zone
    )

  if reservation_name:
    request.queuedResource.reservationName = reservation_name
  return request


def SetForce(ref, args, request):
  """Sets force arg to true if flag is set."""
  del ref  # unused
  if hasattr(args, 'force') and args.force:
    request.force = True

  return request
