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
from googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1 import gapic_version as package_version

__version__ = package_version.__version__


from .services.prediction_service import PredictionServiceClient
from .services.prediction_service import PredictionServiceAsyncClient

from .types.api_auth import ApiAuth
from .types.auth import AuthConfig
from .types.auth import AuthType
from .types.auth import HttpElementLocation
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
from .types.content import ModalityTokenCount
from .types.content import ModelArmorConfig
from .types.content import Part
from .types.content import PrebuiltVoiceConfig
from .types.content import ProactivityConfig
from .types.content import RetrievalMetadata
from .types.content import SafetyRating
from .types.content import SafetySetting
from .types.content import SearchEntryPoint
from .types.content import Segment
from .types.content import SpeechConfig
from .types.content import UrlContextMetadata
from .types.content import UrlMetadata
from .types.content import VideoMetadata
from .types.content import VoiceConfig
from .types.content import HarmCategory
from .types.content import Modality
from .types.encryption_spec import EncryptionSpec
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
from .types.prediction_service import PredictLongRunningRequest
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
from .types.tool import EnterpriseWebSearch
from .types.tool import ExecutableCode
from .types.tool import ExternalApi
from .types.tool import FunctionCall
from .types.tool import FunctionCallingConfig
from .types.tool import FunctionDeclaration
from .types.tool import FunctionResponse
from .types.tool import GoogleMaps
from .types.tool import GoogleSearchRetrieval
from .types.tool import RagRetrievalConfig
from .types.tool import Retrieval
from .types.tool import RetrievalConfig
from .types.tool import Tool
from .types.tool import ToolConfig
from .types.tool import UrlContext
from .types.tool import VertexAISearch
from .types.tool import VertexRagStore
from .types.types import BoolArray
from .types.types import DoubleArray
from .types.types import Int64Array
from .types.types import StringArray
from .types.types import Tensor
from .types.vertex_rag_data import CorpusStatus
from .types.vertex_rag_data import FileStatus
from .types.vertex_rag_data import ImportRagFilesConfig
from .types.vertex_rag_data import RagChunk
from .types.vertex_rag_data import RagCorpus
from .types.vertex_rag_data import RagEmbeddingModelConfig
from .types.vertex_rag_data import RagEngineConfig
from .types.vertex_rag_data import RagFile
from .types.vertex_rag_data import RagFileChunkingConfig
from .types.vertex_rag_data import RagFileParsingConfig
from .types.vertex_rag_data import RagFileTransformationConfig
from .types.vertex_rag_data import RagManagedDbConfig
from .types.vertex_rag_data import RagVectorDbConfig
from .types.vertex_rag_data import UploadRagFileConfig
from .types.vertex_rag_data import VertexAiSearchConfig

__all__ = (
    'PredictionServiceAsyncClient',
'ApiAuth',
'Attribution',
'AuthConfig',
'AuthType',
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
'CorpusStatus',
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
'EncryptionSpec',
'EnterpriseWebSearch',
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
'ExternalApi',
'FeatureNoiseSigma',
'FetchPredictOperationRequest',
'FileData',
'FileStatus',
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
'GoogleMaps',
'GoogleSearchRetrieval',
'GroundingChunk',
'GroundingMetadata',
'GroundingSupport',
'HarmCategory',
'HttpElementLocation',
'ImportRagFilesConfig',
'Int64Array',
'IntegratedGradientsAttribution',
'JiraSource',
'LogprobsResult',
'Modality',
'ModalityTokenCount',
'ModelArmorConfig',
'ModelExplanation',
'Neighbor',
'Part',
'PrebuiltVoiceConfig',
'PredictLongRunningRequest',
'PredictRequest',
'PredictResponse',
'PredictionServiceClient',
'Presets',
'ProactivityConfig',
'RagChunk',
'RagCorpus',
'RagEmbeddingModelConfig',
'RagEngineConfig',
'RagFile',
'RagFileChunkingConfig',
'RagFileParsingConfig',
'RagFileTransformationConfig',
'RagManagedDbConfig',
'RagRetrievalConfig',
'RagVectorDbConfig',
'RawPredictRequest',
'Retrieval',
'RetrievalConfig',
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
'SpeechConfig',
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
'Type',
'UploadRagFileConfig',
'UrlContext',
'UrlContextMetadata',
'UrlMetadata',
'VertexAISearch',
'VertexAiSearchConfig',
'VertexRagStore',
'VideoMetadata',
'VoiceConfig',
'XraiAttribution',
)
