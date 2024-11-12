# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Parsers given command arguments for the Cloud Run V2 command surface into configuration changes."""

from googlecloudsdk.command_lib.run import flags
from googlecloudsdk.command_lib.run.v2 import config_changes
from googlecloudsdk.core import config


def _PrependClientNameAndVersionChange(args, changes):
  """Set client name and version regardless of whether or not it was specified."""
  if 'client_name' in args:
    is_either_specified = args.IsSpecified('client_name') or args.IsSpecified(
        'client_version'
    )
    changes.insert(
        0,
        config_changes.SetClientNameAndVersionChange(
            client_name=args.client_name if is_either_specified else 'gcloud',
            client_version=args.client_version
            if is_either_specified
            else config.CLOUD_SDK_VERSION,
        ),
    )


def _GetResourceLimitsChanges(args, non_ingress_type=False):
  """Returns the resource limits changes for the given args."""
  changes = []
  if 'memory' in args and args.memory:
    changes.append(
        config_changes.ResourceLimitsChange(
            memory=args.memory, non_ingress_type=non_ingress_type
        )
    )
  if 'cpu' in args and args.cpu:
    changes.append(
        config_changes.ResourceLimitsChange(
            cpu=args.cpu, non_ingress_type=non_ingress_type
        )
    )
  if 'gpu' in args and args.gpu:
    changes.append(
        config_changes.ResourceLimitsChange(
            gpu=args.gpu, non_ingress_type=non_ingress_type
        )
    )
    if args.gpu == '0':
      changes.append(config_changes.GpuTypeChange(gpu_type=''))
  return changes


def _GetTemplateConfigurationChanges(args, non_ingress_type=False):
  """Returns a list of changes shared by multiple resources, based on the flags set."""
  changes = []

  # FlagIsExplicitlySet can't be used here because args.image is also set from
  # code in deploy.py once deploy from source is supported.
  if hasattr(args, 'image') and args.image is not None:
    changes.append(
        config_changes.ImageChange(
            args.image, non_ingress_type=non_ingress_type
        )
    )
  if 'command' in args and args.command is not None:
    changes.append(
        config_changes.ContainerCommandChange(
            args.command, non_ingress_type=non_ingress_type
        )
    )
  if 'args' in args and args.args is not None:
    changes.append(
        config_changes.ContainerArgsChange(
            args.args, non_ingress_type=non_ingress_type
        )
    )
  changes.extend(
      _GetResourceLimitsChanges(args, non_ingress_type=non_ingress_type)
  )
  if 'gpu_type' in args and args.gpu_type:
    changes.append(config_changes.GpuTypeChange(gpu_type=args.gpu_type))
  return changes


def _HasWorkerPoolScalingChanges(args):
  """Returns true iff any worker pool scaling changes are specified."""
  scaling_flags = [
      'min_instances',
      'max_instances',
      'max_surge',
      'scaling',
      'max_unavailable',
  ]
  return flags.HasChanges(args, scaling_flags)


# TODO(b/369135381): For now, this is as simple as setting the fields that's
# provided. Still need to decided on `default` or unsetting, etc.
def _GetWorkerPoolScalingChange(args):
  """Return the changes for engine-level scaling for Worker resources for the given args."""
  return config_changes.WorkerPoolScalingChange(
      min_instance_count=args.min_instances.instance_count
      if 'min_instances' in args and args.min_instances is not None
      else None,
      max_instance_count=args.max_instances.instance_count
      if 'max_instances' in args and args.max_instances is not None
      else None,
      max_surge=args.max_surge.surge_percent
      if 'max_surge' in args and args.max_surge is not None
      else None,
      max_unavailable=args.max_unavailable.unavailable_percent
      if 'max_unavailable' in args and args.max_unavailable is not None
      else None,
      scaling=args.scaling if 'scaling' in args and args.scaling is not None
      else None,
  )


def GetWorkerPoolConfigurationChanges(args):
  """Returns a list of changes to the worker pool config, based on the flags set."""
  changes = []
  changes.extend(_GetTemplateConfigurationChanges(args, non_ingress_type=True))
  if _HasWorkerPoolScalingChanges(args):
    changes.append(_GetWorkerPoolScalingChange(args))
  if 'service_account' in args and args.service_account:
    changes.append(
        config_changes.ServiceAccountChange(
            service_account=args.service_account
        )
    )
  _PrependClientNameAndVersionChange(args, changes)
  return changes
