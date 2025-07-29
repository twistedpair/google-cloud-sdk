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


def AddClearableExtraAndExtendedAttributesOAuth2Client():
  """Creates an ArgumentGroup for ExtraAttributesOAuth2Client and ExtendedAttributesOAuth2Client Attributes for the update-oidc command."""
  clear_extra_attributes_config_arg = base.Argument(
      '--clear-extra-attributes-config',
      dest='clear_extra_attributes_config',
      action='store_true',
      required=False,
      help='Clear the extra attributes configuration.',
  )
  clear_extended_attributes_config_arg = base.Argument(
      '--clear-extended-attributes-config',
      dest='clear_extended_attributes_config',
      action='store_true',
      required=False,
      help='Clear the extended attributes configuration.',
  )

  clearable_extra_attributes_group = base.ArgumentGroup(mutex=True)
  clearable_extra_attributes_group.AddArgument(
      clear_extra_attributes_config_arg
  )
  clearable_extra_attributes_group.AddArgument(
      ExtraAttributesOAuth2ClientAttributesGroup(required=False)
  )
  clearable_extended_attributes_group = base.ArgumentGroup(
      mutex=True,
  )
  clearable_extended_attributes_group.AddArgument(
      clear_extended_attributes_config_arg
  )
  clearable_extended_attributes_group.AddArgument(
      ExtendedAttributesOAuth2ClientAttributesGroup(required=False)
  )

  return [clearable_extra_attributes_group, clearable_extended_attributes_group]


