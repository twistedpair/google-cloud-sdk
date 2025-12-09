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

from cloudsdk.google.protobuf import duration_pb2  # type: ignore
from cloudsdk.google.protobuf import struct_pb2  # type: ignore
from google.type import date_pb2  # type: ignore
from googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types import openapi
from googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types import tool
from googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types import vertex_rag_data


__protobuf__ = proto.module(
    package='google.cloud.aiplatform.v1',
    manifest={
        'HarmCategory',
        'Modality',
        'Content',
        'Part',
        'Blob',
        'FileData',
        'VideoMetadata',
        'PrebuiltVoiceConfig',
        'VoiceConfig',
        'SpeakerVoiceConfig',
        'MultiSpeakerVoiceConfig',
        'SpeechConfig',
        'ProactivityConfig',
        'ImageConfig',
        'GenerationConfig',
        'SafetySetting',
        'SafetyRating',
        'CitationMetadata',
        'Citation',
        'Candidate',
        'UrlContextMetadata',
        'UrlMetadata',
        'LogprobsResult',
        'Segment',
        'GroundingChunk',
        'GroundingSupport',
        'GroundingMetadata',
        'SearchEntryPoint',
        'RetrievalMetadata',
        'ModelArmorConfig',
        'ModalityTokenCount',
    },
)


class HarmCategory(proto.Enum):
    r"""Harm categories that can be detected in user input and model
    responses.

    Values:
        HARM_CATEGORY_UNSPECIFIED (0):
            Default value. This value is unused.
        HARM_CATEGORY_HATE_SPEECH (1):
            Content that promotes violence or incites
            hatred against individuals or groups based on
            certain attributes.
        HARM_CATEGORY_DANGEROUS_CONTENT (2):
            Content that promotes, facilitates, or
            enables dangerous activities.
        HARM_CATEGORY_HARASSMENT (3):
            Abusive, threatening, or content intended to
            bully, torment, or ridicule.
        HARM_CATEGORY_SEXUALLY_EXPLICIT (4):
            Content that contains sexually explicit
            material.
        HARM_CATEGORY_CIVIC_INTEGRITY (5):
            Deprecated: Election filter is not longer
            supported. The harm category is civic integrity.
        HARM_CATEGORY_IMAGE_HATE (6):
            Images that contain hate speech.
        HARM_CATEGORY_IMAGE_DANGEROUS_CONTENT (7):
            Images that contain dangerous content.
        HARM_CATEGORY_IMAGE_HARASSMENT (8):
            Images that contain harassment.
        HARM_CATEGORY_IMAGE_SEXUALLY_EXPLICIT (9):
            Images that contain sexually explicit
            content.
        HARM_CATEGORY_JAILBREAK (10):
            Prompts designed to bypass safety filters.
    """
    HARM_CATEGORY_UNSPECIFIED = 0
    HARM_CATEGORY_HATE_SPEECH = 1
    HARM_CATEGORY_DANGEROUS_CONTENT = 2
    HARM_CATEGORY_HARASSMENT = 3
    HARM_CATEGORY_SEXUALLY_EXPLICIT = 4
    HARM_CATEGORY_CIVIC_INTEGRITY = 5
    HARM_CATEGORY_IMAGE_HATE = 6
    HARM_CATEGORY_IMAGE_DANGEROUS_CONTENT = 7
    HARM_CATEGORY_IMAGE_HARASSMENT = 8
    HARM_CATEGORY_IMAGE_SEXUALLY_EXPLICIT = 9
    HARM_CATEGORY_JAILBREAK = 10


class Modality(proto.Enum):
    r"""The modality of a ``Part`` of a ``Content`` message. A modality is
    the type of media, such as an image or a video. It is used to
    categorize the content of a ``Part`` for token counting purposes.

    Values:
        MODALITY_UNSPECIFIED (0):
            When a modality is not specified, it is treated as ``TEXT``.
        TEXT (1):
            The ``Part`` contains plain text.
        IMAGE (2):
            The ``Part`` contains an image.
        VIDEO (3):
            The ``Part`` contains a video.
        AUDIO (4):
            The ``Part`` contains audio.
        DOCUMENT (5):
            The ``Part`` contains a document, such as a PDF.
    """
    MODALITY_UNSPECIFIED = 0
    TEXT = 1
    IMAGE = 2
    VIDEO = 3
    AUDIO = 4
    DOCUMENT = 5


class Content(proto.Message):
    r"""The structured data content of a message.

    A [Content][google.cloud.aiplatform.master.Content] message contains
    a ``role`` field, which indicates the producer of the content, and a
    ``parts`` field, which contains the multi-part data of the message.

    Attributes:
        role (str):
            Optional. The producer of the content. Must
            be either 'user' or 'model'.
            If not set, the service will default to 'user'.
        parts (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.Part]):
            Required. A list of
            [Part][google.cloud.aiplatform.master.Part] objects that
            make up a single message. Parts of a message can have
            different MIME types.

            A [Content][google.cloud.aiplatform.master.Content] message
            must have at least one
            [Part][google.cloud.aiplatform.master.Part].
    """

    role: str = proto.Field(
        proto.STRING,
        number=1,
    )
    parts: MutableSequence['Part'] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message='Part',
    )


class Part(proto.Message):
    r"""A datatype containing media that is part of a multi-part
    [Content][google.cloud.aiplatform.master.Content] message.

    A ``Part`` consists of data which has an associated datatype. A
    ``Part`` can only contain one of the accepted types in
    ``Part.data``.

    For media types that are not text, ``Part`` must have a fixed IANA
    MIME type identifying the type and subtype of the media if
    ``inline_data`` or ``file_data`` field is filled with raw bytes.

    This message has `oneof`_ fields (mutually exclusive fields).
    For each oneof, at most one member field can be set at the same time.
    Setting any member of the oneof automatically clears all other
    members.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        text (str):
            Optional. The text content of the part.

            This field is a member of `oneof`_ ``data``.
        inline_data (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.Blob):
            Optional. The inline data content of the
            part. This can be used to include images, audio,
            or video in a request.

            This field is a member of `oneof`_ ``data``.
        file_data (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.FileData):
            Optional. The URI-based data of the part.
            This can be used to include files from Google
            Cloud Storage.

            This field is a member of `oneof`_ ``data``.
        function_call (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.FunctionCall):
            Optional. A predicted function call returned
            from the model. This contains the name of the
            function to call and the arguments to pass to
            the function.

            This field is a member of `oneof`_ ``data``.
        function_response (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.FunctionResponse):
            Optional. The result of a function call. This
            is used to provide the model with the result of
            a function call that it predicted.

            This field is a member of `oneof`_ ``data``.
        executable_code (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.ExecutableCode):
            Optional. Code generated by the model that is
            intended to be executed.

            This field is a member of `oneof`_ ``data``.
        code_execution_result (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.CodeExecutionResult):
            Optional. The result of executing the
            [ExecutableCode][google.cloud.aiplatform.master.ExecutableCode].

            This field is a member of `oneof`_ ``data``.
        video_metadata (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.VideoMetadata):
            Optional. Video metadata. The metadata should only be
            specified while the video data is presented in inline_data
            or file_data.

            This field is a member of `oneof`_ ``metadata``.
        thought (bool):
            Optional. Indicates whether the ``part`` represents the
            model's thought process or reasoning.
        thought_signature (bytes):
            Optional. An opaque signature for the thought
            so it can be reused in subsequent requests.
    """

    text: str = proto.Field(
        proto.STRING,
        number=1,
        oneof='data',
    )
    inline_data: 'Blob' = proto.Field(
        proto.MESSAGE,
        number=2,
        oneof='data',
        message='Blob',
    )
    file_data: 'FileData' = proto.Field(
        proto.MESSAGE,
        number=3,
        oneof='data',
        message='FileData',
    )
    function_call: tool.FunctionCall = proto.Field(
        proto.MESSAGE,
        number=5,
        oneof='data',
        message=tool.FunctionCall,
    )
    function_response: tool.FunctionResponse = proto.Field(
        proto.MESSAGE,
        number=6,
        oneof='data',
        message=tool.FunctionResponse,
    )
    executable_code: tool.ExecutableCode = proto.Field(
        proto.MESSAGE,
        number=8,
        oneof='data',
        message=tool.ExecutableCode,
    )
    code_execution_result: tool.CodeExecutionResult = proto.Field(
        proto.MESSAGE,
        number=9,
        oneof='data',
        message=tool.CodeExecutionResult,
    )
    video_metadata: 'VideoMetadata' = proto.Field(
        proto.MESSAGE,
        number=4,
        oneof='metadata',
        message='VideoMetadata',
    )
    thought: bool = proto.Field(
        proto.BOOL,
        number=10,
    )
    thought_signature: bytes = proto.Field(
        proto.BYTES,
        number=11,
    )


