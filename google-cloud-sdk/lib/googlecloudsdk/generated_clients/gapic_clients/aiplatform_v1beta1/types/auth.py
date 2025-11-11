# -*- coding: utf-8 -*-
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import annotations

from typing import MutableMapping, MutableSequence

import proto  # type: ignore


__protobuf__ = proto.module(
    package='google.cloud.aiplatform.v1beta1',
    manifest={
        'HttpElementLocation',
        'AuthType',
        'AuthConfig',
    },
)


class HttpElementLocation(proto.Enum):
    r"""Enum of location an HTTP element can be.

    Values:
        HTTP_IN_UNSPECIFIED (0):
            No description available.
        HTTP_IN_QUERY (1):
            Element is in the HTTP request query.
        HTTP_IN_HEADER (2):
            Element is in the HTTP request header.
        HTTP_IN_PATH (3):
            Element is in the HTTP request path.
        HTTP_IN_BODY (4):
            Element is in the HTTP request body.
        HTTP_IN_COOKIE (5):
            Element is in the HTTP request cookie.
    """
    HTTP_IN_UNSPECIFIED = 0
    HTTP_IN_QUERY = 1
    HTTP_IN_HEADER = 2
    HTTP_IN_PATH = 3
    HTTP_IN_BODY = 4
    HTTP_IN_COOKIE = 5


class AuthType(proto.Enum):
    r"""Type of Auth.

    Values:
        AUTH_TYPE_UNSPECIFIED (0):
            No description available.
        NO_AUTH (1):
            No Auth.
        API_KEY_AUTH (2):
            API Key Auth.
        HTTP_BASIC_AUTH (3):
            HTTP Basic Auth.
        GOOGLE_SERVICE_ACCOUNT_AUTH (4):
            Google Service Account Auth.
        OAUTH (6):
            OAuth auth.
        OIDC_AUTH (8):
            OpenID Connect (OIDC) Auth.
    """
    AUTH_TYPE_UNSPECIFIED = 0
    NO_AUTH = 1
    API_KEY_AUTH = 2
    HTTP_BASIC_AUTH = 3
    GOOGLE_SERVICE_ACCOUNT_AUTH = 4
    OAUTH = 6
    OIDC_AUTH = 8


