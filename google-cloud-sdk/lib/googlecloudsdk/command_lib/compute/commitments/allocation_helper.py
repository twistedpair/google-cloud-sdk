# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Helpers for creating zonal allocations within commitment creation."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute.allocations import resource_args
from googlecloudsdk.command_lib.compute.allocations import util
from googlecloudsdk.core import yaml


def MakeAllocations(args, messages, holder):
  if args.IsSpecified('allocations_from_file'):
    return _MakeAllocationsFromFile(messages, args)
  elif args.IsSpecified('allocation'):
    return [_MakeSingleAllocation(args, messages, holder)]
  else:
    return []


def _MakeAllocationsFromFile(messages, args):
  allocations_yaml = yaml.load(args.allocations_from_file)
  return _ConvertYAMLToMessage(messages, allocations_yaml)


def _ConvertYAMLToMessage(messages, allocations_yaml):
  """Converts the fields in yaml to allocation message object."""
  if not allocations_yaml:
    return []
  allocations_msg = []
  for a in allocations_yaml:
    accelerators = util.MakeGuestAccelerators(
        messages, a.get('accelerator', None))
    local_ssds = util.MakeLocalSsds(
        messages, a.get('local_ssd', None))
    specific_allocation = util.MakeSpecificSKUAllocationMessage(
        messages, a.get('vm_count', None), accelerators, local_ssds,
        a.get('machine_type', None), a.get('min_cpu_platform', None))
    a_msg = util.MakeAllocationMessage(
        messages, a.get('allocation', None), specific_allocation,
        a.get('require_specific_allocation', None),
        a.get('allocation_zone', None))
    allocations_msg.append(a_msg)
  return allocations_msg


def _MakeSingleAllocation(args, messages, holder):
  """Makes one Allocation message object."""
  allocation_ref = resource_args.GetAllocationResourceArg(
      positional=False).ResolveAsResource(
          args,
          holder.resources,
          scope_lister=compute_flags.GetDefaultScopeLister(holder.client))
  return util.MakeAllocationMessageFromArgs(messages, args, allocation_ref)