class Blob(proto.Message):
    r"""A content blob.

    A [Blob][google.cloud.aiplatform.master.Blob] contains data of a
    specific media type. It is used to represent images, audio, and
    video.

    Attributes:
        mime_type (str):
            Required. The IANA standard MIME type of the
            source data.
        data (bytes):
            Required. The raw bytes of the data.
        display_name (str):
            Optional. The display name of the blob. Used to provide a
            label or filename to distinguish blobs.

            This field is only returned in ``PromptMessage`` for prompt
            management. It is used in the Gemini calls only when
            server-side tools (``code_execution``, ``google_search``,
            and ``url_context``) are enabled.
    """

    mime_type: str = proto.Field(
        proto.STRING,
        number=1,
    )
    data: bytes = proto.Field(
        proto.BYTES,
        number=2,
    )
    display_name: str = proto.Field(
        proto.STRING,
        number=4,
    )


class FileData(proto.Message):
    r"""URI-based data.

    A [FileData][google.cloud.aiplatform.master.FileData] message
    contains a URI pointing to data of a specific media type. It is used
    to represent images, audio, and video stored in Google Cloud
    Storage.

    Attributes:
        mime_type (str):
            Required. The IANA standard MIME type of the
            source data.
        file_uri (str):
            Required. The URI of the file in Google Cloud
            Storage.
        display_name (str):
            Optional. The display name of the file. Used to provide a
            label or filename to distinguish files.

            This field is only returned in ``PromptMessage`` for prompt
            management. It is used in the Gemini calls only when server
            side tools (``code_execution``, ``google_search``, and
            ``url_context``) are enabled.
    """

    mime_type: str = proto.Field(
        proto.STRING,
        number=1,
    )
    file_uri: str = proto.Field(
        proto.STRING,
        number=2,
    )
    display_name: str = proto.Field(
        proto.STRING,
        number=3,
    )


class VideoMetadata(proto.Message):
    r"""Provides metadata for a video, including the start and end
    offsets for clipping and the frame rate.

    Attributes:
        start_offset (google.protobuf.duration_pb2.Duration):
            Optional. The start offset of the video.
        end_offset (google.protobuf.duration_pb2.Duration):
            Optional. The end offset of the video.
        fps (float):
            Optional. The frame rate of the video sent to the model. If
            not specified, the default value is 1.0. The valid range is
            (0.0, 24.0].
    """

    start_offset: duration_pb2.Duration = proto.Field(
        proto.MESSAGE,
        number=1,
        message=duration_pb2.Duration,
    )
    end_offset: duration_pb2.Duration = proto.Field(
        proto.MESSAGE,
        number=2,
        message=duration_pb2.Duration,
    )
    fps: float = proto.Field(
        proto.DOUBLE,
        number=3,
    )


class PrebuiltVoiceConfig(proto.Message):
    r"""Configuration for a prebuilt voice.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        voice_name (str):
            The name of the prebuilt voice to use.

            This field is a member of `oneof`_ ``_voice_name``.
    """

    voice_name: str = proto.Field(
        proto.STRING,
        number=1,
        optional=True,
    )


class VoiceConfig(proto.Message):
    r"""Configuration for a voice.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        prebuilt_voice_config (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.PrebuiltVoiceConfig):
            The configuration for a prebuilt voice.

            This field is a member of `oneof`_ ``voice_config``.
    """

    prebuilt_voice_config: 'PrebuiltVoiceConfig' = proto.Field(
        proto.MESSAGE,
        number=1,
        oneof='voice_config',
        message='PrebuiltVoiceConfig',
    )


class SpeakerVoiceConfig(proto.Message):
    r"""Configuration for a single speaker in a multi-speaker setup.

    Attributes:
        speaker (str):
            Required. The name of the speaker. This
            should be the same as the speaker name used in
            the prompt.
        voice_config (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.VoiceConfig):
            Required. The configuration for the voice of
            this speaker.
    """

    speaker: str = proto.Field(
        proto.STRING,
        number=1,
    )
    voice_config: 'VoiceConfig' = proto.Field(
        proto.MESSAGE,
        number=2,
        message='VoiceConfig',
    )


class MultiSpeakerVoiceConfig(proto.Message):
    r"""Configuration for a multi-speaker text-to-speech request.

    Attributes:
        speaker_voice_configs (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.SpeakerVoiceConfig]):
            Required. A list of configurations for the
            voices of the speakers. Exactly two speaker
            voice configurations must be provided.
    """

    speaker_voice_configs: MutableSequence['SpeakerVoiceConfig'] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message='SpeakerVoiceConfig',
    )


class SpeechConfig(proto.Message):
    r"""Configuration for speech generation.

    Attributes:
        voice_config (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.VoiceConfig):
            The configuration for the voice to use.
        language_code (str):
            Optional. The language code (ISO 639-1) for
            the speech synthesis.
        multi_speaker_voice_config (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.MultiSpeakerVoiceConfig):
            The configuration for a multi-speaker text-to-speech
            request. This field is mutually exclusive with
            ``voice_config``.
    """

    voice_config: 'VoiceConfig' = proto.Field(
        proto.MESSAGE,
        number=1,
        message='VoiceConfig',
    )
    language_code: str = proto.Field(
        proto.STRING,
        number=2,
    )
    multi_speaker_voice_config: 'MultiSpeakerVoiceConfig' = proto.Field(
        proto.MESSAGE,
        number=3,
        message='MultiSpeakerVoiceConfig',
    )


class ProactivityConfig(proto.Message):
    r"""Configures the model's proactivity. Proactivity determines
    how the model should respond to input. When proactivity is
    enabled, the model can choose to ignore irrelevant input,
    respond to contextual cues, and generate content even when not
    explicitly prompted. This is useful for more natural, human-like
    interactions in streaming use cases like audio and video.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        proactive_audio (bool):
            Optional. If enabled, the model can
            proactively respond to audio input, for example
            by ignoring out of context speech.

            This field is a member of `oneof`_ ``_proactive_audio``.
    """

    proactive_audio: bool = proto.Field(
        proto.BOOL,
        number=2,
        optional=True,
    )


class ImageConfig(proto.Message):
    r"""Configuration for image generation.

    This message allows you to control various aspects of image
    generation, such as the output format, aspect ratio, and whether
    the model can generate images of people.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        image_output_options (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.ImageConfig.ImageOutputOptions):
            Optional. The image output format for
            generated images.

            This field is a member of `oneof`_ ``_image_output_options``.
        aspect_ratio (str):
            Optional. The desired aspect ratio for the
            generated images. The following aspect ratios
            are supported:

            "1:1"
            "2:3", "3:2"
            "3:4", "4:3"
            "4:5", "5:4"
            "9:16", "16:9"
            "21:9".

            This field is a member of `oneof`_ ``_aspect_ratio``.
        person_generation (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.ImageConfig.PersonGeneration):
            Optional. Controls whether the model can
            generate people.

            This field is a member of `oneof`_ ``_person_generation``.
    """
    class PersonGeneration(proto.Enum):
        r"""Enum for controlling the generation of people in images.

        Values:
            PERSON_GENERATION_UNSPECIFIED (0):
                The default behavior is unspecified. The
                model will decide whether to generate images of
                people.
            ALLOW_ALL (1):
                Allows the model to generate images of
                people, including adults and children.
            ALLOW_ADULT (2):
                Allows the model to generate images of
                adults, but not children.
            ALLOW_NONE (3):
                Prevents the model from generating images of
                people.
        """
        PERSON_GENERATION_UNSPECIFIED = 0
        ALLOW_ALL = 1
        ALLOW_ADULT = 2
        ALLOW_NONE = 3

    class ImageOutputOptions(proto.Message):
        r"""The image output format for generated images.

        .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

        Attributes:
            mime_type (str):
                Optional. The image format that the output
                should be saved as.

                This field is a member of `oneof`_ ``_mime_type``.
            compression_quality (int):
                Optional. The compression quality of the
                output image.

                This field is a member of `oneof`_ ``_compression_quality``.
        """

        mime_type: str = proto.Field(
            proto.STRING,
            number=1,
            optional=True,
        )
        compression_quality: int = proto.Field(
            proto.INT32,
            number=2,
            optional=True,
        )

    image_output_options: ImageOutputOptions = proto.Field(
        proto.MESSAGE,
        number=1,
        optional=True,
        message=ImageOutputOptions,
    )
    aspect_ratio: str = proto.Field(
        proto.STRING,
        number=2,
        optional=True,
    )
    person_generation: PersonGeneration = proto.Field(
        proto.ENUM,
        number=3,
        optional=True,
        enum=PersonGeneration,
    )


