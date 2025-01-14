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
"""Class for representing various changes to a Cloud Run V2 resource."""

from __future__ import absolute_import
from __future__ import annotations
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import abc
import dataclasses

from cloudsdk.google.protobuf import duration_pb2  # pytype: disable=import-error
from google.api import launch_stage_pb2  # pytype: disable=import-error
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.run import config_changes
from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.command_lib.run import flags
from googlecloudsdk.command_lib.run.v2 import instance_split as instance_split_lib
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import instance_split
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import k8s_min
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import vendor_settings
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import worker_pool


def WithChanges(resource, changes):
  """Apply ConfigChangers to resource.

  It's undefined whether the input resource is modified.

  Args:
    resource: The Cloud Run V2 resource to modify.
    changes: List of ConfigChangers.

  Returns:
    Changed resource.
  """
  for config_change in changes:
    resource = config_change.Adjust(resource)
  return resource


@dataclasses.dataclass(frozen=True)
class ContainerConfigChanger(config_changes.TemplateConfigChanger):
  """An abstract class representing worker pool container configuration changes.

  Attributes:
    container_name: Name of the container to modify. If None the first container
      is modified.
  """

  container_name: str | None = None
  non_ingress_type: bool = False

  @abc.abstractmethod
  def AdjustContainer(
      self,
      container: k8s_min.Container,
  ):
    """Mutate the given container.

    This method is called by this class's Adjust method and should apply the
    desired changes directly to container.

    Args:
      container: the container to adjust.
    """

  def Adjust(self, resource):
    """Returns a modified Cloud Run V2 resource.

    Adjusts Cloud Run V2 resource by applying changes to the container specified
    by self.container_name if present or the first container otherwise. Calls
    AdjustContainer to apply changes to the selected container.

    Args:
      resource: The Cloud RUn V2 resource to modify.
    """
    container = self._FindContainer(resource)
    self.AdjustContainer(container)
    return resource

  def _FindContainer(self, resource):
    """Find the container to adjust.

    1. Make ''(empty string) name referenceable.
    2. If name is specified, but not found, create one with the name.
    3. No name specified, no containers, add one with name ''.
    4. No name specified, we have containers, return the first one for
    non-ingress types.
    5. For ingress types, return the ingress container. If not found, fall-back
    to the first one.

    Args:
      resource: The Cloud Run V2 resource to modify.

    Returns:
      The container to adjust.
    """
    containers = resource.template.containers
    # Container name is specified including empty string. Find the container
    # with the name or if not found, add a new one with the name.
    if self.container_name is not None:
      for c in containers:
        if c.name == self.container_name:
          return c
      # Container not found with the given name. Add a new one with the name.
      containers.append(k8s_min.Container(name=self.container_name))
      return containers[-1]
    else:
      if not containers:
        container = k8s_min.Container(name='')
        containers.append(container)
      # For non-ingress types (e.g. worker pools, jobs), default to the first
      # container. For ingress types (e.g. services), default to the primary
      # container by checking ports, then fall-back to the first container.
      if self.non_ingress_type:
        return containers[0]
      else:
        for c in containers:
          if c.ports:
            return c
        # Ingress container not found. Fall-back to the first one.
        return containers[0]


# Common config changes to all resource types starts.
@dataclasses.dataclass(frozen=True)
class SetAnnotationChange(config_changes.NonTemplateConfigChanger):
  """Represents the user intent to set an annotation.

  Attributes:
    key: Annotation to set.
    value: Annotation value to set.
  """

  key: str
  value: str

  def Adjust(self, resource):
    resource.annotations[self.key] = self.value
    return resource


@dataclasses.dataclass(frozen=True)
class DeleteAnnotationChange(config_changes.NonTemplateConfigChanger):
  """Represents the user intent to delete an annotation.

  Attributes:
    key: Annotation to delete.
  """

  key: str

  def Adjust(self, resource):
    annotations = resource.annotations
    if self.key in annotations:
      del annotations[self.key]
    return resource


@dataclasses.dataclass(frozen=True)
class SetTemplateAnnotationChange(config_changes.TemplateConfigChanger):
  """Represents the user intent to set a template annotation.

  Attributes:
    key: Template annotation to set.
    value: Annotation value to set.
  """

  key: str
  value: str

  def Adjust(self, resource):
    resource.template.annotations[self.key] = self.value
    return resource


@dataclasses.dataclass(frozen=True)
class DeleteTemplateAnnotationChange(config_changes.TemplateConfigChanger):
  """Represents the user intent to delete a template annotation.

  Attributes:
    key: Template annotation to delete.
  """

  key: str

  def Adjust(self, resource):
    annotations = resource.template.annotations
    if self.key in annotations:
      del annotations[self.key]
    return resource


