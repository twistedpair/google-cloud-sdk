# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Utilities for validating parameters."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.ai import constants


def ValidateWorkerPoolSpec(worker_pool_spec):
  """Validates the input worker-pool-specs."""
  for spec in worker_pool_spec:
    is_spec_initialized = (
        spec.machineSpec or spec.replicaCount or spec.pythonPackageSpec or
        spec.containerSpec)
    if is_spec_initialized:
      use_python_package = spec.pythonPackageSpec and (
          spec.pythonPackageSpec.executorImageUri or
          spec.pythonPackageSpec.pythonModule)
      use_container = spec.containerSpec and spec.containerSpec.imageUri

      if (use_container and use_python_package) or (not use_container and
                                                    not use_python_package):
        raise exceptions.InvalidArgumentException(
            '--worker-pool-spec',
            'Either container or python package must be set.')


def ValidateDisplayName(display_name):
  """Validates the display name."""
  if display_name is not None and not display_name:
    raise exceptions.InvalidArgumentException(
        '--display-name',
        'Display name can not be empty.')


def GetAndValidateKmsKey(args):
  """Parse CMEK resource arg, and check if the arg was partially specified."""
  if hasattr(args.CONCEPTS, 'kms_key'):
    kms_ref = args.CONCEPTS.kms_key.Parse()
    if kms_ref:
      return kms_ref.RelativeName()
    else:
      for keyword in ['kms_key', 'kms_keyring', 'kms_location', 'kms_project']:
        if getattr(args, keyword, None):
          raise exceptions.InvalidArgumentException(
              '--kms-key', 'Encryption key not fully specified.')


def ValidateAutoscalingMetricSpecs(specs):
  """Value validation for autoscaling metric specs target name and value."""
  if specs is None:
    return

  for key, value in specs.items():
    if key not in constants.OP_AUTOSCALING_METRIC_NAME_MAPPER:
      raise exceptions.InvalidArgumentException(
          '--autoscaling-metric-specs',
          """Autoscaling metric name can only be one of the following: {}."""
          .format(', '.join([
              "'{}'".format(c) for c in sorted(
                  constants.OP_AUTOSCALING_METRIC_NAME_MAPPER.keys())
          ])))

    if value <= 0 or value > 100:
      raise exceptions.InvalidArgumentException(
          '--autoscaling-metric-specs',
          'Metric target value %s is not between 0 and 100.' % value)
