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
import json  # type: ignore
from google.api_core import path_template
from google.api_core import gapic_v1

from cloudsdk.google.protobuf import json_format
from .base import PredictionServiceTransport, DEFAULT_CLIENT_INFO

import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union


from google.api import httpbody_pb2  # type: ignore
from googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types import prediction_service
from google.longrunning import operations_pb2  # type: ignore


class _BasePredictionServiceRestTransport(PredictionServiceTransport):
    """Base REST backend transport for PredictionService.

    Note: This class is not meant to be used directly. Use its sync and
    async sub-classes instead.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1
    """

    def __init__(self, *,
            host: str = 'aiplatform.googleapis.com',
            credentials: Optional[Any] = None,
            client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
            always_use_jwt_access: Optional[bool] = False,
            url_scheme: str = 'https',
            api_audience: Optional[str] = None,
            ) -> None:
        """Instantiate the transport.
        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'aiplatform.googleapis.com').
            credentials (Optional[Any]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
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

    class _BaseChatCompletions:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
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
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.ChatCompletionsRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BaseChatCompletions._get_unset_required_fields(query_params))

            return query_params

    class _BaseCountTokens:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
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
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.CountTokensRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BaseCountTokens._get_unset_required_fields(query_params))

            return query_params

    class _BaseDirectPredict:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}:directPredict',
                'body': '*',
            },
            ]
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.DirectPredictRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BaseDirectPredict._get_unset_required_fields(query_params))

            return query_params

    class _BaseDirectRawPredict:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}:directRawPredict',
                'body': '*',
            },
            ]
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.DirectRawPredictRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BaseDirectRawPredict._get_unset_required_fields(query_params))

            return query_params

    class _BaseEmbedContent:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{model=projects/*/locations/*/publishers/*/models/*}:embedContent',
                'body': '*',
            },
            ]
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.EmbedContentRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BaseEmbedContent._get_unset_required_fields(query_params))

            return query_params

    class _BaseExplain:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
            http_options: List[Dict[str, str]] = [{
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/*}:explain',
                'body': '*',
            },
            ]
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.ExplainRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BaseExplain._get_unset_required_fields(query_params))

            return query_params

    class _BaseFetchPredictOperation:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
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
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.FetchPredictOperationRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BaseFetchPredictOperation._get_unset_required_fields(query_params))

            return query_params

    class _BaseGenerateContent:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
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
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.GenerateContentRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BaseGenerateContent._get_unset_required_fields(query_params))

            return query_params

    class _BaseInvoke:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
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
        {
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/openapi}/completions',
                'body': 'http_body',
            },
        {
                'method': 'post',
                'uri': '/v1beta1/{endpoint=projects/*/locations/*/endpoints/google}/science/inference',
                'body': 'http_body',
            },
            ]
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.InvokeRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BaseInvoke._get_unset_required_fields(query_params))

            return query_params

    class _BasePredict:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
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
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.PredictRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BasePredict._get_unset_required_fields(query_params))

            return query_params

    class _BasePredictLongRunning:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
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
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.PredictLongRunningRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BasePredictLongRunning._get_unset_required_fields(query_params))

            return query_params

    class _BaseRawPredict:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
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
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.RawPredictRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BaseRawPredict._get_unset_required_fields(query_params))

            return query_params

    class _BaseServerStreamingPredict:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
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
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.StreamingPredictRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BaseServerStreamingPredict._get_unset_required_fields(query_params))

            return query_params

    class _BaseStreamDirectPredict:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

    class _BaseStreamDirectRawPredict:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

    class _BaseStreamGenerateContent:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
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
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.GenerateContentRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BaseStreamGenerateContent._get_unset_required_fields(query_params))

            return query_params

    class _BaseStreamingPredict:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

    class _BaseStreamingRawPredict:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

    class _BaseStreamRawPredict:
        def __hash__(self):  # pragma: NO COVER
            return NotImplementedError("__hash__ must be implemented.")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] =  {
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {k: v for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items() if k not in message_dict}

        @staticmethod
        def _get_http_options():
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
            return http_options

        @staticmethod
        def _get_transcoded_request(http_options, request):
            pb_request = prediction_service.StreamRawPredictRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)
            return transcoded_request

        @staticmethod
        def _get_request_body_json(transcoded_request):
            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request['body'],
                use_integers_for_enums=False
            )
            return body
        @staticmethod
        def _get_query_params_json(transcoded_request):
            query_params = json.loads(json_format.MessageToJson(
                transcoded_request['query_params'],
                use_integers_for_enums=False,
            ))
            query_params.update(_BasePredictionServiceRestTransport._BaseStreamRawPredict._get_unset_required_fields(query_params))

            return query_params


__all__=(
    '_BasePredictionServiceRestTransport',
)