@dataclasses.dataclass(frozen=True)
class SetLaunchStageChange(config_changes.NonTemplateConfigChanger):
  """Sets launch stage on a resource.

  Attributes:
    launch_stage: The launch stage to set.
  """

  launch_stage: base.ReleaseTrack

  def Adjust(self, resource):
    if self.launch_stage != base.ReleaseTrack.GA:
      resource.launch_stage = launch_stage_pb2.LaunchStage.Value(
          self.launch_stage.id
      )
    return resource


@dataclasses.dataclass(frozen=True)
class SetClientNameAndVersionChange(config_changes.NonTemplateConfigChanger):
  """Sets the client name and version.

  Attributes:
    client_name: Client name to set.
    client_version: Client version to set.
  """

  client_name: str
  client_version: str

  def Adjust(self, resource):
    if self.client_name is not None:
      resource.client = self.client_name
    if self.client_version is not None:
      resource.client_version = self.client_version
    return resource


@dataclasses.dataclass(frozen=True)
class ServiceAccountChange(config_changes.TemplateConfigChanger):
  """Represents the user intent to change service account for the revision.

  Attributes:
    service_account: The service account to set.
  """

  service_account: str

  def Adjust(self, resource):
    """Mutates the given config's service account to match what's desired."""
    resource.template.service_account = self.service_account
    return resource


@dataclasses.dataclass(init=False, frozen=True)
class ImageChange(ContainerConfigChanger):
  """A Cloud Run container deployment.

  Attributes:
    image: The image to set in the adjusted container.
  """

  image: str

  def __init__(self, image, **kwargs):
    super().__init__(**kwargs)
    object.__setattr__(self, 'image', image)

  def AdjustContainer(self, container):
    container.image = self.image


@dataclasses.dataclass(frozen=True)
class ResourceLimitsChange(ContainerConfigChanger):
  """Represents the user intent to update resource limits.

  Attributes:
    memory: Updated memory limit to set in the container. Specified as string
      ending in 'Mi' or 'Gi'. If None the memory limit is not changed.
    cpu: Updated cpu limit to set in the container if not None.
    gpu: Updated gpu limit to set in the container if not None.
  """

  memory: str | None = None
  cpu: str | None = None
  gpu: str | None = None

  def __init__(self, memory=None, cpu=None, gpu=None, **kwargs):
    super().__init__(**kwargs)
    object.__setattr__(self, 'memory', memory)
    object.__setattr__(self, 'cpu', cpu)
    object.__setattr__(self, 'gpu', gpu)

  def AdjustContainer(self, container):
    """Mutates the given config's resource limits to match what's desired."""
    if self.memory is not None:
      container.resources.limits['memory'] = self.memory
    if self.cpu is not None:
      container.resources.limits['cpu'] = self.cpu
    if self.gpu is not None:
      if self.gpu == '0':
        container.resources.limits.pop('nvidia.com/gpu', None)
      else:
        container.resources.limits['nvidia.com/gpu'] = self.gpu


_MAX_RESOURCE_NAME_LENGTH = 63


@dataclasses.dataclass(frozen=True)
class RevisionNameChange(config_changes.TemplateConfigChanger):
  """Represents the user intent to change revision name.

  Attributes:
    revision_suffix: Suffix to append to the revision name.
  """

  revision_suffix: str

  def Adjust(self, resource):
    """Mutates the given config's revision name to match what's desired."""
    if not self.revision_suffix:
      resource.template.revision = ''
      return resource

    max_prefix_length = (
        _MAX_RESOURCE_NAME_LENGTH - len(self.revision_suffix) - 1
    )
    resource.template.revision = '{}-{}'.format(
        resource.name[:max_prefix_length], self.revision_suffix
    )
    return resource


@dataclasses.dataclass(frozen=True)
class MeshChange(config_changes.TemplateConfigChanger):
  """Represents the user intent to enable/disable Cloud Service Mesh.

  Attributes:
    mesh: Mesh resource name in the format of
      projects/PROJECT/locations/global/meshes/MESH_NAME.
  """

  mesh: str

  def Adjust(self, resource):
    resource.template.service_mesh.mesh = self.mesh
    return resource


@dataclasses.dataclass(frozen=True)
class GpuTypeChange(config_changes.TemplateConfigChanger):
  """Sets the gpu-type on the resource template.

  Attributes:
    gpu_type: The gpu_type value to set.
  """

  gpu_type: str

  def Adjust(self, resource):
    if self.gpu_type:
      resource.template.node_selector.accelerator = self.gpu_type
    else:
      resource.template.node_selector.accelerator = None
    return resource


