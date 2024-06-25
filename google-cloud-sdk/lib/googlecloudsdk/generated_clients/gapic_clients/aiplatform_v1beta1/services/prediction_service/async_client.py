# -*- coding: utf-8 -*-
# Copyright 2023 Google LLC
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
from collections import OrderedDict
import functools
import re
from typing import Dict, Mapping, MutableMapping, MutableSequence, Optional, AsyncIterable, Awaitable, AsyncIterator, Sequence, Tuple, Type, Union

from googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1 import gapic_version as package_version

from google.api_core.client_options import ClientOptions
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials   # type: ignore
from google.oauth2 import service_account              # type: ignore

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object]  # type: ignore

from google.api import httpbody_pb2  # type: ignore
from cloudsdk.google.protobuf import any_pb2  # type: ignore
from cloudsdk.google.protobuf import struct_pb2  # type: ignore
from googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types import content
from googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types import explanation
from googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types import prediction_service
from googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types import types
from .transports.base import PredictionServiceTransport, DEFAULT_CLIENT_INFO
from .transports.grpc_asyncio import PredictionServiceGrpcAsyncIOTransport
from .client import PredictionServiceClient


class PredictionServiceAsyncClient:
    """A service for online predictions and explanations."""

    _client: PredictionServiceClient

    DEFAULT_ENDPOINT = PredictionServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = PredictionServiceClient.DEFAULT_MTLS_ENDPOINT

    common_billing_account_path = staticmethod(PredictionServiceClient.common_billing_account_path)
    parse_common_billing_account_path = staticmethod(PredictionServiceClient.parse_common_billing_account_path)
    common_folder_path = staticmethod(PredictionServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(PredictionServiceClient.parse_common_folder_path)
    common_organization_path = staticmethod(PredictionServiceClient.common_organization_path)
    parse_common_organization_path = staticmethod(PredictionServiceClient.parse_common_organization_path)
    common_project_path = staticmethod(PredictionServiceClient.common_project_path)
    parse_common_project_path = staticmethod(PredictionServiceClient.parse_common_project_path)
    common_location_path = staticmethod(PredictionServiceClient.common_location_path)
    parse_common_location_path = staticmethod(PredictionServiceClient.parse_common_location_path)

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            PredictionServiceAsyncClient: The constructed client.
        """
        return PredictionServiceClient.from_service_account_info.__func__(PredictionServiceAsyncClient, info, *args, **kwargs)  # type: ignore

    @classmethod
    def from_service_account_file(cls, filename: str, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            file.

        Args:
            filename (str): The path to the service account private key json
                file.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            PredictionServiceAsyncClient: The constructed client.
        """
        return PredictionServiceClient.from_service_account_file.__func__(PredictionServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

    from_service_account_json = from_service_account_file

    @classmethod
    def get_mtls_endpoint_and_cert_source(cls, client_options: Optional[ClientOptions] = None):
        """Return the API endpoint and client cert source for mutual TLS.

        The client cert source is determined in the following order:
        (1) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is not "true", the
        client cert source is None.
        (2) if `client_options.client_cert_source` is provided, use the provided one; if the
        default client cert source exists, use the default one; otherwise the client cert
        source is None.

        The API endpoint is determined in the following order:
        (1) if `client_options.api_endpoint` if provided, use the provided one.
        (2) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is "always", use the
        default mTLS endpoint; if the environment variable is "never", use the default API
        endpoint; otherwise if client cert source exists, use the default mTLS endpoint, otherwise
        use the default API endpoint.

        More details can be found at https://google.aip.dev/auth/4114.

        Args:
            client_options (google.api_core.client_options.ClientOptions): Custom options for the
                client. Only the `api_endpoint` and `client_cert_source` properties may be used
                in this method.

        Returns:
            Tuple[str, Callable[[], Tuple[bytes, bytes]]]: returns the API endpoint and the
                client cert source to use.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If any errors happen.
        """
        return PredictionServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> PredictionServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            PredictionServiceTransport: The transport used by the client instance.
        """
        return self._client.transport

    get_transport_class = functools.partial(type(PredictionServiceClient).get_transport_class, type(PredictionServiceClient))

    def __init__(self, *,
            credentials: Optional[ga_credentials.Credentials] = None,
            transport: Union[str, PredictionServiceTransport] = "grpc_asyncio",
            client_options: Optional[ClientOptions] = None,
            client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
            ) -> None:
        """Instantiates the prediction service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Union[str, ~.PredictionServiceTransport]): The
                transport to use. If set to None, a transport is chosen
                automatically.
            client_options (ClientOptions): Custom options for the client. It
                won't take effect if a ``transport`` instance is provided.
                (1) The ``api_endpoint`` property can be used to override the
                default endpoint provided by the client. GOOGLE_API_USE_MTLS_ENDPOINT
                environment variable can also be used to override the endpoint:
                "always" (always use the default mTLS endpoint), "never" (always
                use the default regular endpoint) and "auto" (auto switch to the
                default mTLS endpoint if client certificate is present, this is
                the default value). However, the ``api_endpoint`` property takes
                precedence if provided.
                (2) If GOOGLE_API_USE_CLIENT_CERTIFICATE environment variable
                is "true", then the ``client_cert_source`` property can be used
                to provide client certificate for mutual TLS transport. If
                not provided, the default SSL client certificate will be used if
                present. If GOOGLE_API_USE_CLIENT_CERTIFICATE is "false" or not
                set, no client certificate will be used.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client = PredictionServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,

        )

    async def predict(self,
            request: Optional[Union[prediction_service.PredictRequest, dict]] = None,
            *,
            endpoint: Optional[str] = None,
            instances: Optional[MutableSequence[struct_pb2.Value]] = None,
            parameters: Optional[struct_pb2.Value] = None,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> prediction_service.PredictResponse:
        r"""Perform an online prediction.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_predict():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                instances = aiplatform_v1beta1.Value()
                instances.null_value = "NULL_VALUE"

                request = aiplatform_v1beta1.PredictRequest(
                    endpoint="endpoint_value",
                    instances=instances,
                )

                # Make the request
                response = await client.predict(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.PredictRequest, dict]]):
                The request object. Request message for
                [PredictionService.Predict][google.cloud.aiplatform.v1beta1.PredictionService.Predict].
            endpoint (:class:`str`):
                Required. The name of the Endpoint requested to serve
                the prediction. Format:
                ``projects/{project}/locations/{location}/endpoints/{endpoint}``

                This corresponds to the ``endpoint`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            instances (:class:`MutableSequence[google.protobuf.struct_pb2.Value]`):
                Required. The instances that are the input to the
                prediction call. A DeployedModel may have an upper limit
                on the number of instances it supports per request, and
                when it is exceeded the prediction call errors in case
                of AutoML Models, or, in case of customer created
                Models, the behaviour is as documented by that Model.
                The schema of any single instance may be specified via
                Endpoint's DeployedModels'
                [Model's][google.cloud.aiplatform.v1beta1.DeployedModel.model]
                [PredictSchemata's][google.cloud.aiplatform.v1beta1.Model.predict_schemata]
                [instance_schema_uri][google.cloud.aiplatform.v1beta1.PredictSchemata.instance_schema_uri].

                This corresponds to the ``instances`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            parameters (:class:`google.protobuf.struct_pb2.Value`):
                The parameters that govern the prediction. The schema of
                the parameters may be specified via Endpoint's
                DeployedModels' [Model's
                ][google.cloud.aiplatform.v1beta1.DeployedModel.model]
                [PredictSchemata's][google.cloud.aiplatform.v1beta1.Model.predict_schemata]
                [parameters_schema_uri][google.cloud.aiplatform.v1beta1.PredictSchemata.parameters_schema_uri].

                This corresponds to the ``parameters`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.PredictResponse:
                Response message for
                   [PredictionService.Predict][google.cloud.aiplatform.v1beta1.PredictionService.Predict].

        """
        # Create or coerce a protobuf request object.
        # Quick check: If we got a request object, we should *not* have
        # gotten any keyword arguments that map to the request.
        has_flattened_params = any([endpoint, instances, parameters])
        if request is not None and has_flattened_params:
            raise ValueError("If the `request` argument is set, then none of "
                             "the individual field arguments should be set.")

        request = prediction_service.PredictRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if endpoint is not None:
            request.endpoint = endpoint
        if parameters is not None:
            request.parameters = parameters
        if instances:
            request.instances.extend(instances)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.predict,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((
                ("endpoint", request.endpoint),
            )),
        )

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def raw_predict(self,
            request: Optional[Union[prediction_service.RawPredictRequest, dict]] = None,
            *,
            endpoint: Optional[str] = None,
            http_body: Optional[httpbody_pb2.HttpBody] = None,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> httpbody_pb2.HttpBody:
        r"""Perform an online prediction with an arbitrary HTTP payload.

        The response includes the following HTTP headers:

        -  ``X-Vertex-AI-Endpoint-Id``: ID of the
           [Endpoint][google.cloud.aiplatform.v1beta1.Endpoint] that
           served this prediction.

        -  ``X-Vertex-AI-Deployed-Model-Id``: ID of the Endpoint's
           [DeployedModel][google.cloud.aiplatform.v1beta1.DeployedModel]
           that served this prediction.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_raw_predict():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                request = aiplatform_v1beta1.RawPredictRequest(
                    endpoint="endpoint_value",
                )

                # Make the request
                response = await client.raw_predict(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.RawPredictRequest, dict]]):
                The request object. Request message for
                [PredictionService.RawPredict][google.cloud.aiplatform.v1beta1.PredictionService.RawPredict].
            endpoint (:class:`str`):
                Required. The name of the Endpoint requested to serve
                the prediction. Format:
                ``projects/{project}/locations/{location}/endpoints/{endpoint}``

                This corresponds to the ``endpoint`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            http_body (:class:`google.api.httpbody_pb2.HttpBody`):
                The prediction input. Supports HTTP headers and
                arbitrary data payload.

                A
                [DeployedModel][google.cloud.aiplatform.v1beta1.DeployedModel]
                may have an upper limit on the number of instances it
                supports per request. When this limit it is exceeded for
                an AutoML model, the
                [RawPredict][google.cloud.aiplatform.v1beta1.PredictionService.RawPredict]
                method returns an error. When this limit is exceeded for
                a custom-trained model, the behavior varies depending on
                the model.

                You can specify the schema for each instance in the
                [predict_schemata.instance_schema_uri][google.cloud.aiplatform.v1beta1.PredictSchemata.instance_schema_uri]
                field when you create a
                [Model][google.cloud.aiplatform.v1beta1.Model]. This
                schema applies when you deploy the ``Model`` as a
                ``DeployedModel`` to an
                [Endpoint][google.cloud.aiplatform.v1beta1.Endpoint] and
                use the ``RawPredict`` method.

                This corresponds to the ``http_body`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.api.httpbody_pb2.HttpBody:
                Message that represents an arbitrary HTTP body. It should only be used for
                   payload formats that can't be represented as JSON,
                   such as raw binary or an HTML page.

                   This message can be used both in streaming and
                   non-streaming API methods in the request as well as
                   the response.

                   It can be used as a top-level request field, which is
                   convenient if one wants to extract parameters from
                   either the URL or HTTP template into the request
                   fields and also want access to the raw HTTP body.

                   Example:

                      message GetResourceRequest {
                         // A unique request id. string request_id = 1;

                         // The raw HTTP body is bound to this field.
                         google.api.HttpBody http_body = 2;

                      }

                      service ResourceService {
                         rpc GetResource(GetResourceRequest) returns
                         (google.api.HttpBody); rpc
                         UpdateResource(google.api.HttpBody) returns
                         (google.protobuf.Empty);

                      }

                   Example with streaming methods:

                      service CaldavService {
                         rpc GetCalendar(stream google.api.HttpBody)
                            returns (stream google.api.HttpBody);

                         rpc UpdateCalendar(stream google.api.HttpBody)
                            returns (stream google.api.HttpBody);

                      }

                   Use of this type only changes how the request and
                   response bodies are handled, all other features will
                   continue to work unchanged.

        """
        # Create or coerce a protobuf request object.
        # Quick check: If we got a request object, we should *not* have
        # gotten any keyword arguments that map to the request.
        has_flattened_params = any([endpoint, http_body])
        if request is not None and has_flattened_params:
            raise ValueError("If the `request` argument is set, then none of "
                             "the individual field arguments should be set.")

        request = prediction_service.RawPredictRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if endpoint is not None:
            request.endpoint = endpoint
        if http_body is not None:
            request.http_body = http_body

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.raw_predict,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((
                ("endpoint", request.endpoint),
            )),
        )

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def stream_raw_predict(self,
            request: Optional[Union[prediction_service.StreamRawPredictRequest, dict]] = None,
            *,
            endpoint: Optional[str] = None,
            http_body: Optional[httpbody_pb2.HttpBody] = None,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> Awaitable[AsyncIterable[httpbody_pb2.HttpBody]]:
        r"""Perform a streaming online prediction with an
        arbitrary HTTP payload.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_stream_raw_predict():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                request = aiplatform_v1beta1.StreamRawPredictRequest(
                    endpoint="endpoint_value",
                )

                # Make the request
                stream = await client.stream_raw_predict(request=request)

                # Handle the response
                async for response in stream:
                    print(response)

        Args:
            request (Optional[Union[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.StreamRawPredictRequest, dict]]):
                The request object. Request message for
                [PredictionService.StreamRawPredict][google.cloud.aiplatform.v1beta1.PredictionService.StreamRawPredict].
            endpoint (:class:`str`):
                Required. The name of the Endpoint requested to serve
                the prediction. Format:
                ``projects/{project}/locations/{location}/endpoints/{endpoint}``

                This corresponds to the ``endpoint`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            http_body (:class:`google.api.httpbody_pb2.HttpBody`):
                The prediction input. Supports HTTP
                headers and arbitrary data payload.

                This corresponds to the ``http_body`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            AsyncIterable[google.api.httpbody_pb2.HttpBody]:
                Message that represents an arbitrary HTTP body. It should only be used for
                   payload formats that can't be represented as JSON,
                   such as raw binary or an HTML page.

                   This message can be used both in streaming and
                   non-streaming API methods in the request as well as
                   the response.

                   It can be used as a top-level request field, which is
                   convenient if one wants to extract parameters from
                   either the URL or HTTP template into the request
                   fields and also want access to the raw HTTP body.

                   Example:

                      message GetResourceRequest {
                         // A unique request id. string request_id = 1;

                         // The raw HTTP body is bound to this field.
                         google.api.HttpBody http_body = 2;

                      }

                      service ResourceService {
                         rpc GetResource(GetResourceRequest) returns
                         (google.api.HttpBody); rpc
                         UpdateResource(google.api.HttpBody) returns
                         (google.protobuf.Empty);

                      }

                   Example with streaming methods:

                      service CaldavService {
                         rpc GetCalendar(stream google.api.HttpBody)
                            returns (stream google.api.HttpBody);

                         rpc UpdateCalendar(stream google.api.HttpBody)
                            returns (stream google.api.HttpBody);

                      }

                   Use of this type only changes how the request and
                   response bodies are handled, all other features will
                   continue to work unchanged.

        """
        # Create or coerce a protobuf request object.
        # Quick check: If we got a request object, we should *not* have
        # gotten any keyword arguments that map to the request.
        has_flattened_params = any([endpoint, http_body])
        if request is not None and has_flattened_params:
            raise ValueError("If the `request` argument is set, then none of "
                             "the individual field arguments should be set.")

        request = prediction_service.StreamRawPredictRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if endpoint is not None:
            request.endpoint = endpoint
        if http_body is not None:
            request.http_body = http_body

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.stream_raw_predict,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((
                ("endpoint", request.endpoint),
            )),
        )

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def direct_predict(self,
            request: Optional[Union[prediction_service.DirectPredictRequest, dict]] = None,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> prediction_service.DirectPredictResponse:
        r"""Perform an unary online prediction request to a gRPC
        model server for Vertex first-party products and
        frameworks.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_direct_predict():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                request = aiplatform_v1beta1.DirectPredictRequest(
                    endpoint="endpoint_value",
                )

                # Make the request
                response = await client.direct_predict(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.DirectPredictRequest, dict]]):
                The request object. Request message for
                [PredictionService.DirectPredict][google.cloud.aiplatform.v1beta1.PredictionService.DirectPredict].
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.DirectPredictResponse:
                Response message for
                   [PredictionService.DirectPredict][google.cloud.aiplatform.v1beta1.PredictionService.DirectPredict].

        """
        # Create or coerce a protobuf request object.
        request = prediction_service.DirectPredictRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.direct_predict,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((
                ("endpoint", request.endpoint),
            )),
        )

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def direct_raw_predict(self,
            request: Optional[Union[prediction_service.DirectRawPredictRequest, dict]] = None,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> prediction_service.DirectRawPredictResponse:
        r"""Perform an unary online prediction request to a gRPC
        model server for custom containers.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_direct_raw_predict():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                request = aiplatform_v1beta1.DirectRawPredictRequest(
                    endpoint="endpoint_value",
                )

                # Make the request
                response = await client.direct_raw_predict(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.DirectRawPredictRequest, dict]]):
                The request object. Request message for
                [PredictionService.DirectRawPredict][google.cloud.aiplatform.v1beta1.PredictionService.DirectRawPredict].
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.DirectRawPredictResponse:
                Response message for
                   [PredictionService.DirectRawPredict][google.cloud.aiplatform.v1beta1.PredictionService.DirectRawPredict].

        """
        # Create or coerce a protobuf request object.
        request = prediction_service.DirectRawPredictRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.direct_raw_predict,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((
                ("endpoint", request.endpoint),
            )),
        )

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def stream_direct_predict(self,
            requests: Optional[AsyncIterator[prediction_service.StreamDirectPredictRequest]] = None,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> Awaitable[AsyncIterable[prediction_service.StreamDirectPredictResponse]]:
        r"""Perform a streaming online prediction request to a
        gRPC model server for Vertex first-party products and
        frameworks.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_stream_direct_predict():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                request = aiplatform_v1beta1.StreamDirectPredictRequest(
                    endpoint="endpoint_value",
                )

                # This method expects an iterator which contains
                # 'aiplatform_v1beta1.StreamDirectPredictRequest' objects
                # Here we create a generator that yields a single `request` for
                # demonstrative purposes.
                requests = [request]

                def request_generator():
                    for request in requests:
                        yield request

                # Make the request
                stream = await client.stream_direct_predict(requests=request_generator())

                # Handle the response
                async for response in stream:
                    print(response)

        Args:
            requests (AsyncIterator[`googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.StreamDirectPredictRequest`]):
                The request object AsyncIterator. Request message for
                [PredictionService.StreamDirectPredict][google.cloud.aiplatform.v1beta1.PredictionService.StreamDirectPredict].

                The first message must contain
                [endpoint][google.cloud.aiplatform.v1beta1.StreamDirectPredictRequest.endpoint]
                field and optionally [input][]. The subsequent messages
                must contain [input][].
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            AsyncIterable[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.StreamDirectPredictResponse]:
                Response message for
                   [PredictionService.StreamDirectPredict][google.cloud.aiplatform.v1beta1.PredictionService.StreamDirectPredict].

        """

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.stream_direct_predict,
            default_timeout=5.0,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Send the request.
        response = rpc(
            requests,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def stream_direct_raw_predict(self,
            requests: Optional[AsyncIterator[prediction_service.StreamDirectRawPredictRequest]] = None,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> Awaitable[AsyncIterable[prediction_service.StreamDirectRawPredictResponse]]:
        r"""Perform a streaming online prediction request to a
        gRPC model server for custom containers.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_stream_direct_raw_predict():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                request = aiplatform_v1beta1.StreamDirectRawPredictRequest(
                    endpoint="endpoint_value",
                )

                # This method expects an iterator which contains
                # 'aiplatform_v1beta1.StreamDirectRawPredictRequest' objects
                # Here we create a generator that yields a single `request` for
                # demonstrative purposes.
                requests = [request]

                def request_generator():
                    for request in requests:
                        yield request

                # Make the request
                stream = await client.stream_direct_raw_predict(requests=request_generator())

                # Handle the response
                async for response in stream:
                    print(response)

        Args:
            requests (AsyncIterator[`googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.StreamDirectRawPredictRequest`]):
                The request object AsyncIterator. Request message for
                [PredictionService.StreamDirectRawPredict][google.cloud.aiplatform.v1beta1.PredictionService.StreamDirectRawPredict].

                The first message must contain
                [endpoint][google.cloud.aiplatform.v1beta1.StreamDirectRawPredictRequest.endpoint]
                and
                [method_name][google.cloud.aiplatform.v1beta1.StreamDirectRawPredictRequest.method_name]
                fields and optionally
                [input][google.cloud.aiplatform.v1beta1.StreamDirectRawPredictRequest.input].
                The subsequent messages must contain
                [input][google.cloud.aiplatform.v1beta1.StreamDirectRawPredictRequest.input].
                [method_name][google.cloud.aiplatform.v1beta1.StreamDirectRawPredictRequest.method_name]
                in the subsequent messages have no effect.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            AsyncIterable[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.StreamDirectRawPredictResponse]:
                Response message for
                   [PredictionService.StreamDirectRawPredict][google.cloud.aiplatform.v1beta1.PredictionService.StreamDirectRawPredict].

        """

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.stream_direct_raw_predict,
            default_timeout=5.0,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Send the request.
        response = rpc(
            requests,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def streaming_predict(self,
            requests: Optional[AsyncIterator[prediction_service.StreamingPredictRequest]] = None,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> Awaitable[AsyncIterable[prediction_service.StreamingPredictResponse]]:
        r"""Perform a streaming online prediction request for
        Vertex first-party products and frameworks.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_streaming_predict():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                request = aiplatform_v1beta1.StreamingPredictRequest(
                    endpoint="endpoint_value",
                )

                # This method expects an iterator which contains
                # 'aiplatform_v1beta1.StreamingPredictRequest' objects
                # Here we create a generator that yields a single `request` for
                # demonstrative purposes.
                requests = [request]

                def request_generator():
                    for request in requests:
                        yield request

                # Make the request
                stream = await client.streaming_predict(requests=request_generator())

                # Handle the response
                async for response in stream:
                    print(response)

        Args:
            requests (AsyncIterator[`googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.StreamingPredictRequest`]):
                The request object AsyncIterator. Request message for
                [PredictionService.StreamingPredict][google.cloud.aiplatform.v1beta1.PredictionService.StreamingPredict].

                The first message must contain
                [endpoint][google.cloud.aiplatform.v1beta1.StreamingPredictRequest.endpoint]
                field and optionally [input][]. The subsequent messages
                must contain [input][].
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            AsyncIterable[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.StreamingPredictResponse]:
                Response message for
                   [PredictionService.StreamingPredict][google.cloud.aiplatform.v1beta1.PredictionService.StreamingPredict].

        """

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.streaming_predict,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Send the request.
        response = rpc(
            requests,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def server_streaming_predict(self,
            request: Optional[Union[prediction_service.StreamingPredictRequest, dict]] = None,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> Awaitable[AsyncIterable[prediction_service.StreamingPredictResponse]]:
        r"""Perform a server-side streaming online prediction
        request for Vertex LLM streaming.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_server_streaming_predict():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                request = aiplatform_v1beta1.StreamingPredictRequest(
                    endpoint="endpoint_value",
                )

                # Make the request
                stream = await client.server_streaming_predict(request=request)

                # Handle the response
                async for response in stream:
                    print(response)

        Args:
            request (Optional[Union[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.StreamingPredictRequest, dict]]):
                The request object. Request message for
                [PredictionService.StreamingPredict][google.cloud.aiplatform.v1beta1.PredictionService.StreamingPredict].

                The first message must contain
                [endpoint][google.cloud.aiplatform.v1beta1.StreamingPredictRequest.endpoint]
                field and optionally [input][]. The subsequent messages
                must contain [input][].
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            AsyncIterable[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.StreamingPredictResponse]:
                Response message for
                   [PredictionService.StreamingPredict][google.cloud.aiplatform.v1beta1.PredictionService.StreamingPredict].

        """
        # Create or coerce a protobuf request object.
        request = prediction_service.StreamingPredictRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.server_streaming_predict,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((
                ("endpoint", request.endpoint),
            )),
        )

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def streaming_raw_predict(self,
            requests: Optional[AsyncIterator[prediction_service.StreamingRawPredictRequest]] = None,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> Awaitable[AsyncIterable[prediction_service.StreamingRawPredictResponse]]:
        r"""Perform a streaming online prediction request through
        gRPC.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_streaming_raw_predict():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                request = aiplatform_v1beta1.StreamingRawPredictRequest(
                    endpoint="endpoint_value",
                )

                # This method expects an iterator which contains
                # 'aiplatform_v1beta1.StreamingRawPredictRequest' objects
                # Here we create a generator that yields a single `request` for
                # demonstrative purposes.
                requests = [request]

                def request_generator():
                    for request in requests:
                        yield request

                # Make the request
                stream = await client.streaming_raw_predict(requests=request_generator())

                # Handle the response
                async for response in stream:
                    print(response)

        Args:
            requests (AsyncIterator[`googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.StreamingRawPredictRequest`]):
                The request object AsyncIterator. Request message for
                [PredictionService.StreamingRawPredict][google.cloud.aiplatform.v1beta1.PredictionService.StreamingRawPredict].

                The first message must contain
                [endpoint][google.cloud.aiplatform.v1beta1.StreamingRawPredictRequest.endpoint]
                and
                [method_name][google.cloud.aiplatform.v1beta1.StreamingRawPredictRequest.method_name]
                fields and optionally
                [input][google.cloud.aiplatform.v1beta1.StreamingRawPredictRequest.input].
                The subsequent messages must contain
                [input][google.cloud.aiplatform.v1beta1.StreamingRawPredictRequest.input].
                [method_name][google.cloud.aiplatform.v1beta1.StreamingRawPredictRequest.method_name]
                in the subsequent messages have no effect.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            AsyncIterable[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.StreamingRawPredictResponse]:
                Response message for
                   [PredictionService.StreamingRawPredict][google.cloud.aiplatform.v1beta1.PredictionService.StreamingRawPredict].

        """

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.streaming_raw_predict,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Send the request.
        response = rpc(
            requests,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def explain(self,
            request: Optional[Union[prediction_service.ExplainRequest, dict]] = None,
            *,
            endpoint: Optional[str] = None,
            instances: Optional[MutableSequence[struct_pb2.Value]] = None,
            parameters: Optional[struct_pb2.Value] = None,
            deployed_model_id: Optional[str] = None,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> prediction_service.ExplainResponse:
        r"""Perform an online explanation.

        If
        [deployed_model_id][google.cloud.aiplatform.v1beta1.ExplainRequest.deployed_model_id]
        is specified, the corresponding DeployModel must have
        [explanation_spec][google.cloud.aiplatform.v1beta1.DeployedModel.explanation_spec]
        populated. If
        [deployed_model_id][google.cloud.aiplatform.v1beta1.ExplainRequest.deployed_model_id]
        is not specified, all DeployedModels must have
        [explanation_spec][google.cloud.aiplatform.v1beta1.DeployedModel.explanation_spec]
        populated.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_explain():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                instances = aiplatform_v1beta1.Value()
                instances.null_value = "NULL_VALUE"

                request = aiplatform_v1beta1.ExplainRequest(
                    endpoint="endpoint_value",
                    instances=instances,
                )

                # Make the request
                response = await client.explain(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.ExplainRequest, dict]]):
                The request object. Request message for
                [PredictionService.Explain][google.cloud.aiplatform.v1beta1.PredictionService.Explain].
            endpoint (:class:`str`):
                Required. The name of the Endpoint requested to serve
                the explanation. Format:
                ``projects/{project}/locations/{location}/endpoints/{endpoint}``

                This corresponds to the ``endpoint`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            instances (:class:`MutableSequence[google.protobuf.struct_pb2.Value]`):
                Required. The instances that are the input to the
                explanation call. A DeployedModel may have an upper
                limit on the number of instances it supports per
                request, and when it is exceeded the explanation call
                errors in case of AutoML Models, or, in case of customer
                created Models, the behaviour is as documented by that
                Model. The schema of any single instance may be
                specified via Endpoint's DeployedModels'
                [Model's][google.cloud.aiplatform.v1beta1.DeployedModel.model]
                [PredictSchemata's][google.cloud.aiplatform.v1beta1.Model.predict_schemata]
                [instance_schema_uri][google.cloud.aiplatform.v1beta1.PredictSchemata.instance_schema_uri].

                This corresponds to the ``instances`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            parameters (:class:`google.protobuf.struct_pb2.Value`):
                The parameters that govern the prediction. The schema of
                the parameters may be specified via Endpoint's
                DeployedModels' [Model's
                ][google.cloud.aiplatform.v1beta1.DeployedModel.model]
                [PredictSchemata's][google.cloud.aiplatform.v1beta1.Model.predict_schemata]
                [parameters_schema_uri][google.cloud.aiplatform.v1beta1.PredictSchemata.parameters_schema_uri].

                This corresponds to the ``parameters`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            deployed_model_id (:class:`str`):
                If specified, this ExplainRequest will be served by the
                chosen DeployedModel, overriding
                [Endpoint.traffic_split][google.cloud.aiplatform.v1beta1.Endpoint.traffic_split].

                This corresponds to the ``deployed_model_id`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.ExplainResponse:
                Response message for
                   [PredictionService.Explain][google.cloud.aiplatform.v1beta1.PredictionService.Explain].

        """
        # Create or coerce a protobuf request object.
        # Quick check: If we got a request object, we should *not* have
        # gotten any keyword arguments that map to the request.
        has_flattened_params = any([endpoint, instances, parameters, deployed_model_id])
        if request is not None and has_flattened_params:
            raise ValueError("If the `request` argument is set, then none of "
                             "the individual field arguments should be set.")

        request = prediction_service.ExplainRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if endpoint is not None:
            request.endpoint = endpoint
        if parameters is not None:
            request.parameters = parameters
        if deployed_model_id is not None:
            request.deployed_model_id = deployed_model_id
        if instances:
            request.instances.extend(instances)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.explain,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((
                ("endpoint", request.endpoint),
            )),
        )

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def count_tokens(self,
            request: Optional[Union[prediction_service.CountTokensRequest, dict]] = None,
            *,
            endpoint: Optional[str] = None,
            instances: Optional[MutableSequence[struct_pb2.Value]] = None,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> prediction_service.CountTokensResponse:
        r"""Perform a token counting.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_count_tokens():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                instances = aiplatform_v1beta1.Value()
                instances.null_value = "NULL_VALUE"

                contents = aiplatform_v1beta1.Content()
                contents.parts.text = "text_value"

                request = aiplatform_v1beta1.CountTokensRequest(
                    endpoint="endpoint_value",
                    model="model_value",
                    instances=instances,
                    contents=contents,
                )

                # Make the request
                response = await client.count_tokens(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.CountTokensRequest, dict]]):
                The request object. Request message for
                [PredictionService.CountTokens][google.cloud.aiplatform.v1beta1.PredictionService.CountTokens].
            endpoint (:class:`str`):
                Required. The name of the Endpoint requested to perform
                token counting. Format:
                ``projects/{project}/locations/{location}/endpoints/{endpoint}``

                This corresponds to the ``endpoint`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            instances (:class:`MutableSequence[google.protobuf.struct_pb2.Value]`):
                Required. The instances that are the
                input to token counting call. Schema is
                identical to the prediction schema of
                the underlying model.

                This corresponds to the ``instances`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.CountTokensResponse:
                Response message for
                   [PredictionService.CountTokens][google.cloud.aiplatform.v1beta1.PredictionService.CountTokens].

        """
        # Create or coerce a protobuf request object.
        # Quick check: If we got a request object, we should *not* have
        # gotten any keyword arguments that map to the request.
        has_flattened_params = any([endpoint, instances])
        if request is not None and has_flattened_params:
            raise ValueError("If the `request` argument is set, then none of "
                             "the individual field arguments should be set.")

        request = prediction_service.CountTokensRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if endpoint is not None:
            request.endpoint = endpoint
        if instances:
            request.instances.extend(instances)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.count_tokens,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((
                ("endpoint", request.endpoint),
            )),
        )

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def generate_content(self,
            request: Optional[Union[prediction_service.GenerateContentRequest, dict]] = None,
            *,
            model: Optional[str] = None,
            contents: Optional[MutableSequence[content.Content]] = None,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> prediction_service.GenerateContentResponse:
        r"""Generate content with multimodal inputs.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_generate_content():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                contents = aiplatform_v1beta1.Content()
                contents.parts.text = "text_value"

                request = aiplatform_v1beta1.GenerateContentRequest(
                    model="model_value",
                    contents=contents,
                )

                # Make the request
                response = await client.generate_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.GenerateContentRequest, dict]]):
                The request object. Request message for [PredictionService.GenerateContent].
            model (:class:`str`):
                Required. The name of the publisher model requested to
                serve the prediction. Format:
                ``projects/{project}/locations/{location}/publishers/*/models/*``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            contents (:class:`MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.Content]`):
                Required. The content of the current
                conversation with the model.
                For single-turn queries, this is a
                single instance. For multi-turn queries,
                this is a repeated field that contains
                conversation history + latest request.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.GenerateContentResponse:
                Response message for
                [PredictionService.GenerateContent].

        """
        # Create or coerce a protobuf request object.
        # Quick check: If we got a request object, we should *not* have
        # gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents])
        if request is not None and has_flattened_params:
            raise ValueError("If the `request` argument is set, then none of "
                             "the individual field arguments should be set.")

        request = prediction_service.GenerateContentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if contents:
            request.contents.extend(contents)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.generate_content,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((
                ("model", request.model),
            )),
        )

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def stream_generate_content(self,
            request: Optional[Union[prediction_service.GenerateContentRequest, dict]] = None,
            *,
            model: Optional[str] = None,
            contents: Optional[MutableSequence[content.Content]] = None,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> Awaitable[AsyncIterable[prediction_service.GenerateContentResponse]]:
        r"""Generate content with multimodal inputs with
        streaming support.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_stream_generate_content():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                contents = aiplatform_v1beta1.Content()
                contents.parts.text = "text_value"

                request = aiplatform_v1beta1.GenerateContentRequest(
                    model="model_value",
                    contents=contents,
                )

                # Make the request
                stream = await client.stream_generate_content(request=request)

                # Handle the response
                async for response in stream:
                    print(response)

        Args:
            request (Optional[Union[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.GenerateContentRequest, dict]]):
                The request object. Request message for [PredictionService.GenerateContent].
            model (:class:`str`):
                Required. The name of the publisher model requested to
                serve the prediction. Format:
                ``projects/{project}/locations/{location}/publishers/*/models/*``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            contents (:class:`MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.Content]`):
                Required. The content of the current
                conversation with the model.
                For single-turn queries, this is a
                single instance. For multi-turn queries,
                this is a repeated field that contains
                conversation history + latest request.

                This corresponds to the ``contents`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            AsyncIterable[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.GenerateContentResponse]:
                Response message for
                [PredictionService.GenerateContent].

        """
        # Create or coerce a protobuf request object.
        # Quick check: If we got a request object, we should *not* have
        # gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, contents])
        if request is not None and has_flattened_params:
            raise ValueError("If the `request` argument is set, then none of "
                             "the individual field arguments should be set.")

        request = prediction_service.GenerateContentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if contents:
            request.contents.extend(contents)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.stream_generate_content,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((
                ("model", request.model),
            )),
        )

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def chat_completions(self,
            request: Optional[Union[prediction_service.ChatCompletionsRequest, dict]] = None,
            *,
            endpoint: Optional[str] = None,
            http_body: Optional[httpbody_pb2.HttpBody] = None,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Union[float, object] = gapic_v1.method.DEFAULT,
            metadata: Sequence[Tuple[str, str]] = (),
            ) -> Awaitable[AsyncIterable[httpbody_pb2.HttpBody]]:
        r"""Exposes an OpenAI-compatible endpoint for chat
        completions.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from googlecloudsdk.generated_clients.gapic_clients import aiplatform_v1beta1

            async def sample_chat_completions():
                # Create a client
                client = aiplatform_v1beta1.PredictionServiceAsyncClient()

                # Initialize request argument(s)
                request = aiplatform_v1beta1.ChatCompletionsRequest(
                    endpoint="endpoint_value",
                )

                # Make the request
                stream = await client.chat_completions(request=request)

                # Handle the response
                async for response in stream:
                    print(response)

        Args:
            request (Optional[Union[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.ChatCompletionsRequest, dict]]):
                The request object. Request message for [PredictionService.ChatCompletions]
            endpoint (:class:`str`):
                Required. The name of the Endpoint requested to serve
                the prediction. Format:
                ``projects/{project}/locations/{location}/endpoints/openapi``

                This corresponds to the ``endpoint`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            http_body (:class:`google.api.httpbody_pb2.HttpBody`):
                Optional. The prediction input.
                Supports HTTP headers and arbitrary data
                payload.

                This corresponds to the ``http_body`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            AsyncIterable[google.api.httpbody_pb2.HttpBody]:
                Message that represents an arbitrary HTTP body. It should only be used for
                   payload formats that can't be represented as JSON,
                   such as raw binary or an HTML page.

                   This message can be used both in streaming and
                   non-streaming API methods in the request as well as
                   the response.

                   It can be used as a top-level request field, which is
                   convenient if one wants to extract parameters from
                   either the URL or HTTP template into the request
                   fields and also want access to the raw HTTP body.

                   Example:

                      message GetResourceRequest {
                         // A unique request id. string request_id = 1;

                         // The raw HTTP body is bound to this field.
                         google.api.HttpBody http_body = 2;

                      }

                      service ResourceService {
                         rpc GetResource(GetResourceRequest) returns
                         (google.api.HttpBody); rpc
                         UpdateResource(google.api.HttpBody) returns
                         (google.protobuf.Empty);

                      }

                   Example with streaming methods:

                      service CaldavService {
                         rpc GetCalendar(stream google.api.HttpBody)
                            returns (stream google.api.HttpBody);

                         rpc UpdateCalendar(stream google.api.HttpBody)
                            returns (stream google.api.HttpBody);

                      }

                   Use of this type only changes how the request and
                   response bodies are handled, all other features will
                   continue to work unchanged.

        """
        # Create or coerce a protobuf request object.
        # Quick check: If we got a request object, we should *not* have
        # gotten any keyword arguments that map to the request.
        has_flattened_params = any([endpoint, http_body])
        if request is not None and has_flattened_params:
            raise ValueError("If the `request` argument is set, then none of "
                             "the individual field arguments should be set.")

        request = prediction_service.ChatCompletionsRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if endpoint is not None:
            request.endpoint = endpoint
        if http_body is not None:
            request.http_body = http_body

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.chat_completions,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((
                ("endpoint", request.endpoint),
            )),
        )

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def __aenter__(self) -> "PredictionServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(gapic_version=package_version.__version__)


__all__ = (
    "PredictionServiceAsyncClient",
)
