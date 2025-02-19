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
"""Utilities for working with volumes."""

from __future__ import absolute_import
from __future__ import annotations
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
from typing import TypedDict

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.run import exceptions as serverless_exceptions
from googlecloudsdk.generated_clients.gapic_clients.run_v2 import types

Volume = types.Volume
SecretVolumeSource = types.SecretVolumeSource
NFSVolumeSource = types.NFSVolumeSource
GCSVolumeSource = types.GCSVolumeSource
EmptyDirVolumeSource = types.EmptyDirVolumeSource
CloudSqlInstance = types.CloudSqlInstance
VersionToPath = types.VersionToPath
Medium = types.EmptyDirVolumeSource.Medium


def _IsReadOnly(volume_dict: VolumeDict) -> bool:
  return (
      'readonly' in volume_dict
      and str(volume_dict['readonly']).lower() == 'true'
  )


def _ValidateAndBuildEmptyDirVolume(volume_dict: VolumeDict) -> Volume:
  """Validates and builds an empty dir volume."""
  source = EmptyDirVolumeSource(medium=Medium.MEMORY)
  if 'size-limit' in volume_dict:
    source.size_limit = volume_dict['size-limit']
  return Volume(
      name=volume_dict['name'],
      empty_dir=source,
  )


def _ValidateAndBuildGCSVolume(
    volume_dict: VolumeDict, release_track: base.ReleaseTrack
) -> Volume:
  """Validates and builds a GCS volume."""
  if release_track == base.ReleaseTrack.ALPHA:
    try:
      bool_parser = arg_parsers.ArgBoolean()
      dynamic_mounting = bool_parser(
          volume_dict.get('dynamic-mounting', 'false')
      )
    except argparse.ArgumentTypeError:
      raise serverless_exceptions.ConfigurationError(
          'dynamic-mounting must be set to true or false.'
      )
    if (dynamic_mounting and 'bucket' in volume_dict) or (
        not dynamic_mounting and 'bucket' not in volume_dict
    ):
      raise serverless_exceptions.ConfigurationError(
          'Either set bucket or enable dynamic-mounting, not both.'
      )
  if 'mount-options' in volume_dict:
    mount_options = volume_dict['mount-options'].split(';')
  else:
    mount_options = []
  source = GCSVolumeSource(
      read_only=_IsReadOnly(volume_dict),
      mount_options=mount_options,
  )
  # If dynamic mounting is enabled, we need to set the bucket to a special
  # value to indicate that the bucket should be dynamically mounted.
  if 'dynamic-mounting' in volume_dict and volume_dict['dynamic-mounting']:
    source.bucket = '_'
  else:
    source.bucket = volume_dict['bucket']
  return Volume(
      name=volume_dict['name'],
      gcs=source,
  )


def _ValidateAndBuildNFSVolume(volume_dict: VolumeDict) -> Volume:
  """Validates and builds an NFS volume."""
  if 'location' not in volume_dict:
    raise serverless_exceptions.ConfigurationError(
        'All NFS volumes must have a location specified in the form'
        ' SERVER:/PATH'
    )
  read_only = _IsReadOnly(volume_dict)
  location = volume_dict['location']
  if ':/' not in location:
    raise serverless_exceptions.ConfigurationError(
        "Volume {}: field 'location' must be of the form"
        ' IP_ADDRESS:/DIRECTORY'.format(volume_dict['name'])
    )
  server, path = str(location).split(':/', 1)
  # need to re-add leading slash
  path = '/' + path
  return Volume(
      name=volume_dict['name'],
      nfs=NFSVolumeSource(
          server=server,
          path=path,
          read_only=read_only,
      ),
  )


def _ValidateAndBuildSecretVolume(
    volume_dict: VolumeDict, release_track: base.ReleaseTrack
) -> Volume:
  """Validates and builds a secret volume."""
  if release_track != base.ReleaseTrack.ALPHA:
    raise serverless_exceptions.ConfigurationError(
        'Secret volumes are not supported in this release track'
    )
  if (
      'secret' not in volume_dict
      or 'version' not in volume_dict
      or 'path' not in volume_dict
  ):
    raise serverless_exceptions.ConfigurationError(
        'All secret volumes must have a secret, version, and path specified'
    )
  return Volume(
      name=volume_dict['name'],
      secret=SecretVolumeSource(
          secret=volume_dict['secret'],
          items=[
              VersionToPath(
                  version=volume_dict['version'], path=volume_dict['path']
              )
          ],
      ),
  )


def _ValidateAndBuildCloudSqlVolume(
    volume_dict: VolumeDict, release_track: base.ReleaseTrack
) -> Volume:
  """Validates and builds a Cloud SQL volume."""
  if release_track != base.ReleaseTrack.ALPHA:
    raise serverless_exceptions.ConfigurationError(
        'Cloud SQL volumes are not supported in this release track'
    )
  if 'instances' not in volume_dict:
    raise serverless_exceptions.ConfigurationError(
        'Cloud SQL volumes must have at least one instance specified'
    )
  if volume_dict['name'] != 'cloudsql':
    raise serverless_exceptions.ConfigurationError(
        'Cloud SQL volumes can only be named "cloudsql" and can only be mounted'
        ' at /cloudsql.'
    )
  for instance in volume_dict['instances'].split(';'):
    instance = instance.strip().split(':')
    if len(instance) != 3:
      raise serverless_exceptions.ConfigurationError(
          'Cloud SQL instance names must be in the form'
          ' PROJECT_ID:REGION:INSTANCE_ID but got {}'.format(instance)
      )
  return Volume(
      name=volume_dict['name'],
      cloud_sql_instance=CloudSqlInstance(
          instances=[
              instance.strip()
              for instance in volume_dict['instances'].split(';')
          ]
      ),
  )


VolumeDict = TypedDict(
    'VolumeDict',
    {
        'name': str,
        'type': str,
        'read-only': str,
        'bucket': str,
        'location': str,
        'size-limit': str,
        'dynamic-mounting': str,
        'mount-options': str,
        'secret': str,
        'version': str,
        'path': str,
        'instances': str,
    },
    total=False,
)


# TODO: b/391606593 - Refactor this file to use factory methods instead of a
# single CreateVolume method, like in
# third_party/py/googlecloudsdk/command_lib/run/volumes.py.
def CreateVolume(
    volume_dict: VolumeDict,
    release_track: base.ReleaseTrack = base.ReleaseTrack.ALPHA,
) -> Volume:
  """Creates the volume instance described by the given volume dict."""
  if 'name' not in volume_dict or 'type' not in volume_dict:
    raise serverless_exceptions.ConfigurationError(
        'All added volumes must have a name and type'
    )
  if volume_dict['type'] == 'in-memory':
    return _ValidateAndBuildEmptyDirVolume(volume_dict)
  elif volume_dict['type'] == 'cloud-storage':
    return _ValidateAndBuildGCSVolume(volume_dict, release_track)
  elif volume_dict['type'] == 'nfs':
    return _ValidateAndBuildNFSVolume(volume_dict)
  elif volume_dict['type'] == 'secret':
    return _ValidateAndBuildSecretVolume(volume_dict, release_track)
  elif volume_dict['type'] == 'cloudsql':
    return _ValidateAndBuildCloudSqlVolume(volume_dict, release_track)
  else:
    raise serverless_exceptions.ConfigurationError(
        'Volume type {} not supported'.format(volume_dict['type'])
    )
