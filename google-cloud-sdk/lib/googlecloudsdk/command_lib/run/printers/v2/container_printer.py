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

"""Contains shared methods for container printing."""

from typing import Sequence

from googlecloudsdk.command_lib.run.printers import k8s_object_printer_util as k8s_util
from googlecloudsdk.core.resource import custom_printer_base as cp
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import k8s_min


def _GetUserEnvironmentVariables(container: k8s_min.Container):
  return cp.Mapped(
      k8s_util.OrderByKey(
          {env_var.name: env_var.value for env_var in container.env}
      )
  )


def _GetContainer(container: k8s_min.Container) -> cp.Table:
  return cp.Labeled([
      ('Image', container.image),
      ('Command', ' '.join(container.command)),
      ('Args', ' '.join(container.args)),
      ('Memory', container.resources.limits['memory']),
      ('CPU', container.resources.limits['cpu']),
      (
          'Env vars',
          _GetUserEnvironmentVariables(container),
      ),
      # TODO(b/366115709): add volume mounts
      # TODO(b/366115709): add secrets
      ('Container Dependencies', ', '.join(container.depends_on)),
  ])


def GetContainers(containers: Sequence[k8s_min.Container]) -> cp.Table:
  """Returns a formatted table of a resource's containers.

  Args:
    containers: A list of containers.

  Returns:
    A formatted table of a resource's containers.
  """

  def Containers():
    containers_dict = {container.name: container for container in containers}
    for _, container in k8s_util.OrderByKey(containers_dict):
      key = f'Container {container.name}'
      value = _GetContainer(container)
      yield (key, value)

  return cp.Mapped(Containers())