class GenerationConfig(proto.Message):
    r"""Configuration for content generation.

    This message contains all the parameters that control how the
    model generates content. It allows you to influence the
    randomness, length, and structure of the output.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        temperature (float):
            Optional. Controls the randomness of the output. A higher
            temperature results in more creative and diverse responses,
            while a lower temperature makes the output more predictable
            and focused. The valid range is (0.0, 2.0].

            This field is a member of `oneof`_ ``_temperature``.
        top_p (float):
            Optional. Specifies the nucleus sampling threshold. The
            model considers only the smallest set of tokens whose
            cumulative probability is at least ``top_p``. This helps
            generate more diverse and less repetitive responses. For
            example, a ``top_p`` of 0.9 means the model considers tokens
            until the cumulative probability of the tokens to select
            from reaches 0.9. It's recommended to adjust either
            temperature or ``top_p``, but not both.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (float):
            Optional. Specifies the top-k sampling threshold. The model
            considers only the top k most probable tokens for the next
            token. This can be useful for generating more coherent and
            less random text. For example, a ``top_k`` of 40 means the
            model will choose the next word from the 40 most likely
            words.

            This field is a member of `oneof`_ ``_top_k``.
        candidate_count (int):
            Optional. The number of candidate responses to generate.

            A higher ``candidate_count`` can provide more options to
            choose from, but it also consumes more resources. This can
            be useful for generating a variety of responses and
            selecting the best one.

            This field is a member of `oneof`_ ``_candidate_count``.
        max_output_tokens (int):
            Optional. The maximum number of tokens to
            generate in the response.
            A token is approximately four characters. The
            default value varies by model. This parameter
            can be used to control the length of the
            generated text and prevent overly long
            responses.

            This field is a member of `oneof`_ ``_max_output_tokens``.
        stop_sequences (MutableSequence[str]):
            Optional. A list of character sequences that will stop the
            model from generating further tokens. If a stop sequence is
            generated, the output will end at that point. This is useful
            for controlling the length and structure of the output. For
            example, you can use ["\\n", "###"] to stop generation at a
            new line or a specific marker.
        response_logprobs (bool):
            Optional. If set to true, the log
            probabilities of the output tokens are returned.

            Log probabilities are the logarithm of the
            probability of a token appearing in the output.
            A higher log probability means the token is more
            likely to be generated. This can be useful for
            analyzing the model's confidence in its own
            output and for debugging.

            This field is a member of `oneof`_ ``_response_logprobs``.
        logprobs (int):
            Optional. The number of top log probabilities
            to return for each token.
            This can be used to see which other tokens were
            considered likely candidates for a given
            position. A higher value will return more
            options, but it will also increase the size of
            the response.

            This field is a member of `oneof`_ ``_logprobs``.
        presence_penalty (float):
            Optional. Penalizes tokens that have already appeared in the
            generated text. A positive value encourages the model to
            generate more diverse and less repetitive text. Valid values
            can range from [-2.0, 2.0].

            This field is a member of `oneof`_ ``_presence_penalty``.
        frequency_penalty (float):
            Optional. Penalizes tokens based on their frequency in the
            generated text. A positive value helps to reduce the
            repetition of words and phrases. Valid values can range from
            [-2.0, 2.0].

            This field is a member of `oneof`_ ``_frequency_penalty``.
        seed (int):
            Optional. A seed for the random number generator.

            By setting a seed, you can make the model's output mostly
            deterministic. For a given prompt and parameters (like
            temperature, top_p, etc.), the model will produce the same
            response every time. However, it's not a guaranteed absolute
            deterministic behavior. This is different from parameters
            like ``temperature``, which control the *level* of
            randomness. ``seed`` ensures that the "random" choices the
            model makes are the same on every run, making it essential
            for testing and ensuring reproducible results.

            This field is a member of `oneof`_ ``_seed``.
        response_mime_type (str):
            Optional. The IANA standard MIME type of the
            response. The model will generate output that
            conforms to this MIME type. Supported values
            include 'text/plain' (default) and
            'application/json'. The model needs to be
            prompted to output the appropriate response
            type, otherwise the behavior is undefined. This
            is a preview feature.
        response_schema (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.Schema):
            Optional. Lets you to specify a schema for the model's
            response, ensuring that the output conforms to a particular
            structure. This is useful for generating structured data
            such as JSON. The schema is a subset of the `OpenAPI 3.0
            schema
            object <https://spec.openapis.org/oas/v3.0.3#schema>`__
            object.

            When this field is set, you must also set the
            ``response_mime_type`` to ``application/json``.

            This field is a member of `oneof`_ ``_response_schema``.
        response_json_schema (google.protobuf.struct_pb2.Value):
            Optional. When this field is set,
            [response_schema][google.cloud.aiplatform.master.GenerationConfig.response_schema]
            must be omitted and
            [response_mime_type][google.cloud.aiplatform.master.GenerationConfig.response_mime_type]
            must be set to ``application/json``.

            This field is a member of `oneof`_ ``_response_json_schema``.
        routing_config (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GenerationConfig.RoutingConfig):
            Optional. Routing configuration.

            This field is a member of `oneof`_ ``_routing_config``.
        audio_timestamp (bool):
            Optional. If enabled, audio timestamps will
            be included in the request to the model. This
            can be useful for synchronizing audio with other
            modalities in the response.

            This field is a member of `oneof`_ ``_audio_timestamp``.
        response_modalities (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GenerationConfig.Modality]):
            Optional. The modalities of the response. The model will
            generate a response that includes all the specified
            modalities. For example, if this is set to
            ``[TEXT, IMAGE]``, the response will include both text and
            an image.
        media_resolution (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GenerationConfig.MediaResolution):
            Optional. The token resolution at which input
            media content is sampled. This is used to
            control the trade-off between the quality of the
            response and the number of tokens used to
            represent the media. A higher resolution allows
            the model to perceive more detail, which can
            lead to a more nuanced response, but it will
            also use more tokens. This does not affect the
            image dimensions sent to the model.

            This field is a member of `oneof`_ ``_media_resolution``.
        speech_config (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.SpeechConfig):
            Optional. The speech generation config.

            This field is a member of `oneof`_ ``_speech_config``.
        thinking_config (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GenerationConfig.ThinkingConfig):
            Optional. Configuration for thinking
            features. An error will be returned if this
            field is set for models that don't support
            thinking.
        enable_affective_dialog (bool):
            Optional. If enabled, the model will detect
            emotions and adapt its responses accordingly.
            For example, if the model detects that the user
            is frustrated, it may provide a more empathetic
            response.

            This field is a member of `oneof`_ ``_enable_affective_dialog``.
        image_config (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.ImageConfig):
            Optional. Config for image generation
            features.

            This field is a member of `oneof`_ ``_image_config``.
    """
    class Modality(proto.Enum):
        r"""The modalities of the response.

        Values:
            MODALITY_UNSPECIFIED (0):
                Unspecified modality. Will be processed as
                text.
            TEXT (1):
                Text modality.
            IMAGE (2):
                Image modality.
            AUDIO (3):
                Audio modality.
        """
        MODALITY_UNSPECIFIED = 0
        TEXT = 1
        IMAGE = 2
        AUDIO = 3

    class MediaResolution(proto.Enum):
        r"""Media resolution for the input media.

        Values:
            MEDIA_RESOLUTION_UNSPECIFIED (0):
                Media resolution has not been set.
            MEDIA_RESOLUTION_LOW (1):
                Media resolution set to low (64 tokens).
            MEDIA_RESOLUTION_MEDIUM (2):
                Media resolution set to medium (256 tokens).
            MEDIA_RESOLUTION_HIGH (3):
                Media resolution set to high (zoomed
                reframing with 256 tokens).
        """
        MEDIA_RESOLUTION_UNSPECIFIED = 0
        MEDIA_RESOLUTION_LOW = 1
        MEDIA_RESOLUTION_MEDIUM = 2
        MEDIA_RESOLUTION_HIGH = 3

    class RoutingConfig(proto.Message):
        r"""The configuration for routing the request to a specific
        model. This can be used to control which model is used for the
        generation, either automatically or by specifying a model name.

        This message has `oneof`_ fields (mutually exclusive fields).
        For each oneof, at most one member field can be set at the same time.
        Setting any member of the oneof automatically clears all other
        members.

        .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

        Attributes:
            auto_mode (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GenerationConfig.RoutingConfig.AutoRoutingMode):
                In this mode, the model is selected
                automatically based on the content of the
                request.

                This field is a member of `oneof`_ ``routing_config``.
            manual_mode (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GenerationConfig.RoutingConfig.ManualRoutingMode):
                In this mode, the model is specified
                manually.

                This field is a member of `oneof`_ ``routing_config``.
        """

        class AutoRoutingMode(proto.Message):
            r"""The configuration for automated routing.

            When automated routing is specified, the routing will be
            determined by the pretrained routing model and customer provided
            model routing preference.


            .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

            Attributes:
                model_routing_preference (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GenerationConfig.RoutingConfig.AutoRoutingMode.ModelRoutingPreference):
                    The model routing preference.

                    This field is a member of `oneof`_ ``_model_routing_preference``.
            """
            class ModelRoutingPreference(proto.Enum):
                r"""The model routing preference.

                Values:
                    UNKNOWN (0):
                        Unspecified model routing preference.
                    PRIORITIZE_QUALITY (1):
                        The model will be selected to prioritize the
                        quality of the response.
                    BALANCED (2):
                        The model will be selected to balance quality
                        and cost.
                    PRIORITIZE_COST (3):
                        The model will be selected to prioritize the
                        cost of the request.
                """
                UNKNOWN = 0
                PRIORITIZE_QUALITY = 1
                BALANCED = 2
                PRIORITIZE_COST = 3

            model_routing_preference: 'GenerationConfig.RoutingConfig.AutoRoutingMode.ModelRoutingPreference' = proto.Field(
                proto.ENUM,
                number=1,
                optional=True,
                enum='GenerationConfig.RoutingConfig.AutoRoutingMode.ModelRoutingPreference',
            )

        class ManualRoutingMode(proto.Message):
            r"""The configuration for manual routing.

            When manual routing is specified, the model will be selected
            based on the model name provided.


            .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

            Attributes:
                model_name (str):
                    The name of the model to use. Only public LLM
                    models are accepted.

                    This field is a member of `oneof`_ ``_model_name``.
            """

            model_name: str = proto.Field(
                proto.STRING,
                number=1,
                optional=True,
            )

        auto_mode: 'GenerationConfig.RoutingConfig.AutoRoutingMode' = proto.Field(
            proto.MESSAGE,
            number=1,
            oneof='routing_config',
            message='GenerationConfig.RoutingConfig.AutoRoutingMode',
        )
        manual_mode: 'GenerationConfig.RoutingConfig.ManualRoutingMode' = proto.Field(
            proto.MESSAGE,
            number=2,
            oneof='routing_config',
            message='GenerationConfig.RoutingConfig.ManualRoutingMode',
        )

    class ThinkingConfig(proto.Message):
        r"""Configuration for the model's thinking features.

        "Thinking" is a process where the model breaks down a complex
        task into smaller, manageable steps. This allows the model to
        reason about the task, plan its approach, and execute the plan
        to generate a high-quality response.


        .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

        Attributes:
            include_thoughts (bool):
                Optional. If true, the model will include its
                thoughts in the response. "Thoughts" are the
                intermediate steps the model takes to arrive at
                the final response. They can provide insights
                into the model's reasoning process and help with
                debugging. If this is true, thoughts are
                returned only when available.

                This field is a member of `oneof`_ ``_include_thoughts``.
            thinking_budget (int):
                Optional. The token budget for the model's
                thinking process. The model will make a best
                effort to stay within this budget. This can be
                used to control the trade-off between response
                quality and latency.

                This field is a member of `oneof`_ ``_thinking_budget``.
        """

        include_thoughts: bool = proto.Field(
            proto.BOOL,
            number=1,
            optional=True,
        )
        thinking_budget: int = proto.Field(
            proto.INT32,
            number=3,
            optional=True,
        )

    temperature: float = proto.Field(
        proto.FLOAT,
        number=1,
        optional=True,
    )
    top_p: float = proto.Field(
        proto.FLOAT,
        number=2,
        optional=True,
    )
    top_k: float = proto.Field(
        proto.FLOAT,
        number=3,
        optional=True,
    )
    candidate_count: int = proto.Field(
        proto.INT32,
        number=4,
        optional=True,
    )
    max_output_tokens: int = proto.Field(
        proto.INT32,
        number=5,
        optional=True,
    )
    stop_sequences: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=6,
    )
    response_logprobs: bool = proto.Field(
        proto.BOOL,
        number=18,
        optional=True,
    )
    logprobs: int = proto.Field(
        proto.INT32,
        number=7,
        optional=True,
    )
    presence_penalty: float = proto.Field(
        proto.FLOAT,
        number=8,
        optional=True,
    )
    frequency_penalty: float = proto.Field(
        proto.FLOAT,
        number=9,
        optional=True,
    )
    seed: int = proto.Field(
        proto.INT32,
        number=12,
        optional=True,
    )
    response_mime_type: str = proto.Field(
        proto.STRING,
        number=13,
    )
    response_schema: openapi.Schema = proto.Field(
        proto.MESSAGE,
        number=16,
        optional=True,
        message=openapi.Schema,
    )
    response_json_schema: struct_pb2.Value = proto.Field(
        proto.MESSAGE,
        number=28,
        optional=True,
        message=struct_pb2.Value,
    )
    routing_config: RoutingConfig = proto.Field(
        proto.MESSAGE,
        number=17,
        optional=True,
        message=RoutingConfig,
    )
    audio_timestamp: bool = proto.Field(
        proto.BOOL,
        number=20,
        optional=True,
    )
    response_modalities: MutableSequence[Modality] = proto.RepeatedField(
        proto.ENUM,
        number=21,
        enum=Modality,
    )
    media_resolution: MediaResolution = proto.Field(
        proto.ENUM,
        number=22,
        optional=True,
        enum=MediaResolution,
    )
    speech_config: 'SpeechConfig' = proto.Field(
        proto.MESSAGE,
        number=23,
        optional=True,
        message='SpeechConfig',
    )
    thinking_config: ThinkingConfig = proto.Field(
        proto.MESSAGE,
        number=25,
        message=ThinkingConfig,
    )
    enable_affective_dialog: bool = proto.Field(
        proto.BOOL,
        number=29,
        optional=True,
    )
    image_config: 'ImageConfig' = proto.Field(
        proto.MESSAGE,
        number=30,
        optional=True,
        message='ImageConfig',
    )


