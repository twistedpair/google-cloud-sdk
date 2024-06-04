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
"""Common flags for workforce pools commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


def AddParentFlags(parser, verb):
  parser.add_argument(
      '--organization',
      help='The parent organization of the workforce pool{0} to {1}.'.format(
          's' if verb == 'list' else '', verb
      ),
      required=True,
  )


def AddLocationFlag(parser, verb):
  parser.add_argument(
      '--location',
      help='The location of the workforce pool{0} to {1}.'.format(
          's' if verb == 'list' else '', verb
      ),
      required=True,
  )


def ParseLocation(args):
  if not args.IsSpecified('location'):
    return 'locations/global'
  return 'locations/{}'.format(args.location)


def AddClearableExtraAttributesOAuth2Client():
  """Creates an ArgumentGroup for ExtraAttributesOAuth2Client Attributes for the update-oidc command."""
  clear_extra_attributes_config_arg = base.Argument(
      '--clear-extra-attributes-config',
      dest='clear_extra_attributes_config',
      action='store_true',
      required=False,
      help='Clear the extra attributes configuration.',
  )

  clearable_extra_attributes_group = base.ArgumentGroup(mutex=True)
  clearable_extra_attributes_group.AddArgument(
      clear_extra_attributes_config_arg
  )
  clearable_extra_attributes_group.AddArgument(
      ExtraAttributesOAuth2ClientAttributesGroup(required=False)
  )

  return [clearable_extra_attributes_group]


def AddExtraAttributesOAuth2Client():
  """Creates an ArgumentGroup for ExtraAttributesOAuth2Client Attributes for the create-oidc command."""
  return [ExtraAttributesOAuth2ClientAttributesGroup()]


def ExtraAttributesOAuth2ClientAttributesGroup(required=True):
  """Creates an ArgumentGroup for ExtraAttributesOAuth2Client Attributes."""
  extra_attributes_client_id_arg = base.Argument(
      '--extra-attributes-client-id',
      dest='extra_attributes_client_id',
      type=str,
      required=required,
      metavar='EXTRA_ATTRIBUTES_CLIENT_ID',
      help=(
          'The OAuth 2.0 client ID for retrieving extra attributes from the'
          ' identity provider. Required to get the Access Token using client'
          ' credentials grant flow.'
      ),
  )
  extra_attributes_client_secret_value_arg = base.Argument(
      '--extra-attributes-client-secret-value',
      dest='extra_attributes_client_secret_value',
      type=str,
      required=required,
      metavar='EXTRA_ATTRIBUTES_CLIENT_SECRET_VALUE',
      help=(
          'The OAuth 2.0 client secret for retrieving extra attributes from'
          ' the identity provider. Required to get the Access Token using'
          ' client credentials grant flow.'
      ),
  )
  extra_attributes_issuer_uri_arg = base.Argument(
      '--extra-attributes-issuer-uri',
      dest='extra_attributes_issuer_uri',
      type=str,
      required=required,
      metavar='EXTRA_ATTRIBUTES_ISSUER_URI',
      help=(
          "OIDC identity provider's issuer URI. Must be a valid URI using"
          " the 'https' scheme. Required to get the OIDC discovery"
          ' document.'
      ),
  )
  # Adding this flag as a ArgList to hide `AZURE_AD_GROUPS_ID` from the end user
  # . Currently there is no other way to hide new enum choices. These flags will
  # move back to enum types once feature is ready for launch
  extra_attributes_type_arg = base.Argument(
      '--extra-attributes-type',
      dest='extra_attributes_type',
      type=arg_parsers.ArgList(
          choices=[
              'azure-ad-groups-mail',
              'azure-ad-groups-id',
          ],
          visible_choices=['azure-ad-groups-mail'],
          max_length=1,
          min_length=1,
      ),
      required=required,
      metavar='EXTRA_ATTRIBUTES_TYPE',
      help=(
          'Represents the identity provider and type of claims that should'
          ' be fetched.'
      ),
  )
  extra_attributes_filter_arg = base.Argument(
      '--extra-attributes-filter',
      dest='extra_attributes_filter',
      type=str,
      required=False,
      metavar='EXTRA_ATTRIBUTES_FILTER',
      help=(
          'The filter used to request specific records from IdP. In case of'
          ' attributes type as AZURE_AD_GROUPS_MAIL, it represents the'
          ' filter used to request specific groups for users from IdP. By'
          ' default all the groups associated with the user are fetched.'
          ' The groups that are used should be mail enabled and security'
          ' enabled. See'
          ' https://learn.microsoft.com/en-us/graph/search-query-parameter'
          ' for more details.'
      ),
  )

  create_extra_attributes_group = base.ArgumentGroup()
  create_extra_attributes_group.AddArgument(extra_attributes_client_id_arg)
  create_extra_attributes_group.AddArgument(
      extra_attributes_client_secret_value_arg
  )
  create_extra_attributes_group.AddArgument(extra_attributes_issuer_uri_arg)
  create_extra_attributes_group.AddArgument(extra_attributes_type_arg)
  create_extra_attributes_group.AddArgument(extra_attributes_filter_arg)

  return create_extra_attributes_group
