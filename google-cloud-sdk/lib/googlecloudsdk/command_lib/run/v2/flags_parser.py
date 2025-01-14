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


def _GetLabelChanges(args):
  """Returns the label changes for the given args."""
  additions = (
      args.labels
      if flags.FlagIsExplicitlySet(args, 'labels')
      else args.update_labels
  )
  subtractions = (
      args.remove_labels
      if flags.FlagIsExplicitlySet(args, 'remove_labels')
      else []
  )
  return config_changes.LabelChange(
      additions,
      subtractions,
      clear_labels=args.clear_labels if 'clear_labels' in args else False,
  )


def _HasNetworkChanges(args):
  """Returns true iff any network changes are specified."""
  network_flags = [
      'vpc_egress',
      'network',
      'subnet',
      'network_tags',
      'clear_network',
      'clear_network_tags',
  ]
  return flags.HasChanges(args, network_flags)


def _GetNetworkChange(args):
  return config_changes.VpcAccessChanges(
      vpc_egress=args.vpc_egress,
      network=args.network,
      subnet=args.subnet,
      network_tags=args.network_tags
      if flags.FlagIsExplicitlySet(args, 'network_tags')
      else [],
      clear_network=args.clear_network if 'clear_network' in args else False,
      clear_network_tags=args.clear_network_tags
      if 'clear_network_tags' in args
      else False,
  )


def _HasCmekKeyChanges(args):
  """Returns true iff any CMEK key changes are specified."""
  cmek_key_flags = [
      'key',
      'post_key_revocation_action_type',
      'encryption_key_shutdown_hours',
      'clear_key',
      'clear_post_key_revocation_action_type',
      'clear_encryption_key_shutdown_hours',
  ]
  return flags.HasChanges(args, cmek_key_flags)


def _GetCmekKeyChange(args):
  return config_changes.CmekKeyChanges(
      key=args.key if flags.FlagIsExplicitlySet(args, 'key') else None,
      post_key_revocation_action_type=args.post_key_revocation_action_type
      if flags.FlagIsExplicitlySet(args, 'post_key_revocation_action_type')
      else None,
      encryption_key_shutdown_hours=int(args.encryption_key_shutdown_hours)
      if flags.FlagIsExplicitlySet(args, 'encryption_key_shutdown_hours')
      else None,
      clear_key=flags.FlagIsExplicitlySet(args, 'clear_key'),
      clear_post_key_revocation_action_type=flags.FlagIsExplicitlySet(
          args, 'clear_post_key_revocation_action_type'
      ),
      clear_encryption_key_shutdown_hours=flags.FlagIsExplicitlySet(
          args, 'clear_encryption_key_shutdown_hours'
      ),
  )


def _GetTemplateConfigurationChanges(args, non_ingress_type=False):
  """Returns a list of changes shared by multiple resources, based on the flags set."""
  changes = []
  # Revision name suffix
  if flags.FlagIsExplicitlySet(args, 'revision_suffix'):
    changes.append(config_changes.RevisionNameChange(args.revision_suffix))
  if flags.FlagIsExplicitlySet(args, 'mesh'):
    changes.append(config_changes.MeshChange(mesh=args.mesh))
  if _HasNetworkChanges(args):
    changes.append(_GetNetworkChange(args))
  if _HasCmekKeyChanges(args):
    changes.append(_GetCmekKeyChange(args))
  # Service account
  if 'service_account' in args and args.service_account:
    changes.append(
        config_changes.ServiceAccountChange(
            service_account=args.service_account
        )
    )
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
  if flags.HasEnvChanges(args):
    changes.append(_GetEnvChanges(args, non_ingress_type=non_ingress_type))
  # Add cpu, memory and gpu limits changes.
  changes.extend(
      _GetResourceLimitsChanges(args, non_ingress_type=non_ingress_type)
  )
  if 'gpu_type' in args and args.gpu_type:
    changes.append(config_changes.GpuTypeChange(gpu_type=args.gpu_type))
  return changes


def _GetEnvChanges(args, **kwargs):
  """Returns the env var literal changes for the given args."""
  return config_changes.EnvVarLiteralChanges(
      updates=flags.StripKeys(
          getattr(args, 'update_env_vars', None)
          or args.set_env_vars
          or args.env_vars_file
          or {}
      ),
      removes=flags.MapLStrip(
          getattr(args, 'remove_env_vars', None) or []
      ),
      clear_others=bool(
          args.set_env_vars or args.env_vars_file or args.clear_env_vars
      ),
      **kwargs,
  )


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
      scaling=args.scaling
      if 'scaling' in args and args.scaling is not None
      else None,
  )


def _HasBinaryAuthorizationChanges(args):
  """Returns true iff any binary authorization changes are specified."""
  bin_auth_flags = [
      'binary_authorization',
      'clear_binary_authorization',
      'breakglass',
  ]
  return flags.HasChanges(args, bin_auth_flags)


def _GetBinaryAuthorizationChanges(args):
  """Returns the binary authorization changes for the given args."""
  changes = []
  if flags.FlagIsExplicitlySet(args, 'binary_authorization'):
    changes.append(
        config_changes.BinaryAuthorizationChange(
            policy=args.binary_authorization
        )
    )
  if flags.FlagIsExplicitlySet(args, 'clear_binary_authorization'):
    changes.append(
        config_changes.BinaryAuthorizationChange(
            clear_binary_authorization=True
        )
    )
  if flags.FlagIsExplicitlySet(args, 'breakglass'):
    changes.append(
        config_changes.BinaryAuthorizationChange(
            breakglass_justification=args.breakglass
        )
    )
  return changes


def _GetInstanceSplitChanges(args):
  """Returns the instance split changes for the given args."""
  if args.to_latest:
    # Mutually exclusive flag with to-revisions
    return config_changes.InstanceSplitChange(to_latest=True)
  elif args.to_revisions:
    return config_changes.InstanceSplitChange(to_revisions=args.to_revisions)


def GetWorkerPoolConfigurationChanges(args):
  """Returns a list of changes to the worker pool config, based on the flags set."""
  changes = []
  # Description
  if flags.FlagIsExplicitlySet(args, 'description'):
    changes.append(config_changes.DescriptionChange(args.description))
  # Labels
  if flags.HasLabelChanges(args):
    changes.append(_GetLabelChanges(args))
  # Binary authorization
  if _HasBinaryAuthorizationChanges(args):
    changes.extend(_GetBinaryAuthorizationChanges(args))
  # Template changes
  changes.extend(_GetTemplateConfigurationChanges(args, non_ingress_type=True))
  # Worker pool scaling
  if _HasWorkerPoolScalingChanges(args):
    changes.append(_GetWorkerPoolScalingChange(args))
  if flags.HasInstanceSplitChanges(args):
    changes.append(_GetInstanceSplitChanges(args))
  _PrependClientNameAndVersionChange(args, changes)
  return changes
