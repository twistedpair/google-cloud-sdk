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

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.util.apis import arg_utils
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
      hidden_choices=['biglake'],
      required=True,
      help_str='Catalog type to create the catalog with.',
      custom_mappings={
          'CATALOG_TYPE_GCS_BUCKET': (
              'gcs-bucket',
              'A catalog backed by a Cloud Storage bucket.',
          ),
          'CATALOG_TYPE_BIGLAKE': (
              'biglake',
              (
                  'BigLake Iceberg catalog. Catalog type which allows'
                  ' namespaces and tables within a catalog to be mapped to'
                  ' locations beyond the catalog\'s designated default.'
              ),
          ),
      },
  )


def GetUpdateCatalogTypeEnumMapper(release_track):
  messages = GetMessagesModule(release_track)
  catalog_type_enum = messages.IcebergCatalog.CatalogTypeValueValuesEnum
  return arg_utils.ChoiceEnumMapper(
      '--catalog-type',
      catalog_type_enum,
      hidden=True,
      required=False,
      help_str=(
          'Catalog type to update the catalog with. Currently only updating to '
          'a BigLake catalog type is supported.'
      ),
      custom_mappings={
          'CATALOG_TYPE_BIGLAKE': (
              'biglake',
              (
                  'BigLake Iceberg catalog. Catalog type which allows'
                  ' namespaces and tables within a catalog to be mapped to'
                  " locations beyond the catalog's designated default."
              ),
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


def GcsBucketLinkValidator(value):
  if not value.startswith('gs://'):
    raise arg_parsers.ArgumentTypeError(
        'Location must be a Google Cloud Storage URI starting with `gs://`'
    )
  return value


def AddDefaultLocationArg(parser):
  parser.add_argument(
      '--default-location',
      hidden=True,
      type=GcsBucketLinkValidator,
      help=(
          'Can only be used with BigLake catalogs. The default'
          ' storage location for the catalog, e.g., `gs://my-bucket/...`.'
      ),
  )


def AddAdditionalLocationsArg(parser):
  parser.add_argument(
      '--additional-locations',
      hidden=True,
      type=arg_parsers.ArgList(element_type=GcsBucketLinkValidator),
      metavar='LOCATION',
      help=(
          'Can only be used with BigLake catalogs. Additional'
          ' Google Cloud Storage buckets and locations (e.g.,'
          ' `gs://my-other-bucket/...`) that are permitted for use by'
          ' resources within a catalog.'
      ),
  )


def CheckValidArgCombinations(args):
  """Checks for valid combinations of arguments.

  Ensures that `--default-location` and `--additional-locations`
  are only used when `--catalog-type` is 'BigLake'.

  Args:
    args: The parsed command-line arguments.

  Raises:
    arg_parsers.ArgumentTypeError: If an invalid argument combination is found.
  """
  if args.catalog_type == 'biglake' and not args.IsSpecified(
      'default_location'
  ):
    raise arg_parsers.ArgumentTypeError(
        '--default-location must be specified when catalog type is BigLake.'
    )
  elif args.catalog_type != 'biglake' and args.IsSpecified(
      'default_location'
  ):
    raise arg_parsers.ArgumentTypeError(
        '--default-location is only supported for BigLake catalogs.'
    )
  elif args.catalog_type != 'biglake' and args.IsSpecified(
      'additional_locations'
  ):
    raise arg_parsers.ArgumentTypeError(
        '--additional-locations is only supported for BigLake catalogs.'
    )
