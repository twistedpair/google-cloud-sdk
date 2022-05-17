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
  for node_id in args.node_id:
    node_spec = tpu_messages.NodeSpec()
    node_spec.nodeId = node_id
    node_spec.parent = ref.Parent().RelativeName()

    node_spec.node = tpu_messages.Node()
    node_spec.node.acceleratorType = args.accelerator_type
    node_spec.node.runtimeVersion = args.runtime_version

    request.queuedResource.tpu.nodeSpec.append(node_spec)

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
