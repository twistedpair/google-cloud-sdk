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

"""Contains shared methods for volume printing."""

from typing import Sequence

from googlecloudsdk.command_lib.run.printers import k8s_object_printer_util as k8s_util
from googlecloudsdk.core.resource import custom_printer_base as cp
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import k8s_min


def _FormatVersionToPath(
    version_to_path: k8s_min.VersionToPath,
) -> str:
  return (
      f'path: {version_to_path.path}, version: {version_to_path.version}, mode:'
      f' {version_to_path.mode}'
  )


def _FormatVolume(volume: k8s_min.Volume) -> cp.Table:
  """Format a volume for the volumes list."""
  if volume.empty_dir:
    return cp.Labeled([
        ('type', 'in-memory'),
        ('size-limit', volume.empty_dir.size_limit),
    ])
  elif volume.nfs:
    return cp.Labeled([
        ('type', 'nfs'),
        ('location', '{}:{}'.format(volume.nfs.server, volume.nfs.path)),
        ('read-only', volume.nfs.read_only),
    ])
  elif volume.gcs:
    return cp.Labeled([
        ('type', 'cloud-storage'),
        ('bucket', volume.gcs.bucket),
        ('read-only', volume.gcs.read_only),
        ('mount-options', volume.gcs.mount_options),
    ])
  elif volume.secret:
    return cp.Labeled([
        ('type', 'secret'),
        ('secret', volume.secret.secret),
        ('default-mode', volume.secret.default_mode),
        ('items', [_FormatVersionToPath(i) for i in volume.secret.items]),
    ])
  elif volume.cloud_sql_instance:
    return cp.Labeled([
        ('type', 'cloudsql'),
        ('instances', volume.cloud_sql_instance.instances),
    ])
  else:
    return cp.Labeled([('type', 'unknown')])


def GetVolumes(volumes: Sequence[k8s_min.Volume]) -> cp.Table:
  """Returns a formatted table of a resource's volumes.

  Args:
    volumes: A list of volumes.

  Returns:
    A formatted table of a resource's volumes.
  """

  def Volumes():
    volumes_dict = {volume.name: volume for volume in volumes}
    for _, volume in k8s_util.OrderByKey(volumes_dict):
      key = f'volume {volume.name}'
      value = _FormatVolume(volume)
      yield (key, value)

  return cp.Mapped(Volumes())
