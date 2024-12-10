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
from googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1 import gapic_version as package_version

__version__ = package_version.__version__


from .services.prediction_service import PredictionServiceClient
from .services.prediction_service import PredictionServiceAsyncClient

from .types.api_auth import ApiAuth
from .types.content import Blob
from .types.content import Candidate
from .types.content import Citation
from .types.content import CitationMetadata
from .types.content import Content
from .types.content import FileData
from .types.content import GenerationConfig
from .types.content import GroundingChunk
from .types.content import GroundingMetadata
from .types.content import GroundingSupport
from .types.content import LogprobsResult
from .types.content import Part
from .types.content import RetrievalMetadata
from .types.content import SafetyRating
from .types.content import SafetySetting
from .types.content import SearchEntryPoint
from .types.content import Segment
from .types.content import VideoMetadata
from .types.content import HarmCategory
from .types.explanation import Attribution
from .types.explanation import BlurBaselineConfig
from .types.explanation import Examples
from .types.explanation import ExamplesOverride
from .types.explanation import ExamplesRestrictionsNamespace
from .types.explanation import Explanation
from .types.explanation import ExplanationMetadataOverride
from .types.explanation import ExplanationParameters
from .types.explanation import ExplanationSpec
from .types.explanation import ExplanationSpecOverride
from .types.explanation import FeatureNoiseSigma
from .types.explanation import IntegratedGradientsAttribution
from .types.explanation import ModelExplanation
from .types.explanation import Neighbor
from .types.explanation import Presets
from .types.explanation import SampledShapleyAttribution
from .types.explanation import SmoothGradConfig
from .types.explanation import XraiAttribution
from .types.explanation_metadata import ExplanationMetadata
from .types.io import AvroSource
from .types.io import BigQueryDestination
from .types.io import BigQuerySource
from .types.io import ContainerRegistryDestination
from .types.io import CsvDestination
from .types.io import CsvSource
from .types.io import DirectUploadSource
from .types.io import GcsDestination
from .types.io import GcsSource
from .types.io import GoogleDriveSource
from .types.io import JiraSource
from .types.io import SharePointSources
from .types.io import SlackSource
from .types.io import TFRecordDestination
from .types.openapi import Schema
from .types.openapi import Type
from .types.prediction_service import ChatCompletionsRequest
from .types.prediction_service import CountTokensRequest
from .types.prediction_service import CountTokensResponse
from .types.prediction_service import DirectPredictRequest
from .types.prediction_service import DirectPredictResponse
from .types.prediction_service import DirectRawPredictRequest
from .types.prediction_service import DirectRawPredictResponse
from .types.prediction_service import ExplainRequest
from .types.prediction_service import ExplainResponse
from .types.prediction_service import FetchPredictOperationRequest
from .types.prediction_service import GenerateContentRequest
from .types.prediction_service import GenerateContentResponse
from .types.prediction_service import GenerateVideoResponse
from .types.prediction_service import PredictLongRunningMetadata
from .types.prediction_service import PredictLongRunningRequest
from .types.prediction_service import PredictLongRunningResponse
from .types.prediction_service import PredictRequest
from .types.prediction_service import PredictResponse
from .types.prediction_service import RawPredictRequest
from .types.prediction_service import StreamDirectPredictRequest
from .types.prediction_service import StreamDirectPredictResponse
from .types.prediction_service import StreamDirectRawPredictRequest
from .types.prediction_service import StreamDirectRawPredictResponse
from .types.prediction_service import StreamingPredictRequest
from .types.prediction_service import StreamingPredictResponse
from .types.prediction_service import StreamingRawPredictRequest
from .types.prediction_service import StreamingRawPredictResponse
from .types.prediction_service import StreamRawPredictRequest
from .types.tool import CodeExecutionResult
from .types.tool import DynamicRetrievalConfig
from .types.tool import ExecutableCode
from .types.tool import FunctionCall
from .types.tool import FunctionCallingConfig
from .types.tool import FunctionDeclaration
from .types.tool import FunctionResponse
from .types.tool import GoogleSearchRetrieval
from .types.tool import RagRetrievalConfig
from .types.tool import Retrieval
from .types.tool import Tool
from .types.tool import ToolConfig
from .types.tool import ToolUseExample
from .types.tool import VertexAISearch
from .types.tool import VertexRagStore
from .types.types import BoolArray
from .types.types import DoubleArray
from .types.types import Int64Array
from .types.types import StringArray
from .types.types import Tensor

__all__ = (
    'PredictionServiceAsyncClient',
'ApiAuth',
'Attribution',
'AvroSource',
'BigQueryDestination',
'BigQuerySource',
'Blob',
'BlurBaselineConfig',
'BoolArray',
'Candidate',
'ChatCompletionsRequest',
'Citation',
'CitationMetadata',
'CodeExecutionResult',
'ContainerRegistryDestination',
'Content',
'CountTokensRequest',
'CountTokensResponse',
'CsvDestination',
'CsvSource',
'DirectPredictRequest',
'DirectPredictResponse',
'DirectRawPredictRequest',
'DirectRawPredictResponse',
'DirectUploadSource',
'DoubleArray',
'DynamicRetrievalConfig',
'Examples',
'ExamplesOverride',
'ExamplesRestrictionsNamespace',
'ExecutableCode',
'ExplainRequest',
'ExplainResponse',
'Explanation',
'ExplanationMetadata',
'ExplanationMetadataOverride',
'ExplanationParameters',
'ExplanationSpec',
'ExplanationSpecOverride',
'FeatureNoiseSigma',
'FetchPredictOperationRequest',
'FileData',
'FunctionCall',
'FunctionCallingConfig',
'FunctionDeclaration',
'FunctionResponse',
'GcsDestination',
'GcsSource',
'GenerateContentRequest',
'GenerateContentResponse',
'GenerateVideoResponse',
'GenerationConfig',
'GoogleDriveSource',
'GoogleSearchRetrieval',
'GroundingChunk',
'GroundingMetadata',
'GroundingSupport',
'HarmCategory',
'Int64Array',
'IntegratedGradientsAttribution',
'JiraSource',
'LogprobsResult',
'ModelExplanation',
'Neighbor',
'Part',
'PredictLongRunningMetadata',
'PredictLongRunningRequest',
'PredictLongRunningResponse',
'PredictRequest',
'PredictResponse',
'PredictionServiceClient',
'Presets',
'RagRetrievalConfig',
'RawPredictRequest',
'Retrieval',
'RetrievalMetadata',
'SafetyRating',
'SafetySetting',
'SampledShapleyAttribution',
'Schema',
'SearchEntryPoint',
'Segment',
'SharePointSources',
'SlackSource',
'SmoothGradConfig',
'StreamDirectPredictRequest',
'StreamDirectPredictResponse',
'StreamDirectRawPredictRequest',
'StreamDirectRawPredictResponse',
'StreamRawPredictRequest',
'StreamingPredictRequest',
'StreamingPredictResponse',
'StreamingRawPredictRequest',
'StreamingRawPredictResponse',
'StringArray',
'TFRecordDestination',
'Tensor',
'Tool',
'ToolConfig',
'ToolUseExample',
'Type',
'VertexAISearch',
'VertexRagStore',
'VideoMetadata',
'XraiAttribution',
)