class SafetySetting(proto.Message):
    r"""A safety setting that affects the safety-blocking behavior.

    A [SafetySetting][google.cloud.aiplatform.master.SafetySetting]
    consists of a harm
    [category][google.cloud.aiplatform.master.SafetySetting.category]
    and a
    [threshold][google.cloud.aiplatform.master.SafetySetting.threshold]
    for that category.

    Attributes:
        category (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.HarmCategory):
            Required. The harm category to be blocked.
        threshold (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.SafetySetting.HarmBlockThreshold):
            Required. The threshold for blocking content.
            If the harm probability exceeds this threshold,
            the content will be blocked.
        method (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.SafetySetting.HarmBlockMethod):
            Optional. The method for blocking content. If
            not specified, the default behavior is to use
            the probability score.
    """
    class HarmBlockThreshold(proto.Enum):
        r"""Thresholds for blocking content based on harm probability.

        Values:
            HARM_BLOCK_THRESHOLD_UNSPECIFIED (0):
                The harm block threshold is unspecified.
            BLOCK_LOW_AND_ABOVE (1):
                Block content with a low harm probability or
                higher.
            BLOCK_MEDIUM_AND_ABOVE (2):
                Block content with a medium harm probability
                or higher.
            BLOCK_ONLY_HIGH (3):
                Block content with a high harm probability.
            BLOCK_NONE (4):
                Do not block any content, regardless of its
                harm probability.
            OFF (5):
                Turn off the safety filter entirely.
        """
        HARM_BLOCK_THRESHOLD_UNSPECIFIED = 0
        BLOCK_LOW_AND_ABOVE = 1
        BLOCK_MEDIUM_AND_ABOVE = 2
        BLOCK_ONLY_HIGH = 3
        BLOCK_NONE = 4
        OFF = 5

    class HarmBlockMethod(proto.Enum):
        r"""The method for blocking content.

        Values:
            HARM_BLOCK_METHOD_UNSPECIFIED (0):
                The harm block method is unspecified.
            SEVERITY (1):
                The harm block method uses both probability
                and severity scores.
            PROBABILITY (2):
                The harm block method uses the probability
                score.
        """
        HARM_BLOCK_METHOD_UNSPECIFIED = 0
        SEVERITY = 1
        PROBABILITY = 2

    category: 'HarmCategory' = proto.Field(
        proto.ENUM,
        number=1,
        enum='HarmCategory',
    )
    threshold: HarmBlockThreshold = proto.Field(
        proto.ENUM,
        number=2,
        enum=HarmBlockThreshold,
    )
    method: HarmBlockMethod = proto.Field(
        proto.ENUM,
        number=4,
        enum=HarmBlockMethod,
    )


