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

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core.util import times


def GetMessagesModule(version='v2alpha1'):
  return apis.GetMessagesModule('tpu', version)


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
  node_spec.node.acceleratorType = args.accelerator_type
  node_spec.node.runtimeVersion = args.runtime_version

  node_spec.node.networkConfig = tpu_messages.NetworkConfig()
  node_spec.node.networkConfig.enableExternalIps = not args.internal_ips

  if args.node_id:
    node_spec.nodeId = args.node_id
  elif args.node_prefix and args.node_count:
    node_spec.multiNodeParams = tpu_messages.MultiNodeParams()
    node_spec.multiNodeParams.nodeIdPrefix = args.node_prefix
    node_spec.multiNodeParams.nodeCount = args.node_count
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
