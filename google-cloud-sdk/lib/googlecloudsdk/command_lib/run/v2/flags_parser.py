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

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.command_lib.run import flags
from googlecloudsdk.command_lib.run.config_changes import GenerateVolumeName
from googlecloudsdk.command_lib.run.v2 import config_changes
from googlecloudsdk.command_lib.util.args import repeated
from googlecloudsdk.core import config
from googlecloudsdk.core import properties


def SecretsFlags():
  """Creates flags for creating, updating, and deleting secrets."""
  return flags.MapFlagsNoFile(
      group_help=(
          'Specify secrets to provide as environment variables. '
          "For example: '--set-secrets=ENV=mysecret:latest,"
          "OTHER_ENV=othersecret:1' "
          'will create an environment variable named ENV whose value is the '
          "latest version of secret 'mysecret' and an environment variable "
          "OTHER_ENV whose value is version of 1 of secret 'othersecret'."
      ),
      flag_name='secrets',
  )


def AddSecretsFlags(parser):
  """Adds flags for creating, updating, and deleting secrets."""
  SecretsFlags().AddToParser(parser)


def AddCloudSQLFlags(parser):
  """Add flags for setting CloudSQL stuff."""
  repeated.AddPrimitiveArgs(
      parser,
      'WorkerPool',
      'cloudsql-instances',
      'Cloud SQL instances',
      auto_group_help=False,
      additional_help="""\
      These flags modify the Cloud SQL instances this WorkerPool connects to.
      You can specify a name of a Cloud SQL instance if it's in the same
      project and region as your Cloud Run worker pool; otherwise specify
      <project>:<region>:<instance> for the instance.""",
  )


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
  additions = {}
  if flags.FlagIsExplicitlySet(args, 'labels'):
    additions = args.labels
  elif flags.FlagIsExplicitlySet(args, 'update_labels'):
    additions = args.update_labels
  subtractions = (
      args.remove_labels
      if flags.FlagIsExplicitlySet(args, 'remove_labels')
      else []
  )
  return config_changes.LabelChange(
      additions=additions,
      subtractions=subtractions,
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


def _GetSecretsChanges(args, non_ingress_type=False, container_name=None):
  """Returns the secrets changes for the given args."""
  changes = []
  updates = flags.StripKeys(
      getattr(args, 'update_secrets', None) or args.set_secrets or {}
  )
  for key in updates:
    # Secrets volume mount is not supported for Worker Pools yet.
    if key.startswith('/'):
      raise exceptions.ConfigurationError(
          'Secrets volume mount is not supported for Worker Pools yet.'
      )
  removes = flags.MapLStrip(getattr(args, 'remove_secrets', None) or [])
  for key in removes:
    # Secrets volume mount is not supported for Worker Pools yet.
    if key.startswith('/'):
      raise exceptions.ConfigurationError(
          'Secrets volume mount is not supported for Worker Pools yet.'
      )
  clear_others = bool(args.set_secrets or args.clear_secrets)
  if updates or removes or clear_others:
    changes.append(
        config_changes.SecretsEnvVarChanges(
            updates=updates,
            removes=removes,
            clear_others=clear_others,
            container_name=container_name,
            non_ingress_type=non_ingress_type,
        )
    )
  return changes


def _GetCloudSQLChanges(args):
  """Returns the Cloud SQL changes for the given args."""
  region = flags.GetRegion(args)
  project = getattr(
      args, 'project', None
  ) or properties.VALUES.core.project.Get(required=True)
  if flags.EnabledCloudSqlApiRequired(args):
    flags.CheckCloudSQLApiEnablement()
  # At most one of the cloud sql flags can be set.
  change = []
  if (
      flags.FlagIsExplicitlySet(args, 'add_cloudsql_instances')
      and args.add_cloudsql_instances
  ):
    change.append(
        config_changes.AddCloudSQLChanges(
            project=project,
            region=region,
            add_cloudsql_instances=args.add_cloudsql_instances,
        )
    )
  elif (
      flags.FlagIsExplicitlySet(args, 'remove_cloudsql_instances')
      and args.remove_cloudsql_instances
  ):
    change.append(
        config_changes.RemoveCloudSQLChanges(
            project=project,
            region=region,
            remove_cloudsql_instances=args.remove_cloudsql_instances,
        )
    )
  elif (
      flags.FlagIsExplicitlySet(args, 'clear_cloudsql_instances')
      and args.clear_cloudsql_instances
  ):
    change.append(config_changes.ClearCloudSQLChanges())
  elif (
      flags.FlagIsExplicitlySet(args, 'set_cloudsql_instances')
      and args.set_cloudsql_instances
  ):
    change.append(
        config_changes.SetCloudSQLChanges(
            project=project,
            region=region,
            set_cloudsql_instances=args.set_cloudsql_instances,
        )
    )
  return change


def _GetContainerConfigurationChanges(
    container_args, container_name=None, non_ingress_type=True
):
  """Returns per-container configuration changes."""
  changes = []
  # FlagIsExplicitlySet can't be used here because args.image is also set from
  # code in deploy.py.
  if hasattr(container_args, 'image') and container_args.image is not None:
    changes.append(
        config_changes.ImageChange(
            container_args.image,
            container_name=container_name,
            non_ingress_type=non_ingress_type,
        )
    )
  if flags.HasEnvChanges(container_args):
    changes.append(
        _GetEnvChanges(
            container_args,
            container_name=container_name,
            non_ingress_type=non_ingress_type,
        )
    )
  if container_args.IsSpecified('cpu'):
    changes.append(
        config_changes.ResourceLimitsChange(
            cpu=container_args.cpu,
            container_name=container_name,
            non_ingress_type=non_ingress_type,
        )
    )
  if container_args.IsSpecified('memory'):
    changes.append(
        config_changes.ResourceLimitsChange(
            memory=container_args.memory,
            container_name=container_name,
            non_ingress_type=non_ingress_type,
        )
    )
  if container_args.IsSpecified('command'):
    # Allow passing an empty string here to reset the field
    changes.append(
        config_changes.ContainerCommandChange(
            container_args.command,
            container_name=container_name,
            non_ingress_type=non_ingress_type,
        )
    )
  if container_args.IsSpecified('args'):
    # Allow passing an empty string here to reset the field
    changes.append(
        config_changes.ContainerArgsChange(
            container_args.args,
            container_name=container_name,
            non_ingress_type=non_ingress_type,
        )
    )
  if flags.FlagIsExplicitlySet(
      container_args, 'remove_volume_mount'
  ) or flags.FlagIsExplicitlySet(container_args, 'clear_volume_mounts'):
    changes.append(
        config_changes.RemoveVolumeMountChange(
            removed_mounts=container_args.remove_volume_mount,
            clear_mounts=container_args.clear_volume_mounts,
            container_name=container_name,
            non_ingress_type=non_ingress_type,
        )
    )
  if flags.HasSecretsChanges(container_args):
    changes.extend(
        _GetSecretsChanges(
            container_args,
            container_name=container_name,
            non_ingress_type=non_ingress_type,
        )
    )
  if flags.FlagIsExplicitlySet(container_args, 'add_volume_mount'):
    changes.append(
        config_changes.AddVolumeMountChange(
            new_mounts=container_args.add_volume_mount,
            container_name=container_name,
            non_ingress_type=non_ingress_type,
        )
    )
  return changes


def _GetTemplateConfigurationChanges(
    args, release_track, non_ingress_type=False
):
  """Returns a list of changes shared by multiple resources, based on the flags set."""
  changes = []
  # Revision name suffix
  if flags.FlagIsExplicitlySet(args, 'revision_suffix'):
    changes.append(config_changes.RevisionNameChange(args.revision_suffix))
  if flags.FlagIsExplicitlySet(args, 'mesh'):
    changes.append(
        config_changes.MeshChange(
            project=properties.VALUES.core.project.Get(required=True),
            mesh_name=args.mesh,
        )
    )
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
  if flags.FlagIsExplicitlySet(args, 'gpu_zonal_redundancy'):
    changes.append(
        config_changes.GpuZonalRedundancyChange(
            gpu_zonal_redundancy=args.gpu_zonal_redundancy
        )
    )
  # Cloud SQL changes
  if flags.HasCloudSQLChanges(args):
    changes.extend(_GetCloudSQLChanges(args))
  # Volumes / Volume Mounts / Secrets changes
  if flags.FlagIsExplicitlySet(
      args, 'remove_volume_mount'
  ) or flags.FlagIsExplicitlySet(args, 'clear_volume_mounts'):
    changes.append(
        config_changes.RemoveVolumeMountChange(
            removed_mounts=args.remove_volume_mount,
            clear_mounts=args.clear_volume_mounts,
            non_ingress_type=non_ingress_type,
        )
    )
  if (
      flags.FlagIsExplicitlySet(args, 'remove_volume') and args.remove_volume
  ) or (
      flags.FlagIsExplicitlySet(args, 'clear_volumes') and args.clear_volumes
  ):
    changes.append(
        config_changes.RemoveVolumeChange(
            args.remove_volume, args.clear_volumes
        )
    )
  if flags.HasSecretsChanges(args):
    changes.extend(_GetSecretsChanges(args, non_ingress_type=non_ingress_type))
  if flags.FlagIsExplicitlySet(args, 'add_volume') and args.add_volume:
    # Volume names must be generated before calling AddVolumeChange
    _ValidateAndMaybeGenerateVolumeNames(args, release_track)
    changes.append(
        config_changes.AddVolumeChange(args.add_volume, release_track)
    )
    _MaybeAddVolumeMountChange(args, changes, release_track)
  if (
      flags.FlagIsExplicitlySet(args, 'add_volume_mount')
      and args.add_volume_mount
  ):
    changes.append(
        config_changes.AddVolumeMountChange(
            new_mounts=args.add_volume_mount,
            non_ingress_type=non_ingress_type,
        )
    )
  if flags.FlagIsExplicitlySet(args, 'remove_containers'):
    changes.append(
        config_changes.RemoveContainersChange(args.remove_containers)
    )
    # Add an empty ContainerDependenciesChange to update dependencies.
    changes.append(config_changes.ContainerDependenciesChange())

  # Per container changes
  if flags.FlagIsExplicitlySet(args, 'containers'):
    for container_name, container_args in args.containers.items():
      changes.extend(
          _GetContainerConfigurationChanges(
              container_args, container_name=container_name
          )
      )

  # Dependencies
  if flags.FlagIsExplicitlySet(args, 'containers'):
    # TODO: b/393482156 - Add support for per container config changes.
    dependency_changes = {
        container_name: container_args.depends_on
        for container_name, container_args in args.containers.items()
        if container_args.IsSpecified('depends_on')
    }
    if dependency_changes:
      changes.append(
          config_changes.ContainerDependenciesChange(dependency_changes)
      )
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
      removes=flags.MapLStrip(getattr(args, 'remove_env_vars', None) or []),
      clear_others=bool(
          args.set_env_vars or args.env_vars_file or args.clear_env_vars
      ),
      **kwargs,
  )


