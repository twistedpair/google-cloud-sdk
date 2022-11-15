# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Utils for GKE Hub Identity Service commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
import urllib3

# The max number of auth methods allowed per config.
MAX_AUTH_PROVIDERS = 20


def parse_config(loaded_config, msg):
  """Load FeatureSpec MemberConfig from the parsed ClientConfig CRD yaml file.

  Args:
    loaded_config: YamlConfigFile, The data loaded from the ClientConfig CRD
      yaml file given by the user. YamlConfigFile is from
      googlecloudsdk.command_lib.anthos.common.file_parsers.
    msg: The gkehub messages package.

  Returns:
    member_config: The MemberConfig configuration containing the AuthMethods for
      the IdentityServiceFeatureSpec.
  """

  # Get list of auth providers from ClientConfig.
  if len(loaded_config.data) != 1:
    raise exceptions.Error('Input config file must contain one YAML document.')
  clientconfig = loaded_config.data[0]
  validate_clientconfig_meta(clientconfig)
  auth_providers = clientconfig.GetAuthProviders(name_only=False)

  # Don't accept configs containing more auth providers than MAX_AUTH_PROVIDERS
  auth_providers_count = len(auth_providers)
  if auth_providers_count > MAX_AUTH_PROVIDERS:
    err_msg = ('The provided configuration contains {} identity providers. '
               'The maximum number that can be provided is {}.').format(
                   auth_providers_count, MAX_AUTH_PROVIDERS)
    raise exceptions.Error(err_msg)

  # Create empty MemberConfig and populate it with Auth_Provider configurations.
  member_config = msg.IdentityServiceMembershipSpec()
  # The config must contain at least one auth method
  found_auth_method = False
  for auth_provider in auth_providers:
    # Provision OIDC proto from OIDC ClientConfig dictionary.
    if 'oidc' in auth_provider:
      auth_method = provision_oidc_config(auth_provider, msg)
      member_config.authMethods.append(auth_method)
      found_auth_method = True
    # Provision Google proto from Google ClientConfig dictionary.
    elif 'google' in auth_provider:
      auth_method = provision_google_config(auth_provider, msg)
      member_config.authMethods.append(auth_method)
      found_auth_method = True
    # Provision AzureAD proto from AzureAD ClientConfig dictionary.
    elif 'azureAD' in auth_provider:
      auth_method = provision_azuread_config(auth_provider, msg)
      member_config.authMethods.append(auth_method)
      found_auth_method = True
    # Unsupported configuration found.
    else:
      status_msg = ('Authentication method [{}] is not supported, '
                    'skipping to the next.').format(auth_provider['name'])
      log.status.Print(status_msg)
  if not found_auth_method:
    raise exceptions.Error(
        'No supported authentication method is present in the provided config.')
  return member_config


def validate_clientconfig_meta(clientconfig):
  """Validate the basics of the parsed clientconfig yaml for AIS Hub Feature Spec.

  Args:
    clientconfig: The data field of the YamlConfigFile.
  """

  if 'spec' not in clientconfig:
    raise exceptions.Error('Missing required field .spec')


def provision_oidc_config(auth_method, msg):
  """Provision FeatureSpec OIDCConfig from the parsed yaml file.

  Args:
    auth_method: YamlConfigFile, The data loaded from the yaml file given by the
      user. YamlConfigFile is from
      googlecloudsdk.command_lib.anthos.common.file_parsers.
    msg: The gkehub messages package.

  Returns:
    member_config: A MemberConfig configuration containing a single
      OIDC auth method for the IdentityServiceFeatureSpec.
  """
  auth_method_proto = msg.IdentityServiceAuthMethod()
  auth_method_proto.name = auth_method['name']
  oidc_config = auth_method['oidc']

  # Required Fields.
  if 'issuerURI' not in oidc_config or 'clientID' not in oidc_config:
    raise exceptions.Error(
        'input config file OIDC Config must contain issuerURI and clientID.')
  auth_method_proto.oidcConfig = msg.IdentityServiceOidcConfig()
  auth_method_proto.oidcConfig.issuerUri = oidc_config['issuerURI']
  auth_method_proto.oidcConfig.clientId = oidc_config['clientID']

  validate_issuer_uri(auth_method_proto.oidcConfig.issuerUri,
                      auth_method['name'])

  # Optional Auth Method Fields.
  if 'proxy' in auth_method:
    auth_method_proto.proxy = auth_method['proxy']

  # Optional OIDC Config Fields.
  if 'certificateAuthorityData' in oidc_config:
    auth_method_proto.oidcConfig.certificateAuthorityData = oidc_config[
        'certificateAuthorityData']
  if 'deployCloudConsoleProxy' in oidc_config:
    auth_method_proto.oidcConfig.deployCloudConsoleProxy = oidc_config[
        'deployCloudConsoleProxy']
  if 'extraParams' in oidc_config:
    auth_method_proto.oidcConfig.extraParams = oidc_config['extraParams']
  if 'groupPrefix' in oidc_config:
    auth_method_proto.oidcConfig.groupPrefix = oidc_config['groupPrefix']
  if 'groupsClaim' in oidc_config:
    auth_method_proto.oidcConfig.groupsClaim = oidc_config['groupsClaim']

  # If groupClaim is empty, then groupPrefix should be empty
  if (not auth_method_proto.oidcConfig.groupsClaim and
      auth_method_proto.oidcConfig.groupPrefix):
    raise exceptions.Error(
        'groupPrefix should be empty for method [{}] because groupsClaim is empty.'
        .format(auth_method['name']))

  if 'kubectlRedirectURI' in oidc_config:
    auth_method_proto.oidcConfig.kubectlRedirectUri = oidc_config[
        'kubectlRedirectURI']
  if 'scopes' in oidc_config:
    auth_method_proto.oidcConfig.scopes = oidc_config['scopes']
  if 'userClaim' in oidc_config:
    auth_method_proto.oidcConfig.userClaim = oidc_config['userClaim']
  if 'userPrefix' in oidc_config:
    auth_method_proto.oidcConfig.userPrefix = oidc_config['userPrefix']
  if 'clientSecret' in oidc_config:
    auth_method_proto.oidcConfig.clientSecret = oidc_config['clientSecret']
  if 'enableAccessToken' in oidc_config:
    auth_method_proto.oidcConfig.enableAccessToken = oidc_config[
        'enableAccessToken']
  return auth_method_proto