class SafetyRating(proto.Message):
    r"""A safety rating for a piece of content.

    The safety rating contains the harm category and the harm
    probability level.

    Attributes:
        category (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.HarmCategory):
            Output only. The harm category of this
            rating.
        probability (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.SafetyRating.HarmProbability):
            Output only. The probability of harm for this
            category.
        probability_score (float):
            Output only. The probability score of harm
            for this category.
        severity (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.SafetyRating.HarmSeverity):
            Output only. The severity of harm for this
            category.
        severity_score (float):
            Output only. The severity score of harm for
            this category.
        blocked (bool):
            Output only. Indicates whether the content
            was blocked because of this rating.
        overwritten_threshold (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.SafetySetting.HarmBlockThreshold):
            Output only. The overwritten threshold for
            the safety category of Gemini 2.0 image out. If
            minors are detected in the output image, the
            threshold of each safety category will be
            overwritten if user sets a lower threshold.
    """
    class HarmProbability(proto.Enum):
        r"""The probability of harm for a given category.

        Values:
            HARM_PROBABILITY_UNSPECIFIED (0):
                The harm probability is unspecified.
            NEGLIGIBLE (1):
                The harm probability is negligible.
            LOW (2):
                The harm probability is low.
            MEDIUM (3):
                The harm probability is medium.
            HIGH (4):
                The harm probability is high.
        """
        HARM_PROBABILITY_UNSPECIFIED = 0
        NEGLIGIBLE = 1
        LOW = 2
        MEDIUM = 3
        HIGH = 4

    class HarmSeverity(proto.Enum):
        r"""The severity of harm for a given category.

        Values:
            HARM_SEVERITY_UNSPECIFIED (0):
                The harm severity is unspecified.
            HARM_SEVERITY_NEGLIGIBLE (1):
                The harm severity is negligible.
            HARM_SEVERITY_LOW (2):
                The harm severity is low.
            HARM_SEVERITY_MEDIUM (3):
                The harm severity is medium.
            HARM_SEVERITY_HIGH (4):
                The harm severity is high.
        """
        HARM_SEVERITY_UNSPECIFIED = 0
        HARM_SEVERITY_NEGLIGIBLE = 1
        HARM_SEVERITY_LOW = 2
        HARM_SEVERITY_MEDIUM = 3
        HARM_SEVERITY_HIGH = 4

    category: 'HarmCategory' = proto.Field(
        proto.ENUM,
        number=1,
        enum='HarmCategory',
    )
    probability: HarmProbability = proto.Field(
        proto.ENUM,
        number=2,
        enum=HarmProbability,
    )
    probability_score: float = proto.Field(
        proto.FLOAT,
        number=5,
    )
    severity: HarmSeverity = proto.Field(
        proto.ENUM,
        number=6,
        enum=HarmSeverity,
    )
    severity_score: float = proto.Field(
        proto.FLOAT,
        number=7,
    )
    blocked: bool = proto.Field(
        proto.BOOL,
        number=3,
    )
    overwritten_threshold: 'SafetySetting.HarmBlockThreshold' = proto.Field(
        proto.ENUM,
        number=8,
        enum='SafetySetting.HarmBlockThreshold',
    )


class CitationMetadata(proto.Message):
    r"""A collection of citations that apply to a piece of generated
    content.

    Attributes:
        citations (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.Citation]):
            Output only. A list of citations for the
            content.
    """

    citations: MutableSequence['Citation'] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message='Citation',
    )


class Citation(proto.Message):
    r"""A citation for a piece of generatedcontent.

    Attributes:
        start_index (int):
            Output only. The start index of the citation
            in the content.
        end_index (int):
            Output only. The end index of the citation in
            the content.
        uri (str):
            Output only. The URI of the source of the
            citation.
        title (str):
            Output only. The title of the source of the
            citation.
        license_ (str):
            Output only. The license of the source of the
            citation.
        publication_date (google.type.date_pb2.Date):
            Output only. The publication date of the
            source of the citation.
    """

    start_index: int = proto.Field(
        proto.INT32,
        number=1,
    )
    end_index: int = proto.Field(
        proto.INT32,
        number=2,
    )
    uri: str = proto.Field(
        proto.STRING,
        number=3,
    )
    title: str = proto.Field(
        proto.STRING,
        number=4,
    )
    license_: str = proto.Field(
        proto.STRING,
        number=5,
    )
    publication_date: date_pb2.Date = proto.Field(
        proto.MESSAGE,
        number=6,
        message=date_pb2.Date,
    )