@dataclasses.dataclass(init=False, frozen=True)
class ContainerCommandChange(ContainerConfigChanger):
  """Represents the user intent to change the 'command' for the container.

  Attributes:
    command: The command to set in the adjusted container.
  """

  command: str

  def __init__(self, command, **kwargs):
    super().__init__(**kwargs)
    object.__setattr__(self, 'command', command)

  def AdjustContainer(self, container):
    container.command = self.command


@dataclasses.dataclass(init=False, frozen=True)
class ContainerArgsChange(ContainerConfigChanger):
  """Represents the user intent to change the 'args' for the container.

  Attributes:
    args: The args to set in the adjusted container.
  """

  args: list[str]

  def __init__(self, args, **kwargs):
    super().__init__(**kwargs)
    object.__setattr__(self, 'args', args)

  def AdjustContainer(self, container):
    container.args = self.args


@dataclasses.dataclass(frozen=True)
class EnvVarLiteralChanges(ContainerConfigChanger):
  """Represents the user intent to modify environment variables string literals.

  Attributes:
    updates: Updated env var names and values to set.
    removes: Env vars to remove.
    clear_others: If true clear all non-updated env vars.
  """

  updates: dict[str, str] = dataclasses.field(default_factory=dict)
  removes: list[str] = dataclasses.field(default_factory=list)
  clear_others: bool = False

  def __init__(self, updates=None, removes=None, clear_others=False, **kwargs):
    super().__init__(**kwargs)
    object.__setattr__(self, 'updates', updates if updates is not None else {})
    object.__setattr__(self, 'removes', removes if removes is not None else [])
    object.__setattr__(self, 'clear_others', clear_others)

  def AdjustContainer(self, container: k8s_min.Container):
    """Mutates the given config's env vars literals to match the desired changes.

    Args:
      container: container to adjust

    Returns:
      The adjusted container

    Raises:
      ConfigurationError if there's an attempt to replace the source of an
        existing environment variable whose source is of a different type
        (e.g. env var's secret source can't be replaced with a config map
        source).
    """
    # Make a copy of the current env vars.
    current_env_vars = list(container.env)
    if self.clear_others:
      # Remove all env var literals that aren't being updated.
      current_env_vars = [
          env_var
          for env_var in current_env_vars
          if 'value_source' in env_var or env_var.name in self.updates
      ]
    # Create a new, updated env vars list.
    updated_env_vars = []
    for env_var in current_env_vars:
      # Secret env vars.
      if 'value_source' in env_var:
        # If the secret env var key is in the updates list, error.
        if env_var.name in self.updates:
          raise exceptions.ConfigurationError(
              'Cannot update environment variable [{}] to string literal'
              ' because it has already been set with a different type.'.format(
                  env_var.name
              )
          )
        # Else, put it in the list without touching it.
        updated_env_vars.append(env_var)
        continue
      # If env var is in removes list, skip it.
      if env_var.name in self.removes:
        continue
      # If env var is in updates list, update the value before appending and
      # remove the key from the updates list.
      if env_var.name in self.updates:
        env_var.value = self.updates[env_var.name]
        self.updates.pop(env_var.name)
      updated_env_vars.append(env_var)
    # Iterate over the remaining items in the updates list and add them as new
    # env var literals.
    for env_var_name, env_var_value in self.updates.items():
      updated_env_vars.append(
          k8s_min.EnvVar(name=env_var_name, value=env_var_value)
      )
    container.env = updated_env_vars


@dataclasses.dataclass(frozen=True)
class DescriptionChange(config_changes.NonTemplateConfigChanger):
  """Represents the user intent to change resource description.

  Attributes:
    description: The description to set.
  """

  description: str

  def Adjust(self, resource):
    """Mutates the given resource's description to match what's desired."""
    resource.description = self.description
    return resource


@dataclasses.dataclass(frozen=True)
class BinaryAuthorizationChange(config_changes.NonTemplateConfigChanger):
  """Represents the user intent to change binary authorization.

  Attributes:
    policy: The binauthz policy to set.
    breakglass_justification: The breakglass justification to set.
    clear_binary_authorization: Whether to clear binary authorization.
  """

  policy: str | None = None
  breakglass_justification: str | None = None
  clear_binary_authorization: bool = False

  def Adjust(self, resource):
    """Mutates the given resource's policy to match what's desired."""
    # Clear binary authorization.
    if self.clear_binary_authorization:
      resource.binary_authorization.use_default = False
      resource.binary_authorization.policy = ''
      resource.binary_authorization.breakglass_justification = ''
      return resource
    # Set binary authorization. Either 'default' or a policy with justification.
    if self.policy == 'default':
      resource.binary_authorization.use_default = True
    elif self.policy:
      resource.binary_authorization.use_default = False
      resource.binary_authorization.policy = self.policy
    if self.breakglass_justification:
      resource.binary_authorization.breakglass_justification = (
          self.breakglass_justification
      )
    return resource


