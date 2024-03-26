# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Commonly used display formats."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.command_lib.secrets import args as secrets_args


_LOCATION_TABLE = """
table(
  name.basename():label=NAME,
  displayName:label=LOCATION
)
"""

_SECRET_DATA = """
value[terminator="",private](
  payload.data.decode(base64).decode(utf8)
)
"""

_SECRET_TABLE = """
table(
  name.basename():label=NAME,
  createTime.date():label=CREATED,
  policy_transform():label=REPLICATION_POLICY,
  locations_transform():label=LOCATIONS
)
"""

_REGIONAL_SECRET_TABLE = """
table(
  name.basename():label=NAME,
  createTime.date():label=CREATED
)
"""

_VERSION_TABLE = """
table(
  name.basename():label=NAME,
  state.enum(secrets.StateVersionJobState).color('destroyed', 'disabled', 'enabled', 'unknown'):label=STATE,
  createTime.date():label=CREATED,
  destroyTime.date(undefined='-'):label=DESTROYED
)
"""

_VERSION_STATE_TRANSFORMS = {
    'secrets.StateVersionJobState::enum': {
        'STATE_UNSPECIFIED': 'unknown',
        'ENABLED': 'enabled',
        'DISABLED': 'disabled',
        'DESTROYED': 'destroyed',
    }
}


def _TransformReplicationPolicy(r):
  if 'replication' not in r:
    return 'ERROR'
  if 'automatic' in r['replication']:
    return 'automatic'
  if 'userManaged' in r['replication']:
    return 'user_managed'
  return 'ERROR'


def _TransformLocations(r):
  if 'replication' not in r:
    return 'ERROR'
  if 'automatic' in r['replication']:
    return '-'
  if 'userManaged' in r['replication'] and 'replicas' in r['replication'][
      'userManaged']:
    locations = []
    for replica in r['replication']['userManaged']['replicas']:
      locations.append(replica['location'])
    return ','.join(locations)
  return 'ERROR'


_SECRET_TRANSFORMS = {
    'policy_transform': _TransformReplicationPolicy,
    'locations_transform': _TransformLocations,
}


def UseLocationTable(
    parser: parser_arguments.ArgumentInterceptor, api_version: str = 'v1'
):
  """Table format to display locations.

  Args:
    parser: arguments interceptor
    api_version: api version to be included in resource name
  """
  parser.display_info.AddFormat(_LOCATION_TABLE)
  parser.display_info.AddUriFunc(
      secrets_args.MakeGetUriFunc(
          'secretmanager.projects.locations', api_version=api_version
      )
  )


def UseSecretTable(parser: parser_arguments.ArgumentInterceptor):
  """Table format to display secrets.

  Args:
    parser: arguments interceptor
  """
  parser.display_info.AddFormat(_SECRET_TABLE)
  parser.display_info.AddTransforms(_SECRET_TRANSFORMS)
  parser.display_info.AddUriFunc(
      lambda r: secrets_args.ParseSecretRef(r.name).SelfLink()
  )


def SecretTableUsingArgument(
    args: parser_extensions.Namespace, api_version: str = 'v1'
):
  """Table format to display global secrets.

  Args:
    args: arguments interceptor
    api_version: api version to be included in resource name
  """
  args.GetDisplayInfo().AddFormat(_SECRET_TABLE)
  args.GetDisplayInfo().AddTransforms(_SECRET_TRANSFORMS)
  args.GetDisplayInfo().AddUriFunc(
      secrets_args.MakeGetUriFunc(
          'secretmanager.projects.secrets', api_version=api_version
      )
  )


def RegionalSecretTableUsingArgument(
    args: parser_extensions.Namespace, api_version: str = 'v1'
):
  """Table format to display regional secrets.

  Args:
    args: arguments interceptor
    api_version: api version to be included in resource name
  """
  args.GetDisplayInfo().AddFormat(_REGIONAL_SECRET_TABLE)
  args.GetDisplayInfo().AddTransforms(_SECRET_TRANSFORMS)
  args.GetDisplayInfo().AddUriFunc(
      secrets_args.MakeGetUriFunc(
          'secretmanager.projects.locations.secrets', api_version=api_version
      )
  )


def UseSecretData(parser):
  parser.display_info.AddFormat(_SECRET_DATA)


def UseVersionTable(
    parser: parser_arguments.ArgumentInterceptor, api_version='v1'
):
  """Table format to display secret versions.

  Args:
    parser: arguments interceptor
    api_version: api version to be included in resource name
  """
  parser.display_info.AddFormat(_VERSION_TABLE)
  parser.display_info.AddTransforms(_VERSION_STATE_TRANSFORMS)
  secrets_args.MakeGetUriFunc(
      'secretmanager.projects.locations.secrets.versions',
      api_version=api_version,
  )


def UseRegionalVersionTable(
    parser: parser_arguments.ArgumentInterceptor, api_version='v1'
):
  """Table format to display regional secret versions.

  Args:
    parser: arguments interceptor
    api_version: api version to be included in resource name
  """
  parser.display_info.AddFormat(_VERSION_TABLE)
  parser.display_info.AddTransforms(_VERSION_STATE_TRANSFORMS)
  secrets_args.MakeGetUriFunc(
      'secretmanager.projects.locations.secrets.versions',
      api_version=api_version,
  )


def SecretVersionTableUsingArgument(
    args: parser_extensions.Namespace, api_version: str = 'v1'
):
  """Table format to display global secret version.

  Args:
    args: arguments interceptor
    api_version: api version to be included in resource name
  """
  args.GetDisplayInfo().AddFormat(_VERSION_TABLE)
  args.GetDisplayInfo().AddTransforms(_VERSION_STATE_TRANSFORMS)
  args.GetDisplayInfo().AddUriFunc(
      secrets_args.MakeGetUriFunc(
          'secretmanager.projects.secrets.versions', api_version=api_version
      )
  )


def RegionalSecretVersionTableUsingArgument(
    args: parser_extensions.Namespace, api_version: str = 'v1'
):
  """Table format to display regional secrets.

  Args:
    args: arguments interceptor
    api_version: api version to be included in resource name
  """
  args.GetDisplayInfo().AddFormat(_VERSION_TABLE)
  args.GetDisplayInfo().AddTransforms(_VERSION_STATE_TRANSFORMS)
  args.GetDisplayInfo().AddUriFunc(
      secrets_args.MakeGetUriFunc(
          'secretmanager.projects.locations.secrets.versions',
          api_version=api_version,
      )
  )