class Candidate(proto.Message):
    r"""A response candidate generated from the model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        index (int):
            Output only. The 0-based index of this candidate in the list
            of generated responses. This is useful for distinguishing
            between multiple candidates when ``candidate_count`` > 1.
        content (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.Content):
            Output only. The content of the candidate.
        avg_logprobs (float):
            Output only. The average log probability of
            the tokens in this candidate. This is a
            length-normalized score that can be used to
            compare the quality of candidates of different
            lengths. A higher average log probability
            suggests a more confident and coherent response.
        logprobs_result (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.LogprobsResult):
            Output only. The detailed log probability
            information for the tokens in this candidate.
            This is useful for debugging, understanding
            model uncertainty, and identifying potential
            "hallucinations".
        finish_reason (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.Candidate.FinishReason):
            Output only. The reason why the model stopped
            generating tokens. If empty, the model has not
            stopped generating.
        safety_ratings (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.SafetyRating]):
            Output only. A list of ratings for the safety
            of a response candidate.
            There is at most one rating per category.
        finish_message (str):
            Output only. Describes the reason the model stopped
            generating tokens in more detail. This field is returned
            only when ``finish_reason`` is set.

            This field is a member of `oneof`_ ``_finish_message``.
        citation_metadata (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.CitationMetadata):
            Output only. A collection of citations that
            apply to the generated content.
        grounding_metadata (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GroundingMetadata):
            Output only. Metadata returned when grounding
            is enabled. It contains the sources used to
            ground the generated content.
        url_context_metadata (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.UrlContextMetadata):
            Output only. Metadata returned when the model uses the
            ``url_context`` tool to get information from a user-provided
            URL.
    """
    class FinishReason(proto.Enum):
        r"""The reason why the model stopped generating tokens. If this
        field is empty, the model has not stopped generating.

        Values:
            FINISH_REASON_UNSPECIFIED (0):
                The finish reason is unspecified.
            STOP (1):
                The model reached a natural stopping point or
                a configured stop sequence.
            MAX_TOKENS (2):
                The model generated the maximum number of tokens allowed by
                the ``max_output_tokens`` parameter.
            SAFETY (3):
                The model stopped generating because the content potentially
                violates safety policies. NOTE: When streaming, the
                ``content`` field is empty if content filters block the
                output.
            RECITATION (4):
                The model stopped generating because the
                content may be a recitation from a source.
            OTHER (5):
                The model stopped generating for a reason not
                otherwise specified.
            BLOCKLIST (6):
                The model stopped generating because the
                content contains a term from a configured
                blocklist.
            PROHIBITED_CONTENT (7):
                The model stopped generating because the
                content may be prohibited.
            SPII (8):
                The model stopped generating because the
                content may contain sensitive personally
                identifiable information (SPII).
            MALFORMED_FUNCTION_CALL (9):
                The model generated a function call that is
                syntactically invalid and can't be parsed.
            MODEL_ARMOR (10):
                The model response was blocked by Model
                Armor.
            IMAGE_SAFETY (11):
                The generated image potentially violates
                safety policies.
            IMAGE_PROHIBITED_CONTENT (12):
                The generated image may contain prohibited
                content.
            IMAGE_RECITATION (13):
                The generated image may be a recitation from
                a source.
            IMAGE_OTHER (14):
                The image generation stopped for a reason not
                otherwise specified.
            UNEXPECTED_TOOL_CALL (15):
                The model generated a function call that is
                semantically invalid. This can happen, for
                example, if function calling is not enabled or
                the generated function is not in the function
                declaration.
            NO_IMAGE (16):
                The model was expected to generate an image,
                but didn't.
        """
        FINISH_REASON_UNSPECIFIED = 0
        STOP = 1
        MAX_TOKENS = 2
        SAFETY = 3
        RECITATION = 4
        OTHER = 5
        BLOCKLIST = 6
        PROHIBITED_CONTENT = 7
        SPII = 8
        MALFORMED_FUNCTION_CALL = 9
        MODEL_ARMOR = 10
        IMAGE_SAFETY = 11
        IMAGE_PROHIBITED_CONTENT = 12
        IMAGE_RECITATION = 13
        IMAGE_OTHER = 14
        UNEXPECTED_TOOL_CALL = 15
        NO_IMAGE = 16

    index: int = proto.Field(
        proto.INT32,
        number=1,
    )
    content: 'Content' = proto.Field(
        proto.MESSAGE,
        number=2,
        message='Content',
    )
    avg_logprobs: float = proto.Field(
        proto.DOUBLE,
        number=9,
    )
    logprobs_result: 'LogprobsResult' = proto.Field(
        proto.MESSAGE,
        number=10,
        message='LogprobsResult',
    )
    finish_reason: FinishReason = proto.Field(
        proto.ENUM,
        number=3,
        enum=FinishReason,
    )
    safety_ratings: MutableSequence['SafetyRating'] = proto.RepeatedField(
        proto.MESSAGE,
        number=4,
        message='SafetyRating',
    )
    finish_message: str = proto.Field(
        proto.STRING,
        number=5,
        optional=True,
    )
    citation_metadata: 'CitationMetadata' = proto.Field(
        proto.MESSAGE,
        number=6,
        message='CitationMetadata',
    )
    grounding_metadata: 'GroundingMetadata' = proto.Field(
        proto.MESSAGE,
        number=7,
        message='GroundingMetadata',
    )
    url_context_metadata: 'UrlContextMetadata' = proto.Field(
        proto.MESSAGE,
        number=13,
        message='UrlContextMetadata',
    )


class UrlContextMetadata(proto.Message):
    r"""Metadata returned when the model uses the ``url_context`` tool to
    get information from a user-provided URL.

    Attributes:
        url_metadata (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.UrlMetadata]):
            Output only. A list of URL metadata, with one
            entry for each URL retrieved by the tool.
    """

    url_metadata: MutableSequence['UrlMetadata'] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message='UrlMetadata',
    )


class UrlMetadata(proto.Message):
    r"""The metadata for a single URL retrieval.

    Attributes:
        retrieved_url (str):
            The URL retrieved by the tool.
        url_retrieval_status (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.UrlMetadata.UrlRetrievalStatus):
            The status of the URL retrieval.
    """
    class UrlRetrievalStatus(proto.Enum):
        r"""The status of a URL retrieval.

        Values:
            URL_RETRIEVAL_STATUS_UNSPECIFIED (0):
                Default value. This value is unused.
            URL_RETRIEVAL_STATUS_SUCCESS (1):
                The URL was retrieved successfully.
            URL_RETRIEVAL_STATUS_ERROR (2):
                The URL retrieval failed.
        """
        URL_RETRIEVAL_STATUS_UNSPECIFIED = 0
        URL_RETRIEVAL_STATUS_SUCCESS = 1
        URL_RETRIEVAL_STATUS_ERROR = 2

    retrieved_url: str = proto.Field(
        proto.STRING,
        number=1,
    )
    url_retrieval_status: UrlRetrievalStatus = proto.Field(
        proto.ENUM,
        number=2,
        enum=UrlRetrievalStatus,
    )


class LogprobsResult(proto.Message):
    r"""The log probabilities of the tokens generated by the model.

    This is useful for understanding the model's confidence in its
    predictions and for debugging. For example, you can use log
    probabilities to identify when the model is making a less
    confident prediction or to explore alternative responses that
    the model considered. A low log probability can also indicate
    that the model is "hallucinating" or generating factually
    incorrect information.

    Attributes:
        top_candidates (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.LogprobsResult.TopCandidates]):
            A list of the top candidate tokens at each
            decoding step. The length of this list is equal
            to the total number of decoding steps.
        chosen_candidates (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.LogprobsResult.Candidate]):
            A list of the chosen candidate tokens at each decoding step.
            The length of this list is equal to the total number of
            decoding steps. Note that the chosen candidate might not be
            in ``top_candidates``.
    """

    class Candidate(proto.Message):
        r"""A single token and its associated log probability.

        .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

        Attributes:
            token (str):
                The token's string representation.

                This field is a member of `oneof`_ ``_token``.
            token_id (int):
                The token's numerical ID. While the ``token`` field provides
                the string representation of the token, the ``token_id`` is
                the numerical representation that the model uses internally.
                This can be useful for developers who want to build custom
                logic based on the model's vocabulary.

                This field is a member of `oneof`_ ``_token_id``.
            log_probability (float):
                The log probability of this token. A higher
                value indicates that the model was more
                confident in this token. The log probability can
                be used to assess the relative likelihood of
                different tokens and to identify when the model
                is uncertain.

                This field is a member of `oneof`_ ``_log_probability``.
        """

        token: str = proto.Field(
            proto.STRING,
            number=1,
            optional=True,
        )
        token_id: int = proto.Field(
            proto.INT32,
            number=3,
            optional=True,
        )
        log_probability: float = proto.Field(
            proto.FLOAT,
            number=2,
            optional=True,
        )

    class TopCandidates(proto.Message):
        r"""A list of the top candidate tokens and their log
        probabilities at each decoding step. This can be used to see
        what other tokens the model considered.

        Attributes:
            candidates (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.LogprobsResult.Candidate]):
                The list of candidate tokens, sorted by log
                probability in descending order.
        """

        candidates: MutableSequence['LogprobsResult.Candidate'] = proto.RepeatedField(
            proto.MESSAGE,
            number=1,
            message='LogprobsResult.Candidate',
        )

    top_candidates: MutableSequence[TopCandidates] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message=TopCandidates,
    )
    chosen_candidates: MutableSequence[Candidate] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message=Candidate,
    )


