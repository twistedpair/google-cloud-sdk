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

"""Contains shared methods for container and volume printing."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections
from typing import Mapping

from googlecloudsdk.api_lib.run import container_resource
from googlecloudsdk.command_lib.run.printers import k8s_object_printer_util as k8s_util
from googlecloudsdk.core.resource import custom_printer_base as cp


def _FormatSecretKeyRef(v):
  return '{}:{}'.format(v.secretKeyRef.name, v.secretKeyRef.key)


def _FormatSecretVolumeSource(v):
  if v.items:
    return '{}:{}'.format(v.secretName, v.items[0].key)
  else:
    return v.secretName


def _FormatConfigMapKeyRef(v):
  return '{}:{}'.format(v.configMapKeyRef.name, v.configMapKeyRef.key)


def _FormatConfigMapVolumeSource(v):
  if v.items:
    return '{}:{}'.format(v.name, v.items[0].key)
  else:
    return v.name


def GetContainer(
    container: container_resource.Container,
    labels: Mapping[str, str],
    is_primary: bool,
) -> cp.Table:
  limits = GetLimits(container)
  return cp.Labeled([
      ('Image', container.image),
      ('Command', ' '.join(container.command)),
      ('Args', ' '.join(container.args)),
      (
          'Port',
          ' '.join(str(p.containerPort) for p in container.ports),
      ),
      ('Memory', limits['memory']),
      ('CPU', limits['cpu']),
      (
          'Env vars',
          GetUserEnvironmentVariables(container),
      ),
      ('Secrets', GetSecrets(container)),
      ('Config Maps', GetConfigMaps(container)),
      (
          'Startup Probe',
          k8s_util.GetStartupProbe(container, labels, is_primary),
      ),
      ('Liveness Probe', k8s_util.GetLivenessProbe(container)),
  ])


def GetContainers(record: container_resource.ContainerResource) -> cp.Table:
  def Containers():
    for name, container in k8s_util.OrderByKey(record.containers):
      key = 'Container {name}'.format(name=name)
      value = GetContainer(
          container,
          record.labels,
          len(record.containers) == 1 or container.ports,
      )
      yield (key, value)

  return cp.Mapped(Containers())


def GetLimits(record):
  return collections.defaultdict(str, record.resource_limits)


def GetUserEnvironmentVariables(record):
  return cp.Mapped(k8s_util.OrderByKey(record.env_vars.literals))


def GetSecrets(container: container_resource.Container) -> cp.Table:
  """Returns a print mapping for env var and volume-mounted secrets."""
  secrets = {}
  secrets.update(
      {k: _FormatSecretKeyRef(v) for k, v in container.env_vars.secrets.items()}
  )
  secrets.update(
      {
          k: _FormatSecretVolumeSource(v)
          for k, v in container.MountedVolumeJoin('secrets').items()
      }
  )
  return cp.Mapped(k8s_util.OrderByKey(secrets))


def GetConfigMaps(container: container_resource.Container) -> cp.Table:
  """Returns a print mapping for env var and volume-mounted config maps."""
  config_maps = {}
  config_maps.update(
      {
          k: _FormatConfigMapKeyRef(v)
          for k, v in container.env_vars.config_maps.items()
      }
  )
  config_maps.update(
      {
          k: _FormatConfigMapVolumeSource(v)
          for k, v in container.MountedVolumeJoin('config_maps').items()
      }
  )
  return cp.Mapped(k8s_util.OrderByKey(config_maps))