def _HasWorkerPoolScalingChanges(args):
  """Returns true iff any worker pool scaling changes are specified."""
  scaling_flags = [
      'min',
      'max',
      'scaling',
  ]
  return flags.HasChanges(args, scaling_flags)


def _GetWorkerPoolScalingChange(args, release_track):
  """Return the changes for engine-level scaling for Worker Pools for the given args."""
  # Catch the case where user sets scaling mode to auto for BETA.
  if release_track == base.ReleaseTrack.BETA:
    if args.scaling and args.scaling.auto_scaling:
      raise exceptions.ConfigurationError(
          'Automatic scaling is not supported in BETA.'
      )
  return config_changes.WorkerPoolScalingChange(
      min_instance_count=args.min
      if 'min' in args and args.min is not None
      else None,
      max_instance_count=args.max
      if 'max' in args and args.max is not None
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


def _ValidateAndMaybeGenerateVolumeNames(args, release_track):
  """Validates used of the volumes shortcut and generates volume names when needed.

  Specifically, it checks that the 'mount-path' parameter is not being used
  with the --containers flag and that the volume type is an allowed type. If
  validation succeeds and the volume also needs a name, one is generated.

  Args:
    args: The argparse namespace containing the parsed command line arguments.
    release_track: The current release track (e.g., base.ReleaseTrack.ALPHA).
  """
  uses_containers_flag = flags.FlagIsExplicitlySet(args, 'containers')
  if release_track == base.ReleaseTrack.ALPHA:
    for volume in args.add_volume:
      # If mount-path is specified, the user is attempting to use the volumes
      # shortcut.
      if 'mount-path' in volume:
        # The volumes shortcut is not compatible with the --containers flag.
        if uses_containers_flag:
          raise exceptions.ConfigurationError(
              'When using the --containers flag, "mount-path" cannot be'
              ' specified under the --add-volume flag. Instead, specify'
              ' "mount-path" using the --add-volume-mount flag after the'
              ' --container flag of the container the volume should be'
              ' mounted to.'
          )
        # Generate a name if the user has not specified one.
        if 'name' not in volume:
          volume['name'] = GenerateVolumeName(volume['type'])


def _MaybeAddVolumeMountChange(args, changes, release_track):
  """Adds a VolumeMountChange to the list of changes if applicable.

  This function checks if new volume mounts should be added based on the
  `--add-volume` flag in ALPHA release track. If a volume in `args.add_volume`
  has a 'mount-path', a corresponding AddVolumeMountChange
  is appended to the `changes` list.

  Args:
    args: The argparse namespace containing the parsed command line arguments.
    changes: A list of configuration changes to append to.
    release_track: The current release track (e.g., base.ReleaseTrack.ALPHA).
  """
  if release_track == base.ReleaseTrack.ALPHA:
    new_volume_mounts = []
    for volume in args.add_volume:
      if 'mount-path' in volume and 'name' in volume:
        volume_mount_args = {
            'volume': volume['name'],
            'mount-path': volume['mount-path'],
        }
        new_volume_mounts.append(volume_mount_args)
    if new_volume_mounts:
      changes.append(
          config_changes.AddVolumeMountChange(
              new_mounts=new_volume_mounts,
          )
      )


def GetWorkerPoolConfigurationChanges(args, release_track):
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
  changes.extend(
      _GetTemplateConfigurationChanges(
          args, release_track, non_ingress_type=True
      )
  )
  # Worker pool scaling
  if _HasWorkerPoolScalingChanges(args):
    changes.append(_GetWorkerPoolScalingChange(args, release_track))
  if flags.HasInstanceSplitChanges(args):
    changes.append(_GetInstanceSplitChanges(args))
  if 'no_promote' in args and args.no_promote:
    changes.append(config_changes.NoPromoteChange())
  _PrependClientNameAndVersionChange(args, changes)
  return changes