class Segment(proto.Message):
    r"""A segment of the content.

    Attributes:
        part_index (int):
            Output only. The index of the ``Part`` object that this
            segment belongs to. This is useful for associating the
            segment with a specific part of the content.
        start_index (int):
            Output only. The start index of the segment in the ``Part``,
            measured in bytes. This marks the beginning of the segment
            and is inclusive, meaning the byte at this index is the
            first byte of the segment.
        end_index (int):
            Output only. The end index of the segment in the ``Part``,
            measured in bytes. This marks the end of the segment and is
            exclusive, meaning the segment includes content up to, but
            not including, the byte at this index.
        text (str):
            Output only. The text of the segment.
    """

    part_index: int = proto.Field(
        proto.INT32,
        number=1,
    )
    start_index: int = proto.Field(
        proto.INT32,
        number=2,
    )
    end_index: int = proto.Field(
        proto.INT32,
        number=3,
    )
    text: str = proto.Field(
        proto.STRING,
        number=4,
    )


class GroundingChunk(proto.Message):
    r"""A piece of evidence that supports a claim made by the model.

    This is used to show a citation for a claim made by the model. When
    grounding is enabled, the model returns a ``GroundingChunk`` that
    contains a reference to the source of the information.

    This message has `oneof`_ fields (mutually exclusive fields).
    For each oneof, at most one member field can be set at the same time.
    Setting any member of the oneof automatically clears all other
    members.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        web (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GroundingChunk.Web):
            A grounding chunk from a web page, typically from Google
            Search. See the ``Web`` message for details.

            This field is a member of `oneof`_ ``chunk_type``.
        retrieved_context (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GroundingChunk.RetrievedContext):
            A grounding chunk from a data source retrieved by a
            retrieval tool, such as Vertex AI Search. See the
            ``RetrievedContext`` message for details

            This field is a member of `oneof`_ ``chunk_type``.
        maps (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GroundingChunk.Maps):
            A grounding chunk from Google Maps. See the ``Maps`` message
            for details.

            This field is a member of `oneof`_ ``chunk_type``.
    """

    class Web(proto.Message):
        r"""A ``Web`` chunk is a piece of evidence that comes from a web page.
        It contains the URI of the web page, the title of the page, and the
        domain of the page. This is used to provide the user with a link to
        the source of the information.


        .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

        Attributes:
            uri (str):
                The URI of the web page that contains the
                evidence.

                This field is a member of `oneof`_ ``_uri``.
            title (str):
                The title of the web page that contains the
                evidence.

                This field is a member of `oneof`_ ``_title``.
            domain (str):
                The domain of the web page that contains the
                evidence. This can be used to filter out
                low-quality sources.

                This field is a member of `oneof`_ ``_domain``.
        """

        uri: str = proto.Field(
            proto.STRING,
            number=1,
            optional=True,
        )
        title: str = proto.Field(
            proto.STRING,
            number=2,
            optional=True,
        )
        domain: str = proto.Field(
            proto.STRING,
            number=3,
            optional=True,
        )

    class RetrievedContext(proto.Message):
        r"""Context retrieved from a data source to ground the model's
        response. This is used when a retrieval tool fetches information
        from a user-provided corpus or a public dataset.


        .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

        Attributes:
            rag_chunk (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.RagChunk):
                Additional context for a Retrieval-Augmented
                Generation (RAG) retrieval result. This is
                populated only when the RAG retrieval tool is
                used.

                This field is a member of `oneof`_ ``context_details``.
            uri (str):
                The URI of the retrieved data source.

                This field is a member of `oneof`_ ``_uri``.
            title (str):
                The title of the retrieved data source.

                This field is a member of `oneof`_ ``_title``.
            text (str):
                The content of the retrieved data source.

                This field is a member of `oneof`_ ``_text``.
            document_name (str):
                Output only. The full resource name of the referenced Vertex
                AI Search document. This is used to identify the specific
                document that was retrieved. The format is
                ``projects/{project}/locations/{location}/collections/{collection}/dataStores/{data_store}/branches/{branch}/documents/{document}``.

                This field is a member of `oneof`_ ``_document_name``.
        """

        rag_chunk: vertex_rag_data.RagChunk = proto.Field(
            proto.MESSAGE,
            number=4,
            oneof='context_details',
            message=vertex_rag_data.RagChunk,
        )
        uri: str = proto.Field(
            proto.STRING,
            number=1,
            optional=True,
        )
        title: str = proto.Field(
            proto.STRING,
            number=2,
            optional=True,
        )
        text: str = proto.Field(
            proto.STRING,
            number=3,
            optional=True,
        )
        document_name: str = proto.Field(
            proto.STRING,
            number=6,
            optional=True,
        )

    class Maps(proto.Message):
        r"""A ``Maps`` chunk is a piece of evidence that comes from Google Maps.
        It contains information about a place, such as its name, address,
        and reviews. This is used to provide the user with rich,
        location-based information.


        .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

        Attributes:
            uri (str):
                The URI of the place.

                This field is a member of `oneof`_ ``_uri``.
            title (str):
                The title of the place.

                This field is a member of `oneof`_ ``_title``.
            text (str):
                The text of the place answer.

                This field is a member of `oneof`_ ``_text``.
            place_id (str):
                This Place's resource name, in ``places/{place_id}`` format.
                This can be used to look up the place in the Google Maps
                API.

                This field is a member of `oneof`_ ``_place_id``.
            place_answer_sources (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GroundingChunk.Maps.PlaceAnswerSources):
                The sources that were used to generate the
                place answer. This includes review snippets and
                photos that were used to generate the answer, as
                well as URIs to flag content.
        """

        class PlaceAnswerSources(proto.Message):
            r"""The sources that were used to generate the place answer. This
            includes review snippets and photos that were used to generate
            the answer, as well as URIs to flag content.

            Attributes:
                review_snippets (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GroundingChunk.Maps.PlaceAnswerSources.ReviewSnippet]):
                    Snippets of reviews that were used to
                    generate the answer.
            """

            class ReviewSnippet(proto.Message):
                r"""A review snippet that is used to generate the answer.

                Attributes:
                    review_id (str):
                        The ID of the review that is being
                        referenced.
                    google_maps_uri (str):
                        A link to show the review on Google Maps.
                    title (str):
                        The title of the review.
                """

                review_id: str = proto.Field(
                    proto.STRING,
                    number=1,
                )
                google_maps_uri: str = proto.Field(
                    proto.STRING,
                    number=7,
                )
                title: str = proto.Field(
                    proto.STRING,
                    number=8,
                )

            review_snippets: MutableSequence['GroundingChunk.Maps.PlaceAnswerSources.ReviewSnippet'] = proto.RepeatedField(
                proto.MESSAGE,
                number=1,
                message='GroundingChunk.Maps.PlaceAnswerSources.ReviewSnippet',
            )

        uri: str = proto.Field(
            proto.STRING,
            number=1,
            optional=True,
        )
        title: str = proto.Field(
            proto.STRING,
            number=2,
            optional=True,
        )
        text: str = proto.Field(
            proto.STRING,
            number=3,
            optional=True,
        )
        place_id: str = proto.Field(
            proto.STRING,
            number=4,
            optional=True,
        )
        place_answer_sources: 'GroundingChunk.Maps.PlaceAnswerSources' = proto.Field(
            proto.MESSAGE,
            number=5,
            message='GroundingChunk.Maps.PlaceAnswerSources',
        )

    web: Web = proto.Field(
        proto.MESSAGE,
        number=1,
        oneof='chunk_type',
        message=Web,
    )
    retrieved_context: RetrievedContext = proto.Field(
        proto.MESSAGE,
        number=2,
        oneof='chunk_type',
        message=RetrievedContext,
    )
    maps: Maps = proto.Field(
        proto.MESSAGE,
        number=3,
        oneof='chunk_type',
        message=Maps,
    )