def AddExtraAndExtendedAttributesOAuth2Client():
  """Creates an ArgumentGroup for ExtraAttributesOAuth2Client and ExtendedAttributesOAuth2Client Attributes for the create-oidc command."""
  return [
      ExtraAttributesOAuth2ClientAttributesGroup(),
      ExtendedAttributesOAuth2ClientAttributesGroup(),
  ]


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
          ' identity provider. Required to get the access token using client'
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
          ' the identity provider. Required to get the access token using'
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
          ' the `https` scheme. Required to get the OIDC discovery'
          ' document.'
      ),
  )
  # Adding this flag as a ArgList to hide `AZURE_AD_GROUPS_DISPLAY_NAME` from
  # the end user. Currently there is no other way to hide new enum choices.
  # These flags will move back to enum types once feature is ready for launch
  extra_attributes_type_arg = base.Argument(
      '--extra-attributes-type',
      dest='extra_attributes_type',
      type=arg_parsers.ArgList(
          choices=[
              'azure-ad-groups-mail',
              'azure-ad-groups-id',
              'azure-ad-groups-display-name',
          ],
          hidden_choices=['azure-ad-groups-display-name'],
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
          'The filter used to request specific records from the IdP. By'
          ' default, all of the groups that are associated with a user are'
          ' fetched. For Microsoft Entra ID, you can add `$search` query'
          ' parameters using [Keyword Query Language]'
          ' (https://learn.microsoft.com/en-us/sharepoint/dev/general-development/keyword-query-language-kql-syntax-reference).'
          ' To learn more about `$search` querying in Microsoft Entra ID, see'
          ' [Use the `$search` query parameter]'
          ' (https://learn.microsoft.com/en-us/graph/search-query-parameter).'
          ' \n\nAdditionally, Workforce Identity Federation automatically adds'
          ' the following [`$filter` query parameters]'
          ' (https://learn.microsoft.com/en-us/graph/filter-query-parameter),'
          ' based on the value of `attributes_type`. Values passed to `filter`'
          ' are converted to `$search` query parameters. Additional `$filter`'
          ' query parameters cannot be added using this field. \n\n*'
          ' `AZURE_AD_GROUPS_MAIL`: `mailEnabled` and `securityEnabled` filters'
          ' are applied. \n* `AZURE_AD_GROUPS_ID`: `securityEnabled` filter is'
          ' applied.'
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


def ExtendedAttributesOAuth2ClientAttributesGroup(required=True):
  """Creates an ArgumentGroup for ExtendedAttributesOAuth2Client Attributes."""
  extended_attributes_client_id_arg = base.Argument(
      '--extended-attributes-client-id',
      dest='extended_attributes_client_id',
      type=str,
      required=required,
      metavar='EXTENDED_ATTRIBUTES_CLIENT_ID',
      help=(
          'The OAuth 2.0 client ID for retrieving extended attributes from the'
          ' identity provider. Required to get extended group memberships for'
          ' a subset of Google Cloud products.'
      ),
  )
  extended_attributes_client_secret_value_arg = base.Argument(
      '--extended-attributes-client-secret-value',
      dest='extended_attributes_client_secret_value',
      type=str,
      required=required,
      metavar='EXTENDED_ATTRIBUTES_CLIENT_SECRET_VALUE',
      help=(
          'The OAuth 2.0 client secret for retrieving extended attributes from'
          ' the identity provider. Required to get extended group memberships'
          ' for a subset of Google Cloud products.'
      ),
  )
  extended_attributes_issuer_uri_arg = base.Argument(
      '--extended-attributes-issuer-uri',
      dest='extended_attributes_issuer_uri',
      type=str,
      required=required,
      metavar='EXTENDED_ATTRIBUTES_ISSUER_URI',
      help=(
          "OIDC identity provider's issuer URI. Must be a valid URI using"
          ' the `https` scheme. Required to get the OIDC discovery'
          ' document.'
      ),
  )
  # Adding this flag as a ArgList to hide `AZURE_AD_GROUPS_DISPLAY_NAME` from
  # the end user. Currently there is no other way to hide new enum choices.
  # These flags will move back to enum types once feature is ready for launch
  extended_attributes_type_arg = base.Argument(
      '--extended-attributes-type',
      dest='extended_attributes_type',
      type=arg_parsers.ArgList(
          choices=[
              'azure-ad-groups-id',
          ],
          max_length=1,
          min_length=1,
      ),
      required=required,
      metavar='EXTENDED_ATTRIBUTES_TYPE',
      help=(
          'Represents the identity provider and type of claims that should'
          ' be fetched.'
      ),
  )
  extended_attributes_filter_arg = base.Argument(
      '--extended-attributes-filter',
      dest='extended_attributes_filter',
      type=str,
      required=False,
      metavar='EXTENDED_ATTRIBUTES_FILTER',
      help=(
          'The filter used to request specific records from the IdP. By'
          ' default, all of the groups that are associated with a user are'
          ' fetched. For Microsoft Entra ID, you can add `$search` query'
          ' parameters using [Keyword Query Language]'
          ' (https://learn.microsoft.com/en-us/sharepoint/dev/general-development/keyword-query-language-kql-syntax-reference).'
          ' To learn more about `$search` querying in Microsoft Entra ID, see'
          ' [Use the `$search` query parameter]'
          ' (https://learn.microsoft.com/en-us/graph/search-query-parameter).'
          ' \n\nAdditionally, Workforce Identity Federation automatically adds'
          ' the following [`$filter` query parameters]'
          ' (https://learn.microsoft.com/en-us/graph/filter-query-parameter),'
          ' based on the value of `attributes_type`. Values passed to `filter`'
          ' are converted to `$search` query parameters. Additional `$filter`'
          ' query parameters cannot be added using this field. \n\n*'
          ' `AZURE_AD_GROUPS_ID`: `securityEnabled` filter is applied.'
      ),
  )
  create_extended_attributes_group = base.ArgumentGroup()
  create_extended_attributes_group.AddArgument(
      extended_attributes_client_id_arg
  )
  create_extended_attributes_group.AddArgument(
      extended_attributes_client_secret_value_arg
  )
  create_extended_attributes_group.AddArgument(
      extended_attributes_issuer_uri_arg
  )
  create_extended_attributes_group.AddArgument(extended_attributes_type_arg)
  create_extended_attributes_group.AddArgument(extended_attributes_filter_arg)

  return create_extended_attributes_group