class AuthConfig(proto.Message):
    r"""Auth configuration to run the extension.

    This message has `oneof`_ fields (mutually exclusive fields).
    For each oneof, at most one member field can be set at the same time.
    Setting any member of the oneof automatically clears all other
    members.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        api_key_config (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.AuthConfig.ApiKeyConfig):
            Config for API key auth.

            This field is a member of `oneof`_ ``auth_config``.
        http_basic_auth_config (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.AuthConfig.HttpBasicAuthConfig):
            Config for HTTP Basic auth.

            This field is a member of `oneof`_ ``auth_config``.
        google_service_account_config (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.AuthConfig.GoogleServiceAccountConfig):
            Config for Google Service Account auth.

            This field is a member of `oneof`_ ``auth_config``.
        oauth_config (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.AuthConfig.OauthConfig):
            Config for user oauth.

            This field is a member of `oneof`_ ``auth_config``.
        oidc_config (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.AuthConfig.OidcConfig):
            Config for user OIDC auth.

            This field is a member of `oneof`_ ``auth_config``.
        auth_type (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.AuthType):
            Type of auth scheme.
    """

    class ApiKeyConfig(proto.Message):
        r"""Config for authentication with API key.

        Attributes:
            name (str):
                Optional. The parameter name of the API key. E.g. If the API
                request is "https://example.com/act?api_key=", "api_key"
                would be the parameter name.
            api_key_secret (str):
                Optional. The name of the SecretManager secret version
                resource storing the API key. Format:
                ``projects/{project}/secrets/{secrete}/versions/{version}``

                - If both ``api_key_secret`` and ``api_key_string`` are
                  specified, this field takes precedence over
                  ``api_key_string``.

                - If specified, the ``secretmanager.versions.access``
                  permission should be granted to Vertex AI Extension
                  Service Agent
                  (https://cloud.google.com/vertex-ai/docs/general/access-control#service-agents)
                  on the specified resource.
            api_key_string (str):
                Optional. The API key to be used in the
                request directly.
            http_element_location (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.HttpElementLocation):
                Optional. The location of the API key.
        """

        name: str = proto.Field(
            proto.STRING,
            number=1,
        )
        api_key_secret: str = proto.Field(
            proto.STRING,
            number=2,
        )
        api_key_string: str = proto.Field(
            proto.STRING,
            number=4,
        )
        http_element_location: 'HttpElementLocation' = proto.Field(
            proto.ENUM,
            number=3,
            enum='HttpElementLocation',
        )

    class HttpBasicAuthConfig(proto.Message):
        r"""Config for HTTP Basic Authentication.

        Attributes:
            credential_secret (str):
                Required. The name of the SecretManager secret version
                resource storing the base64 encoded credentials. Format:
                ``projects/{project}/secrets/{secrete}/versions/{version}``

                - If specified, the ``secretmanager.versions.access``
                  permission should be granted to Vertex AI Extension
                  Service Agent
                  (https://cloud.google.com/vertex-ai/docs/general/access-control#service-agents)
                  on the specified resource.
        """

        credential_secret: str = proto.Field(
            proto.STRING,
            number=2,
        )

    class GoogleServiceAccountConfig(proto.Message):
        r"""Config for Google Service Account Authentication.

        Attributes:
            service_account (str):
                Optional. The service account that the extension execution
                service runs as.

                - If the service account is specified, the
                  ``iam.serviceAccounts.getAccessToken`` permission should
                  be granted to Vertex AI Extension Service Agent
                  (https://cloud.google.com/vertex-ai/docs/general/access-control#service-agents)
                  on the specified service account.

                - If not specified, the Vertex AI Extension Service Agent
                  will be used to execute the Extension.
        """

        service_account: str = proto.Field(
            proto.STRING,
            number=1,
        )

    class OauthConfig(proto.Message):
        r"""Config for user oauth.

        This message has `oneof`_ fields (mutually exclusive fields).
        For each oneof, at most one member field can be set at the same time.
        Setting any member of the oneof automatically clears all other
        members.

        .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

        Attributes:
            access_token (str):
                Access token for extension endpoint. Only used to propagate
                token from [[ExecuteExtensionRequest.runtime_auth_config]]
                at request time.

                This field is a member of `oneof`_ ``oauth_config``.
            service_account (str):
                The service account used to generate access tokens for
                executing the Extension.

                - If the service account is specified, the
                  ``iam.serviceAccounts.getAccessToken`` permission should
                  be granted to Vertex AI Extension Service Agent
                  (https://cloud.google.com/vertex-ai/docs/general/access-control#service-agents)
                  on the provided service account.

                This field is a member of `oneof`_ ``oauth_config``.
        """

        access_token: str = proto.Field(
            proto.STRING,
            number=1,
            oneof='oauth_config',
        )
        service_account: str = proto.Field(
            proto.STRING,
            number=2,
            oneof='oauth_config',
        )

    class OidcConfig(proto.Message):
        r"""Config for user OIDC auth.

        This message has `oneof`_ fields (mutually exclusive fields).
        For each oneof, at most one member field can be set at the same time.
        Setting any member of the oneof automatically clears all other
        members.

        .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

        Attributes:
            id_token (str):
                OpenID Connect formatted ID token for extension endpoint.
                Only used to propagate token from
                [[ExecuteExtensionRequest.runtime_auth_config]] at request
                time.

                This field is a member of `oneof`_ ``oidc_config``.
            service_account (str):
                The service account used to generate an OpenID Connect
                (OIDC)-compatible JWT token signed by the Google OIDC
                Provider (accounts.google.com) for extension endpoint
                (https://cloud.google.com/iam/docs/create-short-lived-credentials-direct#sa-credentials-oidc).

                - The audience for the token will be set to the URL in the
                  server url defined in the OpenApi spec.

                - If the service account is provided, the service account
                  should grant ``iam.serviceAccounts.getOpenIdToken``
                  permission to Vertex AI Extension Service Agent
                  (https://cloud.google.com/vertex-ai/docs/general/access-control#service-agents).

                This field is a member of `oneof`_ ``oidc_config``.
        """

        id_token: str = proto.Field(
            proto.STRING,
            number=1,
            oneof='oidc_config',
        )
        service_account: str = proto.Field(
            proto.STRING,
            number=2,
            oneof='oidc_config',
        )

    api_key_config: ApiKeyConfig = proto.Field(
        proto.MESSAGE,
        number=2,
        oneof='auth_config',
        message=ApiKeyConfig,
    )
    http_basic_auth_config: HttpBasicAuthConfig = proto.Field(
        proto.MESSAGE,
        number=3,
        oneof='auth_config',
        message=HttpBasicAuthConfig,
    )
    google_service_account_config: GoogleServiceAccountConfig = proto.Field(
        proto.MESSAGE,
        number=4,
        oneof='auth_config',
        message=GoogleServiceAccountConfig,
    )
    oauth_config: OauthConfig = proto.Field(
        proto.MESSAGE,
        number=5,
        oneof='auth_config',
        message=OauthConfig,
    )
    oidc_config: OidcConfig = proto.Field(
        proto.MESSAGE,
        number=7,
        oneof='auth_config',
        message=OidcConfig,
    )
    auth_type: 'AuthType' = proto.Field(
        proto.ENUM,
        number=101,
        enum='AuthType',
    )


__all__ = tuple(sorted(__protobuf__.manifest))