@dataclasses.dataclass(frozen=True)
class LabelChange(config_changes.ConfigChanger):
  """Represents the user intent to modify metadata labels.

  Attributes:
    additions: {str: str}, any label values to be updated
    subtractions: List[str], any labels to be removed
    clear_labels: bool, whether to clear the labels

  Raises:
      ValueError: if both subtractions and clear are specified at the same time.
  """

  additions: dict[str, str] = dataclasses.field(default_factory=dict)
  subtractions: list[str] = dataclasses.field(default_factory=list)
  clear_labels: bool = False

  @property
  def adjusts_template(self):
    return True

  def Adjust(self, resource):
    if self.subtractions and self.clear_labels:
      raise ValueError(
          'Cannot specify both subtractions and clear_labels at the same time.'
      )
    # If clear_labels AND additions, clear_labels takes precedence.
    # If substractions AND additions, additions take precedence.
    # Clear all
    if self.clear_labels:
      resource.labels.clear()
      resource.template.labels.clear()
    # Update
    resource.labels.update(self.additions)
    resource.template.labels.update(self.additions)
    # Remove
    for label_key in self.subtractions:
      resource.labels.pop(label_key, None)
      resource.template.labels.pop(label_key, None)
    return resource


@dataclasses.dataclass(frozen=True)
class VpcAccessChanges(config_changes.TemplateConfigChanger):
  """Represents the user intent to modify VPC access.

  Attributes:
    vpc_egress: str, the vpc egress setting (all traffic, private ranges only).
    network: str, vpc network to set.
    subnet: str, vpc subnet to set.
    network_tags: List[str], vpc network tags to set.
    clear_network: bool, whether to clear the network.
    clear_network_tags: bool, whether to clear the network tags.
  """

  vpc_egress: str | None = None
  network: str | None = None
  subnet: str | None = None
  network_tags: list[str] = dataclasses.field(default_factory=list)
  clear_network: bool = False
  clear_network_tags: bool = False

  def Adjust(self, resource):
    # --clear-network cannot be used with other flags.
    if self.clear_network:
      resource.template.vpc_access.network_interfaces = None
      resource.template.vpc_access.egress = (
          vendor_settings.VpcAccess.VpcEgress.VPC_EGRESS_UNSPECIFIED
      )
      return resource
    # Currently only single network interface is supported.
    if not resource.template.vpc_access.network_interfaces:
      resource.template.vpc_access.network_interfaces.append(
          vendor_settings.VpcAccess.NetworkInterface()
      )
    network_interface = resource.template.vpc_access.network_interfaces[0]
    if self.network:
      network_interface.network = self.network
    if self.subnet:
      network_interface.subnetwork = self.subnet
    if self.network_tags:
      network_interface.tags = self.network_tags
    if self.clear_network_tags:
      network_interface.tags = []
    if self.vpc_egress == 'all' or self.vpc_egress == 'all-traffic':
      resource.template.vpc_access.egress = (
          vendor_settings.VpcAccess.VpcEgress.ALL_TRAFFIC
      )
    elif self.vpc_egress == 'private-ranges-only':
      resource.template.vpc_access.egress = (
          vendor_settings.VpcAccessEgress.PRIVATE_RANGES_ONLY
      )
    return resource


