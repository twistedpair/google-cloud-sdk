# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
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

from google.auth.transport.requests import AuthorizedSession  # type: ignore
import json  # type: ignore
import grpc  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.api_core import exceptions as core_exceptions
from google.api_core import retry as retries
from google.api_core import rest_helpers
from google.api_core import rest_streaming
from google.api_core import path_template
from google.api_core import gapic_v1

from cloudsdk.google.protobuf import json_format
from requests import __version__ as requests_version
import dataclasses
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import warnings

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore


from google.api import httpbody_pb2  # type: ignore
from googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types import prediction_service
from google.longrunning import operations_pb2  # type: ignore

from .base import PredictionServiceTransport, DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class PredictionServiceRestInterceptor:
    """Interceptor for PredictionService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the PredictionServiceRestTransport.

    .. code-block:: python
        class MyCustomPredictionServiceInterceptor(PredictionServiceRestInterceptor):
            def pre_chat_completions(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_chat_completions(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_count_tokens(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_count_tokens(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_direct_predict(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_direct_predict(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_direct_raw_predict(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_direct_raw_predict(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_embed_content(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_embed_content(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_explain(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_explain(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_fetch_predict_operation(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_fetch_predict_operation(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_generate_content(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_generate_content(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_invoke(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_invoke(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_predict(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_predict(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_predict_long_running(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_predict_long_running(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_raw_predict(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_raw_predict(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_server_streaming_predict(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_server_streaming_predict(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_stream_generate_content(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_stream_generate_content(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_stream_raw_predict(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_stream_raw_predict(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = PredictionServiceRestTransport(interceptor=MyCustomPredictionServiceInterceptor())
        client = PredictionServiceClient(transport=transport)


    """
    def pre_chat_completions(self, request: prediction_service.ChatCompletionsRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.ChatCompletionsRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for chat_completions

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_chat_completions(self, response: rest_streaming.ResponseIterator) -> rest_streaming.ResponseIterator:
        """Post-rpc interceptor for chat_completions

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response
    def pre_count_tokens(self, request: prediction_service.CountTokensRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.CountTokensRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for count_tokens

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_count_tokens(self, response: prediction_service.CountTokensResponse) -> prediction_service.CountTokensResponse:
        """Post-rpc interceptor for count_tokens

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response
    def pre_direct_predict(self, request: prediction_service.DirectPredictRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.DirectPredictRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for direct_predict

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_direct_predict(self, response: prediction_service.DirectPredictResponse) -> prediction_service.DirectPredictResponse:
        """Post-rpc interceptor for direct_predict

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response
    def pre_direct_raw_predict(self, request: prediction_service.DirectRawPredictRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.DirectRawPredictRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for direct_raw_predict

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_direct_raw_predict(self, response: prediction_service.DirectRawPredictResponse) -> prediction_service.DirectRawPredictResponse:
        """Post-rpc interceptor for direct_raw_predict

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response
    def pre_embed_content(self, request: prediction_service.EmbedContentRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.EmbedContentRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for embed_content

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_embed_content(self, response: prediction_service.EmbedContentResponse) -> prediction_service.EmbedContentResponse:
        """Post-rpc interceptor for embed_content

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response
    def pre_explain(self, request: prediction_service.ExplainRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.ExplainRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for explain

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_explain(self, response: prediction_service.ExplainResponse) -> prediction_service.ExplainResponse:
        """Post-rpc interceptor for explain

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response
    def pre_fetch_predict_operation(self, request: prediction_service.FetchPredictOperationRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.FetchPredictOperationRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for fetch_predict_operation

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_fetch_predict_operation(self, response: operations_pb2.Operation) -> operations_pb2.Operation:
        """Post-rpc interceptor for fetch_predict_operation

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response
    def pre_generate_content(self, request: prediction_service.GenerateContentRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.GenerateContentRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for generate_content

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_generate_content(self, response: prediction_service.GenerateContentResponse) -> prediction_service.GenerateContentResponse:
        """Post-rpc interceptor for generate_content

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response
    def pre_invoke(self, request: prediction_service.InvokeRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.InvokeRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for invoke

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_invoke(self, response: rest_streaming.ResponseIterator) -> rest_streaming.ResponseIterator:
        """Post-rpc interceptor for invoke

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response
    def pre_predict(self, request: prediction_service.PredictRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.PredictRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for predict

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_predict(self, response: prediction_service.PredictResponse) -> prediction_service.PredictResponse:
        """Post-rpc interceptor for predict

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response
    def pre_predict_long_running(self, request: prediction_service.PredictLongRunningRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.PredictLongRunningRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for predict_long_running

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_predict_long_running(self, response: operations_pb2.Operation) -> operations_pb2.Operation:
        """Post-rpc interceptor for predict_long_running

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response
    def pre_raw_predict(self, request: prediction_service.RawPredictRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.RawPredictRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for raw_predict

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_raw_predict(self, response: httpbody_pb2.HttpBody) -> httpbody_pb2.HttpBody:
        """Post-rpc interceptor for raw_predict

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response
    def pre_server_streaming_predict(self, request: prediction_service.StreamingPredictRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.StreamingPredictRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for server_streaming_predict

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_server_streaming_predict(self, response: rest_streaming.ResponseIterator) -> rest_streaming.ResponseIterator:
        """Post-rpc interceptor for server_streaming_predict

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response
    def pre_stream_generate_content(self, request: prediction_service.GenerateContentRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.GenerateContentRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for stream_generate_content

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_stream_generate_content(self, response: rest_streaming.ResponseIterator) -> rest_streaming.ResponseIterator:
        """Post-rpc interceptor for stream_generate_content

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response
    def pre_stream_raw_predict(self, request: prediction_service.StreamRawPredictRequest, metadata: Sequence[Tuple[str, str]]) -> Tuple[prediction_service.StreamRawPredictRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for stream_raw_predict

        Override in a subclass to manipulate the request or metadata
        before they are sent to the PredictionService server.
        """
        return request, metadata

    def post_stream_raw_predict(self, response: rest_streaming.ResponseIterator) -> rest_streaming.ResponseIterator:
        """Post-rpc interceptor for stream_raw_predict

        Override in a subclass to manipulate the response
        after it is returned by the PredictionService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class PredictionServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: PredictionServiceRestInterceptor


class PredictionServiceRestTransport(PredictionServiceTransport):
    """REST backend transport for PredictionService.

    A service for online predictions and explanations.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1

    NOTE: This REST transport functionality is currently in a beta
    state (preview). We welcome your feedback via an issue in this
    library's source repository. Thank you!
    """

    def __init__(self, *,
            host: str = 'aiplatform.googleapis.com',
            credentials: Optional[ga_credentials.Credentials] = None,
            credentials_file: Optional[str] = None,
            scopes: Optional[Sequence[str]] = None,
            client_cert_source_for_mtls: Optional[Callable[[
                ], Tuple[bytes, bytes]]] = None,
            quota_project_id: Optional[str] = None,
            client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
            always_use_jwt_access: Optional[bool] = False,
            url_scheme: str = 'https',
            interceptor: Optional[PredictionServiceRestInterceptor] = None,
            api_audience: Optional[str] = None,
            ) -> None:
        """Instantiate the transport.

       NOTE: This REST transport functionality is currently in a beta
       state (preview). We welcome your feedback via a GitHub issue in
       this library's repository. Thank you!

        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'aiplatform.googleapis.com').
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.

            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if ``channel`` is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if ``channel`` is provided.
            client_cert_source_for_mtls (Callable[[], Tuple[bytes, bytes]]): Client
                certificate to configure mutual TLS HTTP channel. It is ignored
                if ``channel`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you are developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
            url_scheme: the protocol scheme for the API endpoint.  Normally
                "https", but for testing or local servers,
                "http" can be specified.
        """
        # Run the base constructor
        # TODO(yon-mg): resolve other ctor params i.e. scopes, quota, etc.
        # TODO: When custom host (api_endpoint) is set, `scopes` must *also* be set on the
        # credentials object
        maybe_url_match = re.match("^(?P<scheme>http(?:s)?://)?(?P<host>.*)$", host)
        if maybe_url_match is None:
            raise ValueError(f"Unexpected hostname structure: {host}")  # pragma: NO COVER

        url_match_items = maybe_url_match.groupdict()

        host = f"{url_scheme}://{host}" if not url_match_items["scheme"] else host

        super().__init__(
            host=host,
            credentials=credentials,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience
        )
        self._session = AuthorizedSession(
            self._credentials, default_host=self.DEFAULT_HOST)
        if client_cert_source_for_mtls:
            self._session.configure_mtls_channel(client_cert_source_for_mtls)
        self._interceptor = interceptor or PredictionServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _ChatCompletions(PredictionServiceRestStub):
        def __hash__(self):
            return hash("ChatCompletions")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.ChatCompletionsRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> rest_streaming.ResponseIterator:
            r"""Call the chat completions method over HTTP.

            Args:
                request (~.prediction_service.ChatCompletionsRequest):
                    The request object. Request message for [PredictionService.ChatCompletions]
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.httpbody_pb2.HttpBody:
                    Message that represents an arbitrary HTTP body. It
                should only be used for payload formats that can't be
                represented as JSON, such as raw binary or an HTML page.

                This message can be used both in streaming and
                non-streaming API methods in the request as well as the
                response.

                It can be used as a top-level request field, which is
                convenient if one wants to extract parameters from
                either the URL or HTTP template into the request fields
                and also want access to the raw HTTP body.

                Example:

                ::

                    message GetResourceRequest {
                      // A unique request id.
                      string request_id = 1;

                      // The raw HTTP body is bound to this field.
                      google.api.HttpBody http_body = 2;

                    }

                    service ResourceService {
                      rpc GetResource(GetResourceRequest)
                        returns (google.api.HttpBody);
                      rpc UpdateResource(google.api.HttpBody)
                        returns (google.protobuf.Empty);

                    }

                Example with streaming methods:

                ::

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

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}/chat/completions',
                'body': 'http_body',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=endpoints/*}/chat/completions',
                'body': 'http_body',
            },
            ]
            request, metadata = self._interceptor.pre_chat_completions(request, metadata)
            pb_request = prediction_service.ChatCompletionsRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = rest_streaming.ResponseIterator(response, httpbody_pb2.HttpBody)
            resp = self._interceptor.post_chat_completions(resp)
            return resp

    class _CountTokens(PredictionServiceRestStub):
        def __hash__(self):
            return hash("CountTokens")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.CountTokensRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> prediction_service.CountTokensResponse:
            r"""Call the count tokens method over HTTP.

            Args:
                request (~.prediction_service.CountTokensRequest):
                    The request object. Request message for
                [PredictionService.CountTokens][google.cloud.aiplatform.v1beta1.PredictionService.CountTokens].
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.prediction_service.CountTokensResponse:
                    Response message for
                [PredictionService.CountTokens][google.cloud.aiplatform.v1beta1.PredictionService.CountTokens].

            """

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}:countTokens',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/publishers/*/models/*}:countTokens',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=endpoints/*}:countTokens',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=publishers/*/models/*}:countTokens',
                'body': '*',
            },
            ]
            request, metadata = self._interceptor.pre_count_tokens(request, metadata)
            pb_request = prediction_service.CountTokensRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = prediction_service.CountTokensResponse()
            pb_resp = prediction_service.CountTokensResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_count_tokens(resp)
            return resp

    class _DirectPredict(PredictionServiceRestStub):
        def __hash__(self):
            return hash("DirectPredict")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.DirectPredictRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> prediction_service.DirectPredictResponse:
            r"""Call the direct predict method over HTTP.

            Args:
                request (~.prediction_service.DirectPredictRequest):
                    The request object. Request message for
                [PredictionService.DirectPredict][google.cloud.aiplatform.v1beta1.PredictionService.DirectPredict].
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.prediction_service.DirectPredictResponse:
                    Response message for
                [PredictionService.DirectPredict][google.cloud.aiplatform.v1beta1.PredictionService.DirectPredict].

            """

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}:directPredict',
                'body': '*',
            },
            ]
            request, metadata = self._interceptor.pre_direct_predict(request, metadata)
            pb_request = prediction_service.DirectPredictRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = prediction_service.DirectPredictResponse()
            pb_resp = prediction_service.DirectPredictResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_direct_predict(resp)
            return resp

    class _DirectRawPredict(PredictionServiceRestStub):
        def __hash__(self):
            return hash("DirectRawPredict")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.DirectRawPredictRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> prediction_service.DirectRawPredictResponse:
            r"""Call the direct raw predict method over HTTP.

            Args:
                request (~.prediction_service.DirectRawPredictRequest):
                    The request object. Request message for
                [PredictionService.DirectRawPredict][google.cloud.aiplatform.v1beta1.PredictionService.DirectRawPredict].
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.prediction_service.DirectRawPredictResponse:
                    Response message for
                [PredictionService.DirectRawPredict][google.cloud.aiplatform.v1beta1.PredictionService.DirectRawPredict].

            """

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}:directRawPredict',
                'body': '*',
            },
            ]
            request, metadata = self._interceptor.pre_direct_raw_predict(request, metadata)
            pb_request = prediction_service.DirectRawPredictRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = prediction_service.DirectRawPredictResponse()
            pb_resp = prediction_service.DirectRawPredictResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_direct_raw_predict(resp)
            return resp

    class _EmbedContent(PredictionServiceRestStub):
        def __hash__(self):
            return hash("EmbedContent")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.EmbedContentRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> prediction_service.EmbedContentResponse:
            r"""Call the embed content method over HTTP.

            Args:
                request (~.prediction_service.EmbedContentRequest):
                    The request object. Request message for
                [PredictionService.EmbedContent][google.cloud.aiplatform.v1beta1.PredictionService.EmbedContent].
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.prediction_service.EmbedContentResponse:
                    Response message for
                [PredictionService.EmbedContent][google.cloud.aiplatform.v1beta1.PredictionService.EmbedContent].

            """

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{model=projects/*/locations/*/publishers/*/models/*}:embedContent',
                'body': '*',
            },
            ]
            request, metadata = self._interceptor.pre_embed_content(request, metadata)
            pb_request = prediction_service.EmbedContentRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = prediction_service.EmbedContentResponse()
            pb_resp = prediction_service.EmbedContentResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_embed_content(resp)
            return resp

    class _Explain(PredictionServiceRestStub):
        def __hash__(self):
            return hash("Explain")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.ExplainRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> prediction_service.ExplainResponse:
            r"""Call the explain method over HTTP.

            Args:
                request (~.prediction_service.ExplainRequest):
                    The request object. Request message for
                [PredictionService.Explain][google.cloud.aiplatform.v1beta1.PredictionService.Explain].
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.prediction_service.ExplainResponse:
                    Response message for
                [PredictionService.Explain][google.cloud.aiplatform.v1beta1.PredictionService.Explain].

            """

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}:explain',
                'body': '*',
            },
            ]
            request, metadata = self._interceptor.pre_explain(request, metadata)
            pb_request = prediction_service.ExplainRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = prediction_service.ExplainResponse()
            pb_resp = prediction_service.ExplainResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_explain(resp)
            return resp

    class _FetchPredictOperation(PredictionServiceRestStub):
        def __hash__(self):
            return hash("FetchPredictOperation")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.FetchPredictOperationRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> operations_pb2.Operation:
            r"""Call the fetch predict operation method over HTTP.

            Args:
                request (~.prediction_service.FetchPredictOperationRequest):
                    The request object. Request message for
                [PredictionService.FetchPredictOperation][google.cloud.aiplatform.v1beta1.PredictionService.FetchPredictOperation].
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.operations_pb2.Operation:
                    This resource represents a
                long-running operation that is the
                result of a network API call.

            """

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}:fetchPredictOperation',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/publishers/*/models/*}:fetchPredictOperation',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=endpoints/*}:fetchPredictOperation',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=publishers/*/models/*}:fetchPredictOperation',
                'body': '*',
            },
            ]
            request, metadata = self._interceptor.pre_fetch_predict_operation(request, metadata)
            pb_request = prediction_service.FetchPredictOperationRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = operations_pb2.Operation()
            pb_resp = resp

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_fetch_predict_operation(resp)
            return resp

    class _GenerateContent(PredictionServiceRestStub):
        def __hash__(self):
            return hash("GenerateContent")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.GenerateContentRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> prediction_service.GenerateContentResponse:
            r"""Call the generate content method over HTTP.

            Args:
                request (~.prediction_service.GenerateContentRequest):
                    The request object. Request message for [PredictionService.GenerateContent].
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.prediction_service.GenerateContentResponse:
                    Response message for
                [PredictionService.GenerateContent].

            """

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{model=projects/*/locations/*/endpoints/*}:generateContent',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{model=projects/*/locations/*/publishers/*/models/*}:generateContent',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{model=endpoints/*}:generateContent',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{model=publishers/*/models/*}:generateContent',
                'body': '*',
            },
            ]
            request, metadata = self._interceptor.pre_generate_content(request, metadata)
            pb_request = prediction_service.GenerateContentRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = prediction_service.GenerateContentResponse()
            pb_resp = prediction_service.GenerateContentResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_generate_content(resp)
            return resp

    class _Invoke(PredictionServiceRestStub):
        def __hash__(self):
            return hash("Invoke")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.InvokeRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> rest_streaming.ResponseIterator:
            r"""Call the invoke method over HTTP.

            Args:
                request (~.prediction_service.InvokeRequest):
                    The request object. Request message for
                [PredictionService.Invoke][google.cloud.aiplatform.v1beta1.PredictionService.Invoke].
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.httpbody_pb2.HttpBody:
                    Message that represents an arbitrary HTTP body. It
                should only be used for payload formats that can't be
                represented as JSON, such as raw binary or an HTML page.

                This message can be used both in streaming and
                non-streaming API methods in the request as well as the
                response.

                It can be used as a top-level request field, which is
                convenient if one wants to extract parameters from
                either the URL or HTTP template into the request fields
                and also want access to the raw HTTP body.

                Example:

                ::

                    message GetResourceRequest {
                      // A unique request id.
                      string request_id = 1;

                      // The raw HTTP body is bound to this field.
                      google.api.HttpBody http_body = 2;

                    }

                    service ResourceService {
                      rpc GetResource(GetResourceRequest)
                        returns (google.api.HttpBody);
                      rpc UpdateResource(google.api.HttpBody)
                        returns (google.protobuf.Empty);

                    }

                Example with streaming methods:

                ::

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

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}/invoke/**',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}/deployedModels/{deployed_model_id}/invoke/**',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/openapi}/embeddings',
                'body': 'http_body',
            },
            ]
            request, metadata = self._interceptor.pre_invoke(request, metadata)
            pb_request = prediction_service.InvokeRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = rest_streaming.ResponseIterator(response, httpbody_pb2.HttpBody)
            resp = self._interceptor.post_invoke(resp)
            return resp

    class _Predict(PredictionServiceRestStub):
        def __hash__(self):
            return hash("Predict")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.PredictRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> prediction_service.PredictResponse:
            r"""Call the predict method over HTTP.

            Args:
                request (~.prediction_service.PredictRequest):
                    The request object. Request message for
                [PredictionService.Predict][google.cloud.aiplatform.v1beta1.PredictionService.Predict].
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.prediction_service.PredictResponse:
                    Response message for
                [PredictionService.Predict][google.cloud.aiplatform.v1beta1.PredictionService.Predict].

            """

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}:predict',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/publishers/*/models/*}:predict',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=endpoints/*}:predict',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=publishers/*/models/*}:predict',
                'body': '*',
            },
            ]
            request, metadata = self._interceptor.pre_predict(request, metadata)
            pb_request = prediction_service.PredictRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = prediction_service.PredictResponse()
            pb_resp = prediction_service.PredictResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_predict(resp)
            return resp

    class _PredictLongRunning(PredictionServiceRestStub):
        def __hash__(self):
            return hash("PredictLongRunning")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.PredictLongRunningRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> operations_pb2.Operation:
            r"""Call the predict long running method over HTTP.

            Args:
                request (~.prediction_service.PredictLongRunningRequest):
                    The request object. Request message for
                [PredictionService.PredictLongRunning][google.cloud.aiplatform.v1beta1.PredictionService.PredictLongRunning].
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.operations_pb2.Operation:
                    This resource represents a
                long-running operation that is the
                result of a network API call.

            """

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}:predictLongRunning',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/publishers/*/models/*}:predictLongRunning',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=endpoints/*}:predictLongRunning',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=publishers/*/models/*}:predictLongRunning',
                'body': '*',
            },
            ]
            request, metadata = self._interceptor.pre_predict_long_running(request, metadata)
            pb_request = prediction_service.PredictLongRunningRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = operations_pb2.Operation()
            pb_resp = resp

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_predict_long_running(resp)
            return resp

    class _RawPredict(PredictionServiceRestStub):
        def __hash__(self):
            return hash("RawPredict")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.RawPredictRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> httpbody_pb2.HttpBody:
            r"""Call the raw predict method over HTTP.

            Args:
                request (~.prediction_service.RawPredictRequest):
                    The request object. Request message for
                [PredictionService.RawPredict][google.cloud.aiplatform.v1beta1.PredictionService.RawPredict].
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.httpbody_pb2.HttpBody:
                    Message that represents an arbitrary HTTP body. It
                should only be used for payload formats that can't be
                represented as JSON, such as raw binary or an HTML page.

                This message can be used both in streaming and
                non-streaming API methods in the request as well as the
                response.

                It can be used as a top-level request field, which is
                convenient if one wants to extract parameters from
                either the URL or HTTP template into the request fields
                and also want access to the raw HTTP body.

                Example:

                ::

                    message GetResourceRequest {
                      // A unique request id.
                      string request_id = 1;

                      // The raw HTTP body is bound to this field.
                      google.api.HttpBody http_body = 2;

                    }

                    service ResourceService {
                      rpc GetResource(GetResourceRequest)
                        returns (google.api.HttpBody);
                      rpc UpdateResource(google.api.HttpBody)
                        returns (google.protobuf.Empty);

                    }

                Example with streaming methods:

                ::

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

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}:rawPredict',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/publishers/*/models/*}:rawPredict',
                'body': '*',
            },
            ]
            request, metadata = self._interceptor.pre_raw_predict(request, metadata)
            pb_request = prediction_service.RawPredictRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = httpbody_pb2.HttpBody()
            pb_resp = resp

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_raw_predict(resp)
            return resp

    class _ServerStreamingPredict(PredictionServiceRestStub):
        def __hash__(self):
            return hash("ServerStreamingPredict")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.StreamingPredictRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> rest_streaming.ResponseIterator:
            r"""Call the server streaming predict method over HTTP.

            Args:
                request (~.prediction_service.StreamingPredictRequest):
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
                ~.prediction_service.StreamingPredictResponse:
                    Response message for
                [PredictionService.StreamingPredict][google.cloud.aiplatform.v1beta1.PredictionService.StreamingPredict].

            """

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}:serverStreamingPredict',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/publishers/*/models/*}:serverStreamingPredict',
                'body': '*',
            },
            ]
            request, metadata = self._interceptor.pre_server_streaming_predict(request, metadata)
            pb_request = prediction_service.StreamingPredictRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = rest_streaming.ResponseIterator(response, prediction_service.StreamingPredictResponse)
            resp = self._interceptor.post_server_streaming_predict(resp)
            return resp

    class _StreamDirectPredict(PredictionServiceRestStub):
        def __hash__(self):
            return hash("StreamDirectPredict")

        def __call__(self,
                request: prediction_service.StreamDirectPredictRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> rest_streaming.ResponseIterator:
            raise NotImplementedError(
                "Method StreamDirectPredict is not available over REST transport"
            )
    class _StreamDirectRawPredict(PredictionServiceRestStub):
        def __hash__(self):
            return hash("StreamDirectRawPredict")

        def __call__(self,
                request: prediction_service.StreamDirectRawPredictRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> rest_streaming.ResponseIterator:
            raise NotImplementedError(
                "Method StreamDirectRawPredict is not available over REST transport"
            )
    class _StreamGenerateContent(PredictionServiceRestStub):
        def __hash__(self):
            return hash("StreamGenerateContent")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.GenerateContentRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> rest_streaming.ResponseIterator:
            r"""Call the stream generate content method over HTTP.

            Args:
                request (~.prediction_service.GenerateContentRequest):
                    The request object. Request message for [PredictionService.GenerateContent].
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.prediction_service.GenerateContentResponse:
                    Response message for
                [PredictionService.GenerateContent].

            """

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{model=projects/*/locations/*/endpoints/*}:streamGenerateContent',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{model=projects/*/locations/*/publishers/*/models/*}:streamGenerateContent',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{model=endpoints/*}:streamGenerateContent',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{model=publishers/*/models/*}:streamGenerateContent',
                'body': '*',
            },
            ]
            request, metadata = self._interceptor.pre_stream_generate_content(request, metadata)
            pb_request = prediction_service.GenerateContentRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = rest_streaming.ResponseIterator(response, prediction_service.GenerateContentResponse)
            resp = self._interceptor.post_stream_generate_content(resp)
            return resp

    class _StreamingPredict(PredictionServiceRestStub):
        def __hash__(self):
            return hash("StreamingPredict")

        def __call__(self,
                request: prediction_service.StreamingPredictRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> rest_streaming.ResponseIterator:
            raise NotImplementedError(
                "Method StreamingPredict is not available over REST transport"
            )
    class _StreamingRawPredict(PredictionServiceRestStub):
        def __hash__(self):
            return hash("StreamingRawPredict")

        def __call__(self,
                request: prediction_service.StreamingRawPredictRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> rest_streaming.ResponseIterator:
            raise NotImplementedError(
                "Method StreamingRawPredict is not available over REST transport"
            )
    class _StreamRawPredict(PredictionServiceRestStub):
        def __hash__(self):
            return hash("StreamRawPredict")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        def __call__(self,
                request: prediction_service.StreamRawPredictRequest, *,
                retry: OptionalRetry=gapic_v1.method.DEFAULT,
                timeout: Optional[float]=None,
                metadata: Sequence[Tuple[str, str]]=(),
                ) -> rest_streaming.ResponseIterator:
            r"""Call the stream raw predict method over HTTP.

            Args:
                request (~.prediction_service.StreamRawPredictRequest):
                    The request object. Request message for
                [PredictionService.StreamRawPredict][google.cloud.aiplatform.v1beta1.PredictionService.StreamRawPredict].
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.httpbody_pb2.HttpBody:
                    Message that represents an arbitrary HTTP body. It
                should only be used for payload formats that can't be
                represented as JSON, such as raw binary or an HTML page.

                This message can be used both in streaming and
                non-streaming API methods in the request as well as the
                response.

                It can be used as a top-level request field, which is
                convenient if one wants to extract parameters from
                either the URL or HTTP template into the request fields
                and also want access to the raw HTTP body.

                Example:

                ::

                    message GetResourceRequest {
                      // A unique request id.
                      string request_id = 1;

                      // The raw HTTP body is bound to this field.
                      google.api.HttpBody http_body = 2;

                    }

                    service ResourceService {
                      rpc GetResource(GetResourceRequest)
                        returns (google.api.HttpBody);
                      rpc UpdateResource(google.api.HttpBody)
                        returns (google.protobuf.Empty);

                    }

                Example with streaming methods:

                ::

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

            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}:streamRawPredict',
                'body': '*',
            },
{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/publishers/*/models/*}:streamRawPredict',
                'body': '*',
            },
            ]
            request, metadata = self._interceptor.pre_stream_raw_predict(request, metadata)
            pb_request = prediction_service.StreamRawPredictRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            uri = transcoded_request['uri']
            method = transcoded_request['method']

            # Jsonify the query params
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(self._get_unset_required_fields(query_params))

            # Send the request
            headers = dict(metadata)
            headers['Content-Type'] = 'application/json'
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
                )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = rest_streaming.ResponseIterator(response, httpbody_pb2.HttpBody)
            resp = self._interceptor.post_stream_raw_predict(resp)
            return resp

    @property
    def chat_completions(self) -> Callable[
            [prediction_service.ChatCompletionsRequest],
            httpbody_pb2.HttpBody]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ChatCompletions(self._session, self._host, self._interceptor) # type: ignore

    @property
    def count_tokens(self) -> Callable[
            [prediction_service.CountTokensRequest],
            prediction_service.CountTokensResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CountTokens(self._session, self._host, self._interceptor) # type: ignore

    @property
    def direct_predict(self) -> Callable[
            [prediction_service.DirectPredictRequest],
            prediction_service.DirectPredictResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._DirectPredict(self._session, self._host, self._interceptor) # type: ignore

    @property
    def direct_raw_predict(self) -> Callable[
            [prediction_service.DirectRawPredictRequest],
            prediction_service.DirectRawPredictResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._DirectRawPredict(self._session, self._host, self._interceptor) # type: ignore

    @property
    def embed_content(self) -> Callable[
            [prediction_service.EmbedContentRequest],
            prediction_service.EmbedContentResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._EmbedContent(self._session, self._host, self._interceptor) # type: ignore

    @property
    def explain(self) -> Callable[
            [prediction_service.ExplainRequest],
            prediction_service.ExplainResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._Explain(self._session, self._host, self._interceptor) # type: ignore

    @property
    def fetch_predict_operation(self) -> Callable[
            [prediction_service.FetchPredictOperationRequest],
            operations_pb2.Operation]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._FetchPredictOperation(self._session, self._host, self._interceptor) # type: ignore

    @property
    def generate_content(self) -> Callable[
            [prediction_service.GenerateContentRequest],
            prediction_service.GenerateContentResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GenerateContent(self._session, self._host, self._interceptor) # type: ignore

    @property
    def invoke(self) -> Callable[
            [prediction_service.InvokeRequest],
            httpbody_pb2.HttpBody]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._Invoke(self._session, self._host, self._interceptor) # type: ignore

    @property
    def predict(self) -> Callable[
            [prediction_service.PredictRequest],
            prediction_service.PredictResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._Predict(self._session, self._host, self._interceptor) # type: ignore

    @property
    def predict_long_running(self) -> Callable[
            [prediction_service.PredictLongRunningRequest],
            operations_pb2.Operation]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._PredictLongRunning(self._session, self._host, self._interceptor) # type: ignore

    @property
    def raw_predict(self) -> Callable[
            [prediction_service.RawPredictRequest],
            httpbody_pb2.HttpBody]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._RawPredict(self._session, self._host, self._interceptor) # type: ignore

    @property
    def server_streaming_predict(self) -> Callable[
            [prediction_service.StreamingPredictRequest],
            prediction_service.StreamingPredictResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ServerStreamingPredict(self._session, self._host, self._interceptor) # type: ignore

    @property
    def stream_direct_predict(self) -> Callable[
            [prediction_service.StreamDirectPredictRequest],
            prediction_service.StreamDirectPredictResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._StreamDirectPredict(self._session, self._host, self._interceptor) # type: ignore

    @property
    def stream_direct_raw_predict(self) -> Callable[
            [prediction_service.StreamDirectRawPredictRequest],
            prediction_service.StreamDirectRawPredictResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._StreamDirectRawPredict(self._session, self._host, self._interceptor) # type: ignore

    @property
    def stream_generate_content(self) -> Callable[
            [prediction_service.GenerateContentRequest],
            prediction_service.GenerateContentResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._StreamGenerateContent(self._session, self._host, self._interceptor) # type: ignore

    @property
    def streaming_predict(self) -> Callable[
            [prediction_service.StreamingPredictRequest],
            prediction_service.StreamingPredictResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._StreamingPredict(self._session, self._host, self._interceptor) # type: ignore

    @property
    def streaming_raw_predict(self) -> Callable[
            [prediction_service.StreamingRawPredictRequest],
            prediction_service.StreamingRawPredictResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._StreamingRawPredict(self._session, self._host, self._interceptor) # type: ignore

    @property
    def stream_raw_predict(self) -> Callable[
            [prediction_service.StreamRawPredictRequest],
            httpbody_pb2.HttpBody]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._StreamRawPredict(self._session, self._host, self._interceptor) # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__=(
    'PredictionServiceRestTransport',
)
