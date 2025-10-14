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

"""A library that is used to support our commands."""

from googlecloudsdk.command_lib.util.apis import arg_utils

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v1',
    base.ReleaseTrack.BETA: 'v1',
    base.ReleaseTrack.GA: 'v1',
}


# The messages module can also be accessed from client.MESSAGES_MODULE
def GetMessagesModule(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetMessagesModule('biglake', api_version)


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetClientInstance('biglake', api_version)


def GetCatalogRef(catalog):
  """Get a resource reference to a catalog."""
  return resources.REGISTRY.Parse(
      catalog,  # in the format of projects/{project-id}/catalogs/{catalog-id}
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail,
      },
      collection='biglake.iceberg.v1.restcatalog.extensions.projects.catalogs',
  )


def GetCatalogName(catalog_id):
  """Get the catalog name in the format of projects/{project-id}/catalogs/{catalog-id}."""
  return f'projects/{properties.VALUES.core.project.GetOrFail()}/catalogs/{catalog_id}'


def GetParentName():
  """Get the parent name in the format of projects/{project-id}."""
  return f'projects/{properties.VALUES.core.project.GetOrFail()}'


def GetCatalogTypeEnumMapper(release_track):
  messages = GetMessagesModule(release_track)
  catalog_type_enum = messages.IcebergCatalog.CatalogTypeValueValuesEnum
  return arg_utils.ChoiceEnumMapper(
      '--catalog-type',
      catalog_type_enum,
      required=True,
      help_str='Catalog type to create the catalog with.',
      custom_mappings={
          'CATALOG_TYPE_GCS_BUCKET': (
              'gcs-bucket',
              'A catalog backed by a GCS bucket.',
          ),
      },
  )


def GetCredentialModeEnumMapper(release_track):
  messages = GetMessagesModule(release_track)
  credential_mode_enum = messages.IcebergCatalog.CredentialModeValueValuesEnum
  return arg_utils.ChoiceEnumMapper(
      '--credential-mode',
      credential_mode_enum,
      default='end-user',
      help_str='Credential mode to create the catalog with.',
      custom_mappings={
          'CREDENTIAL_MODE_END_USER': (
              'end-user',
              'Use end user credentials to access the catalog.',
          ),
          'CREDENTIAL_MODE_VENDED_CREDENTIALS': (
              'vended-credentials',
              'Use vended credentials to access the catalog.',
          ),
      },
  )
