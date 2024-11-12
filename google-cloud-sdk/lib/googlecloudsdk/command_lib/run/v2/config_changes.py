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

from google.api import launch_stage_pb2  # pytype: disable=import-error
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.run import config_changes
from googlecloudsdk.command_lib.run import flags
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


# Worker pool specific config changes ends.