class GroundingSupport(proto.Message):
    r"""A collection of supporting references for a segment of the
    model's response.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        segment (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.Segment):
            The content segment that this support message
            applies to.

            This field is a member of `oneof`_ ``_segment``.
        grounding_chunk_indices (MutableSequence[int]):
            A list of indices into the ``grounding_chunks`` field of the
            ``GroundingMetadata`` message. These indices specify which
            grounding chunks support the claim made in the content
            segment.

            For example, if this field has the values ``[1, 3]``, it
            means that ``grounding_chunks[1]`` and
            ``grounding_chunks[3]`` are the sources for the claim in the
            content segment.
        confidence_scores (MutableSequence[float]):
            The confidence scores for the support references. This list
            is parallel to the ``grounding_chunk_indices`` list. A score
            is a value between 0.0 and 1.0, with a higher score
            indicating a higher confidence that the reference supports
            the claim.

            For Gemini 2.0 and before, this list has the same size as
            ``grounding_chunk_indices``. For Gemini 2.5 and later, this
            list is empty and should be ignored.
    """

    segment: 'Segment' = proto.Field(
        proto.MESSAGE,
        number=1,
        optional=True,
        message='Segment',
    )
    grounding_chunk_indices: MutableSequence[int] = proto.RepeatedField(
        proto.INT32,
        number=2,
    )
    confidence_scores: MutableSequence[float] = proto.RepeatedField(
        proto.FLOAT,
        number=3,
    )


class GroundingMetadata(proto.Message):
    r"""Information about the sources that support the content of a
    response.
    When grounding is enabled, the model returns citations for
    claims in the response. This object contains the retrieved
    sources.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        web_search_queries (MutableSequence[str]):
            Optional. The web search queries that were
            used to generate the content. This field is
            populated only when the grounding source is
            Google Search.
        search_entry_point (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.SearchEntryPoint):
            Optional. A web search entry point that can
            be used to display search results. This field is
            populated only when the grounding source is
            Google Search.

            This field is a member of `oneof`_ ``_search_entry_point``.
        grounding_chunks (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GroundingChunk]):
            A list of supporting references retrieved
            from the grounding source. This field is
            populated when the grounding source is Google
            Search, Vertex AI Search, or Google Maps.
        grounding_supports (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GroundingSupport]):
            Optional. A list of grounding supports that
            connect the generated content to the grounding
            chunks. This field is populated when the
            grounding source is Google Search or Vertex AI
            Search.
        retrieval_metadata (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.RetrievalMetadata):
            Optional. Output only. Metadata related to
            the retrieval grounding source.

            This field is a member of `oneof`_ ``_retrieval_metadata``.
        google_maps_widget_context_token (str):
            Optional. Output only. A token that can be
            used to render a Google Maps widget with the
            contextual data. This field is populated only
            when the grounding source is Google Maps.

            This field is a member of `oneof`_ ``_google_maps_widget_context_token``.
        source_flagging_uris (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.GroundingMetadata.SourceFlaggingUri]):
            Optional. Output only. A list of URIs that
            can be used to flag a place or review for
            inappropriate content. This field is populated
            only when the grounding source is Google Maps.
    """

    class SourceFlaggingUri(proto.Message):
        r"""A URI that can be used to flag a place or review for
        inappropriate content. This is populated only when the grounding
        source is Google Maps.

        Attributes:
            source_id (str):
                The ID of the place or review.
            flag_content_uri (str):
                The URI that can be used to flag the content.
        """

        source_id: str = proto.Field(
            proto.STRING,
            number=1,
        )
        flag_content_uri: str = proto.Field(
            proto.STRING,
            number=2,
        )

    web_search_queries: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=1,
    )
    search_entry_point: 'SearchEntryPoint' = proto.Field(
        proto.MESSAGE,
        number=4,
        optional=True,
        message='SearchEntryPoint',
    )
    grounding_chunks: MutableSequence['GroundingChunk'] = proto.RepeatedField(
        proto.MESSAGE,
        number=5,
        message='GroundingChunk',
    )
    grounding_supports: MutableSequence['GroundingSupport'] = proto.RepeatedField(
        proto.MESSAGE,
        number=6,
        message='GroundingSupport',
    )
    retrieval_metadata: 'RetrievalMetadata' = proto.Field(
        proto.MESSAGE,
        number=7,
        optional=True,
        message='RetrievalMetadata',
    )
    google_maps_widget_context_token: str = proto.Field(
        proto.STRING,
        number=8,
        optional=True,
    )
    source_flagging_uris: MutableSequence[SourceFlaggingUri] = proto.RepeatedField(
        proto.MESSAGE,
        number=10,
        message=SourceFlaggingUri,
    )


class SearchEntryPoint(proto.Message):
    r"""An entry point for displaying Google Search results.

    A ``SearchEntryPoint`` is populated when the grounding source for a
    model's response is Google Search. It provides information that you
    can use to display the search results in your application.

    Attributes:
        rendered_content (str):
            Optional. An HTML snippet that can be
            embedded in a web page or an application's
            webview. This snippet displays a search result,
            including the title, URL, and a brief
            description of the search result.
        sdk_blob (bytes):
            Optional. A base64-encoded JSON object that
            contains a list of search queries and their
            corresponding search URLs. This information can
            be used to build a custom search UI.
    """

    rendered_content: str = proto.Field(
        proto.STRING,
        number=1,
    )
    sdk_blob: bytes = proto.Field(
        proto.BYTES,
        number=2,
    )


class RetrievalMetadata(proto.Message):
    r"""Metadata related to the retrieval grounding source. This is part of
    the ``GroundingMetadata`` returned when grounding is enabled.

    Attributes:
        google_search_dynamic_retrieval_score (float):
            Optional. A score indicating how likely it is that a Google
            Search query could help answer the prompt. The score is in
            the range of ``[0, 1]``. A score of 1 means the model is
            confident that a search will be helpful, and 0 means it is
            not. This score is populated only when Google Search
            grounding and dynamic retrieval are enabled. The score is
            used to determine whether to trigger a search.
    """

    google_search_dynamic_retrieval_score: float = proto.Field(
        proto.FLOAT,
        number=2,
    )


class ModelArmorConfig(proto.Message):
    r"""Configuration for Model Armor.

    Model Armor is a Google Cloud service that provides safety and
    security filtering for prompts and responses. It helps protect
    your AI applications from risks such as harmful content,
    sensitive data leakage, and prompt injection attacks.

    Attributes:
        prompt_template_name (str):
            Optional. The resource name of the Model Armor template to
            use for prompt screening.

            A Model Armor template is a set of customized filters and
            thresholds that define how Model Armor screens content. If
            specified, Model Armor will use this template to check the
            user's prompt for safety and security risks before it is
            sent to the model.

            The name must be in the format
            ``projects/{project}/locations/{location}/templates/{template}``.
        response_template_name (str):
            Optional. The resource name of the Model Armor template to
            use for response screening.

            A Model Armor template is a set of customized filters and
            thresholds that define how Model Armor screens content. If
            specified, Model Armor will use this template to check the
            model's response for safety and security risks before it is
            returned to the user.

            The name must be in the format
            ``projects/{project}/locations/{location}/templates/{template}``.
    """

    prompt_template_name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    response_template_name: str = proto.Field(
        proto.STRING,
        number=2,
    )


class ModalityTokenCount(proto.Message):
    r"""Represents a breakdown of token usage by modality.

    This message is used in
    [CountTokensResponse][google.cloud.aiplatform.master.CountTokensResponse]
    and
    [GenerateContentResponse.UsageMetadata][google.cloud.aiplatform.v1.GenerateContentResponse.UsageMetadata]
    to provide a detailed view of how many tokens are used by each
    modality (e.g., text, image, video) in a request. This is
    particularly useful for multimodal models, allowing you to track and
    manage token consumption for billing and quota purposes.

    Attributes:
        modality (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.Modality):
            The modality that this token count applies
            to.
        token_count (int):
            The number of tokens counted for this
            modality.
    """

    modality: 'Modality' = proto.Field(
        proto.ENUM,
        number=1,
        enum='Modality',
    )
    token_count: int = proto.Field(
        proto.INT32,
        number=2,
    )


__all__ = tuple(sorted(__protobuf__.manifest))