def provision_google_config(auth_method, msg):
  """Provision FeatureSpec GoogleConfig from the parsed configuration file.

  Args:
    auth_method: YamlConfigFile, The data loaded from the yaml file given by the
      user. YamlConfigFile is from
      googlecloudsdk.command_lib.anthos.common.file_parsers.
    msg: The gkehub messages package.

  Returns:
    member_config: A MemberConfig configuration containing a single Google
    auth method for the IdentityServiceFeatureSpec.
  """
  auth_method_proto = msg.IdentityServiceAuthMethod()
  auth_method_proto.name = auth_method['name']
  google_config = auth_method['google']

  auth_method_proto.googleConfig = msg.IdentityServiceGoogleConfig()

  # Optional Auth Method Fields.
  if 'proxy' in auth_method:
    auth_method_proto.proxy = auth_method['proxy']

  # Required Google Config Fields.
  if 'disable' not in google_config:
    raise exceptions.Error(
        'The "disable" field is not set for the authentication method "{}"'
        .format(auth_method['name']))
  auth_method_proto.googleConfig.disable = google_config['disable']
  return auth_method_proto


def provision_azuread_config(auth_method, msg):
  """Provision FeatureSpec AzureADConfig from the parsed yaml file.

  Args:
    auth_method: YamlConfigFile, The data loaded from the yaml file given by the
      user. YamlConfigFile is from
      googlecloudsdk.command_lib.anthos.common.file_parsers.
    msg: The gkehub messages package.

  Returns:
    member_config: A MemberConfig configuration containing a single
    Azure AD auth method for the IdentityServiceFeatureSpec.
  """
  auth_method_proto = msg.IdentityServiceAuthMethod()
  auth_method_proto.name = auth_method['name']
  auth_method_proto.azureadConfig = msg.IdentityServiceAzureADConfig()
  # Optional Auth Method Fields.
  if 'proxy' in auth_method:
    auth_method_proto.proxy = auth_method['proxy']

  azuread_config = auth_method['azureAD']

  # Required AzureAD Config fields.
  if ('clientID' not in azuread_config or
      'kubectlRedirectURI' not in azuread_config or
      'tenant' not in azuread_config):
    err_msg = ('Authentication method [{}] must contain '
               'clientID, kubectlRedirectURI, and tenant.').format(
                   auth_method['name'])
    raise exceptions.Error(err_msg)
  auth_method_proto.azureadConfig.clientId = azuread_config['clientID']
  auth_method_proto.azureadConfig.kubectlRedirectUri = azuread_config[
      'kubectlRedirectURI']
  auth_method_proto.azureadConfig.tenant = azuread_config['tenant']

  # Optional AzureAD Config fields.
  if 'clientSecret' in azuread_config:
    auth_method_proto.azureadConfig.clientSecret = azuread_config[
        'clientSecret']
  return auth_method_proto


def validate_issuer_uri(issuer_uri, auth_method_name):
  """Validates Issuer URI field of OIDC config.

  Args:
    issuer_uri: issuer uri to be validated
    auth_method_name: auth method name that has this field
  """
  url = urllib3.util.parse_url(issuer_uri)
  if url.scheme != 'https':
    raise exceptions.Error(
        'issuerURI is invalid for method [{}]. Scheme is not https.'.format(
            auth_method_name))
  if url.path is not None and '.well-known/openid-configuration' in url.path:
    raise exceptions.Error(
        'issuerURI is invalid for method [{}]. issuerURI should not contain [{}].'
        .format(auth_method_name, '.well-known/openid-configuration'))
