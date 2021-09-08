# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Reducer functions to generate instance props from prior state and flags."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from googlecloudsdk.calliope import exceptions


_MINIMUM_CPU_COUNT = 2
_MAXIMUM_CPU_COUNT = 96
_MINIMUM_MEMORY = 3840
_MINIMUM_MEMORY_CPU_RATIO = 900
_MAXIMUM_MEMORY_CPU_RATIO = 6500
_MEMORY_MULTIPLE = 256


def _CustomMachineTypeString(cpu, memory_mib):
  """Creates a custom machine type from the CPU and memory specs.

  Args:
    cpu: the number of cpu desired for the custom machine type
    memory_mib: the amount of ram desired in MiB for the custom machine type
      instance

  Returns:
    The custom machine type name for the 'instance create' call

  Raises:
    exceptions.InvalidArgumentException when both the tier and
        custom machine type flags are used to generate a new instance.
  """
  return 'db-custom-{0}-{1}'.format(cpu, memory_mib)


def MachineType(tier=None, memory=None, cpu=None):
  """Generates the machine type for the instance.

  Adapted from compute.

  Args:
    tier: string, the v1 or v2 tier.
    memory: string, the amount of memory.
    cpu: int, the number of CPUs.

  Returns:
    A string representing the URL naming a machine-type.

  Raises:
    exceptions.RequiredArgumentException when only one of the two custom
        machine type flags are used, or when none of the flags are used.
    exceptions.InvalidArgumentException when both the tier and
        custom machine type flags are used to generate a new instance or
        memory and cpu values don't meet the following criteria:
        1) CPU must be between 2 and 96 CPU.
        2) Memory must be at least 3.75GB (3840 MB).
        3) There must be between 0.6 and 6.5GB of memory per vCPU.
        4) Memory must be a multiple of 256MB.
  """

  # Setting the machine type.
  machine_type = None
  if tier:
    machine_type = tier

  # Setting the specs for the custom machine.
  if cpu or memory:
    if not cpu:
      raise exceptions.RequiredArgumentException(
          '--cpu', 'Both [--cpu] and [--memory] must be '
          'set to create a custom machine type instance.')
    if not memory:
      raise exceptions.RequiredArgumentException(
          '--memory', 'Both [--cpu] and [--memory] must '
          'be set to create a custom machine type instance.')
    if tier:
      raise exceptions.InvalidArgumentException(
          '--tier', 'Cannot set both [--tier] and '
          '[--cpu]/[--memory] for the same instance.')

    # Converting from B to MiB.
    memory //= (2**20)
    if cpu < _MINIMUM_CPU_COUNT or cpu > _MAXIMUM_CPU_COUNT:
      raise exceptions.InvalidArgumentException(
          '--cpu', '[--cpu] must be between 2 and 96.')
    if memory < _MINIMUM_MEMORY:
      raise exceptions.InvalidArgumentException(
          '--memory', '[--memory] must be at least 3.75GB (3840 MB)')
    if memory / cpu < _MINIMUM_MEMORY_CPU_RATIO or memory / cpu > _MAXIMUM_MEMORY_CPU_RATIO:
      raise exceptions.InvalidArgumentException(
          '--memory', 'There must be between 0.9 - 6.50GB of memory per vCPU.')
    if memory % _MEMORY_MULTIPLE != 0:
      raise exceptions.InvalidArgumentException(
          '--memory', '[--memory] must be a multiple of 256MB.')

    custom_type_string = _CustomMachineTypeString(
        cpu,
        memory)

    # Updating the machine type that is set for the URIs.
    machine_type = custom_type_string

  # Reverting to default if creating instance and no flags are set.
  if not machine_type:
    raise exceptions.InvalidArgumentException(
        '--tier, --cpu/--memory'
        'Please specify [--tier] or [--cpu]/[--memory]')

  return machine_type
