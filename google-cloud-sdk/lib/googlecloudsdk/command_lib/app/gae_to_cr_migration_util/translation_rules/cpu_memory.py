# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""Translation rule for app resources (instance_class, cpu, memory)."""

import logging
from typing import Mapping, Sequence
import frozendict

from googlecloudsdk.command_lib.app.gae_to_cr_migration_util.common import util
from googlecloudsdk.command_lib.app.gae_to_cr_migration_util.translation_rules import scaling


_ALLOWED_RESOURCE_KEY = tuple(['resources.cpu', 'resources.memory_gb'])
_ALLOW_INSTANCE_CLASS_KEY = 'instance_class'
_DEFAULT_CPU_MEM_CONFIG = frozendict.frozendict({
    scaling.ScalingTypeAppYaml.AUTOMATIC_SCALING: 'F1',
    scaling.ScalingTypeAppYaml.MANUAL_SCALING: 'B2',
    scaling.ScalingTypeAppYaml.BASIC_SCALING: 'B2',
})
# See https://cloud.google.com/run/docs/configuring/cpu
# See https://cloud.google.com/run/docs/configuring/memory-limits
_INSTANCE_CLASS_MAP = frozendict.frozendict({
    'F1': {'cpu': 1, 'memory': 0.25},
    'F2': {'cpu': 1, 'memory': 0.5},
    'F4': {'cpu': 1, 'memory': 1},
    'F4_1G': {'cpu': 1, 'memory': 2},
    'B1': {'cpu': 1, 'memory': 0.25},
    'B2': {'cpu': 1, 'memory': 0.5},
    'B4': {'cpu': 1, 'memory': 1},
    'B4_1G': {'cpu': 1, 'memory': 2},
    'B8': {'cpu': 2, 'memory': 2},
})


def translate_app_resources(
    input_data: Mapping[str, any]
) -> Sequence[str]:
  """Translate instance_class(standard) to equivalent/compatible.

  Cloud Run --cpu and --memory flags.

  Args:
    input_data: Dictionary of the input data from app.yaml.

  Returns:
    List of output flags.
  """
  return _translate_standard_instance_class(input_data)


def _translate_standard_instance_class(
    input_data: Mapping[str, any]
) -> Sequence[str]:
  """Translate standard instance_class to equivalent/compatible Cloud Run flags.

  Args:
    input_data: Dictionary of the input data from app.yaml.

  Returns:
    List of output flags.
  """
  instance_class_key_from_input = util.get_feature_key_from_input(
      input_data, [_ALLOW_INSTANCE_CLASS_KEY]
  )
  if instance_class_key_from_input:
    instance_class = input_data[instance_class_key_from_input]
    return _generate_cpu_memory_flags_by_instance_class(instance_class)
  return _get_cpu_memory_default_based_on_scaling_method(input_data)


def _get_cpu_memory_default_based_on_scaling_method(
    input_data: Mapping[str, any]
) -> Sequence[str]:
  """Get default cpu/memory based on scaling method.

  Args:
    input_data: Dictionary of the input data from app.yaml.

  Returns:
    List of output flags.
  """
  scaling_features_used = scaling.get_scaling_features_used(input_data)
  if not scaling_features_used:
    return []
  if len(scaling_features_used) > 1:
    logging.warning(
        'Warning: More than one scaling option is defined,             only one'
        ' scaling option should be used.'
    )
    return []
  scaling_method = scaling_features_used[0]
  default_instance_class = _DEFAULT_CPU_MEM_CONFIG[scaling_method]
  return _generate_cpu_memory_flags_by_instance_class(default_instance_class)


def _generate_cpu_memory_flags_by_instance_class(
    instance_class: str
) -> Sequence[str]:
  """Generate cpu/memory flags based on instance class.

  Args:
    instance_class: Instance class string.

  Returns:
    List of output flags.
  """
  cpu_memory_config = _INSTANCE_CLASS_MAP[instance_class]
  cpu_value = cpu_memory_config['cpu']
  memory_value = cpu_memory_config['memory']
  if memory_value < 0.5:
    memory_value = 0.5
  if memory_value > 32:
    memory_value = 32
    cpu_value = 8
  if memory_value > 24:
    cpu_value = 8
  if memory_value > 16:
    cpu_value = 6
  if memory_value > 8:
    cpu_value = 4
  if memory_value > 4:
    cpu_value = 2
  # Cloud Run --memory requires a unit suffix
  # https://cloud.google.com/run/docs/configuring/memory-limits#setting-services
  return [
      f'--cpu={cpu_value}',
      f'--memory={_format_cloud_run_memory_unit(memory_value)}',
  ]


def _format_cloud_run_memory_unit(value: float) -> str:
  """Format memory value with Cloud Run unit.

  Args:
    value: Memory value in float.

  Returns:
    Memory value with Cloud Run unit.
  """
  # 1GB = 953Mi, 1Gi = 1024Mi memory, in Cloud Run, a minimum of 512MiB memory
  # is required for 1 CPU. Therefore, using Gi works for the lower bound of
  # memory requirement.
  # Allowed values are [m, k, M, G, T, Ki, Mi, Gi, Ti, Pi, Ei]
  return f'{value}Gi'