@dataclasses.dataclass(frozen=True)
class CmekKeyChanges(config_changes.TemplateConfigChanger):
  """Represents the user intent to add cmek key related changes.

  Attributes:
    key: str, cmek key to set.
    post_key_revocation_action_type: str, vpc network to set.
    encryption_key_shutdown_hours: int, the number of hours to wait before an
      automatic shutdown server after CMEK key revocation is detected.
    clear_key: bool, whether to clear any previously set CMEK key reference.
    clear_post_key_revocation_action_type: bool, whether to clear any previously
      set post CMEK key revocation action type.
    clear_encryption_key_shutdown_hours: bool, whether to clear any previously
      set CMEK key shutdown hours setting.
  """

  key: str | None = None
  post_key_revocation_action_type: str | None = None
  encryption_key_shutdown_hours: int | None = None
  clear_key: bool = False
  clear_post_key_revocation_action_type: bool = False
  clear_encryption_key_shutdown_hours: bool = False

  def Adjust(self, resource):
    if self.key is not None:
      resource.template.encryption_key = self.key
    if self.post_key_revocation_action_type:
      # At this point, the user has already been validated to use a valid
      # post_key_revocation_action_type flag value.
      resource.template.encryption_key_revocation_action = (
          vendor_settings.EncryptionKeyRevocationAction.PREVENT_NEW
          if self.post_key_revocation_action_type == 'prevent-new'
          else vendor_settings.EncryptionKeyRevocationAction.SHUTDOWN
      )
    if self.encryption_key_shutdown_hours is not None:
      resource.template.encryption_key_shutdown_duration = (
          duration_pb2.Duration(
              seconds=self.encryption_key_shutdown_hours * 3600
          )
      )
    # Clear all CMEK key related settings.
    if self.clear_key:
      resource.template.encryption_key = None
      resource.template.encryption_key_revocation_action = (
          vendor_settings.EncryptionKeyRevocationAction.ENCRYPTION_KEY_REVOCATION_ACTION_UNSPECIFIED
      )
      resource.template.encryption_key_shutdown_duration = None
    # Clear post CMEK key revocation action type and CMEK key shutdown hours.
    if self.clear_post_key_revocation_action_type:
      resource.template.encryption_key_revocation_action = (
          vendor_settings.EncryptionKeyRevocationAction.ENCRYPTION_KEY_REVOCATION_ACTION_UNSPECIFIED
      )
      resource.template.encryption_key_shutdown_duration = None
    # Clear CMEK key shutdown hours.
    if self.clear_encryption_key_shutdown_hours:
      resource.template.encryption_key_shutdown_duration = None
    return resource


# Common config changes to all resource types ends.


# Worker pool specific config changes starts.
@dataclasses.dataclass(frozen=True)
class WorkerPoolScalingChange(config_changes.NonTemplateConfigChanger):
  """Represents the user intent to adjust worker pool scaling.

  Attributes:
    min_instance_count: The minimum count of instances to set.
    max_instance_count: The maximum count of instances to set.
    scaling: Scaling mode to set.
    max_surge: Max surge to set.
    max_unavailable: Max unavailable to set.
  """

  # TODO(b/369135381): For now, this is as simple as setting the fields that's
  # provided. Still need to decided on `default` or unsetting, etc.
  min_instance_count: int | None = None
  max_instance_count: int | None = None
  scaling: flags.ScalingValue | None = None
  max_surge: int | None = None
  max_unavailable: int | None = None

  def Adjust(self, worker_pool_resource: worker_pool.WorkerPool):
    """Adjusts worker pool scaling."""
    scaling = worker_pool_resource.scaling
    if self.min_instance_count is not None:
      scaling.min_instance_count = self.min_instance_count
    if self.max_instance_count is not None:
      scaling.max_instance_count = self.max_instance_count
    if self.max_surge is not None:
      scaling.max_surge = self.max_surge
    if self.max_unavailable is not None:
      scaling.max_unavailable = self.max_unavailable
    if self.scaling is not None:
      # Automatic scaling.
      if self.scaling.auto_scaling:
        scaling.scaling_mode = (
            vendor_settings.WorkerPoolScaling.ScalingMode.AUTOMATIC
        )
      # Manual scaling with flag value as an instance count.
      # TODO(b/376749010): Use manual instance count once supported in V2
      # WorkerPool API.
      else:
        scaling.scaling_mode = (
            vendor_settings.WorkerPoolScaling.ScalingMode.MANUAL
        )
        scaling.min_instance_count = self.scaling.instance_count
        scaling.max_instance_count = None
    return worker_pool_resource


@dataclasses.dataclass(frozen=True)
class InstanceSplitChange(config_changes.NonTemplateConfigChanger):
  """Represents the user intent to change a worker pool's instance split assignments.

  Attributes:
    to_latest: Whether to assign all traffic to the latest revision.
    to_revisions: The new instance split percentages to set based on revision.
  """

  to_latest: bool = False
  to_revisions: dict[str, int] = dataclasses.field(default_factory=dict)

  def Adjust(self, resource: worker_pool.WorkerPool):
    if self.to_latest:
      resource.instance_splits.clear()
      resource.instance_splits.append(
          instance_split.InstanceSplit(
              type=instance_split.InstanceSplitAllocationType.INSTANCE_SPLIT_ALLOCATION_TYPE_LATEST,
              percent=100,
          )
      )
    elif self.to_revisions:
      resource.instance_splits = instance_split_lib.GetUpdatedSplits(
          list(resource.instance_splits), self.to_revisions
      )
    return resource


# Worker pool specific config changes ends.
