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
"""Flags for speech commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs


SPEAKER_COUNT_MAX_VALUE = 6
SPEAKER_COUNT_MIN_VALUE = 1
ALTERNATIVES_MAX_VALUE = 30
ALTERNATIVES_MIN_VALUE = 1
AUDIO_CHANNEL_COUNT_MAX_VALUE = 8
AUDIO_CHANNEL_COUNT_MIN_VALUE = 1
SAMPLE_RATE_MAX_VALUE = 48000
SAMPLE_RATE_MIN_VALUE = 8000


def AddRecognizerArgToParser(parser):
  """Sets up an argument for the recognizer resource."""
  resource_data = yaml_data.ResourceYAMLData.FromPath('ml.speech.recognizer')
  resource_spec = concepts.ResourceSpec.FromYaml(
      resource_data.GetData(), api_version='v2'
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name='recognizer',
      concept_spec=resource_spec,
      required=True,
      group_help='recognizer.',
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddLocationArgToParser(parser):
  """Parses location flag."""
  location_data = yaml_data.ResourceYAMLData.FromPath('ml.speech.location')
  resource_spec = concepts.ResourceSpec.FromYaml(location_data.GetData())
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name='--location',
      concept_spec=resource_spec,
      required=True,
      group_help='location.',
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddLocationPositionalArgToParser(parser):
  """Parses location when there is no flag."""
  location_data = yaml_data.ResourceYAMLData.FromPath('ml.speech.location')
  resource_spec = concepts.ResourceSpec.FromYaml(location_data.GetData())
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name='location',
      concept_spec=resource_spec,
      required=True,
      group_help='location.',
  )
  return concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddAllFlagsToParser(
    parser, require_base_recognizer_attributes=False, use_store_true=False
):
  """Parses all flags for v2 STT API."""
  AddRecognizerArgToParser(parser)
  AddAsyncFlagToParser(parser)
  parser.add_argument(
      '--display-name',
      help="""\
      Name of this recognizer as it appears in UIs.
      """,
  )
  AddBaseRecognizerAttributeFlagsToParser(
      parser, required=require_base_recognizer_attributes
  )
  AddFeatureFlagsToParser(parser, use_store_true)
  AddDecodingConfigFlagsToParser(parser)


def AddRecognizeRequestFlagsToParser(parser, add_async_flag=False):
  """Parses all flags for v2 STT API for command run-batch."""
  AddRecognizerArgToParser(parser)
  parser.add_argument(
      '--audio',
      required=True,
      help=(
          'Location of the audio file to transcribe. '
          'Must be a audio data bytes, local file, or Google Cloud Storage URL '
          '(in the format gs://bucket/object).'
      ),
  )
  AddFeatureFlagsToParser(parser)
  AddDecodingConfigFlagsToParser(parser)
  AddBaseRecognizerAttributeFlagsToParser(parser)
  parser.add_argument(
      '--hint-phrases',
      metavar='PHRASE',
      type=arg_parsers.ArgList(),
      help="""\
        A list of strings containing word and phrase "hints" so that the '
        'speech recognition is more likely to recognize them. This can be '
        'used to improve the accuracy for specific words and phrases, '
        'for example, if specific commands are typically spoken by '
        'the user. This can also be used to add additional words to the '
        'vocabulary of the recognizer. '
        'See https://cloud.google.com/speech/limits#content.
      """,
  )
  parser.add_argument(
      '--hint-phrase-sets',
      metavar='PHRASE_SET',
      type=arg_parsers.ArgList(),
      help="""\
        A list of phrase set resource names to use for speech recognition.
      """,
  )
  parser.add_argument(
      '--hint-boost',
      type=arg_parsers.BoundedFloat(1, 20),
      help="""\
        Boost value for the phrases passed to --phrases.
        Can have a value between 1 and 20.
      """,
  )

  if add_async_flag:
    AddAsyncFlagToParser(parser)


def AddAsyncFlagToParser(parser):
  """Adds async flag to parser."""
  base.ASYNC_FLAG.AddToParser(parser)
  base.ASYNC_FLAG.SetDefault(parser, False)


def AddBaseRecognizerAttributeFlagsToParser(parser, required=False):
  """Adds base recognizer attribute flags to parser."""
  parser.add_argument(
      '--model',
      required=required,
      help="""\
          Which model to use for recognition requests.
          Select the model best suited to your domain to get best results.
          Guidance for choosing which model to use can be found in the
          [Transcription Models Documentation](https://cloud.google.com/speech-to-text/v2/docs/transcription-model)
          and the models supported in each region can be found in the
          [Table Of Supported Models](https://cloud.google.com/speech-to-text/v2/docs/speech-to-text-supported-languages).
          """,
  )
  parser.add_argument(
      '--language-codes',
      metavar='LANGUAGE_CODE',
      required=required,
      type=arg_parsers.ArgList(),
      help="""\
          Language code is one of `en-US`, `en-GB`, `fr-FR`.
          Check [documentation](https://cloud.google.com/speech-to-text/docs/multiple-languages)
          for using more than one language code.
          """,
  )


def AddDecodingConfigFlagsToParser(parser):
  """Adds decoding config flags to parser."""
  decoding_config_group = parser.add_group(help='Encoding format')
  decoding_config_group.add_argument(
      '--encoding',
      help="""\
          Encoding format of the provided audio.
          For headerless formats, must be set to `LINEAR16`, `MULAW,` or `ALAW`.
          For other formats, set to `AUTO`. Overrides the recognizer
          configuration if present, else uses recognizer encoding.
          """,
  )
  sample_rate_help = (
      'Sample rate in Hertz of the audio data sent for recognition. '
      'Required if --encoding flag is specified and is not AUTO. '
      'Must be set to a value between {} and {}.'.format(
          SAMPLE_RATE_MIN_VALUE, SAMPLE_RATE_MAX_VALUE
      )
  )
  decoding_config_group.add_argument(
      '--sample-rate',
      type=arg_parsers.BoundedInt(SAMPLE_RATE_MIN_VALUE, SAMPLE_RATE_MAX_VALUE),
      help=sample_rate_help,
  )
  audio_channel_count_help = (
      'Number of channels present in the audio data sent for recognition. '
      'Required if --encoding flag is specified and is not AUTO. '
      'Must be set to a value between {} and {}.'.format(
          AUDIO_CHANNEL_COUNT_MIN_VALUE, AUDIO_CHANNEL_COUNT_MAX_VALUE
      )
  )
  decoding_config_group.add_argument(
      '--audio-channel-count',
      type=arg_parsers.BoundedInt(
          AUDIO_CHANNEL_COUNT_MIN_VALUE, AUDIO_CHANNEL_COUNT_MAX_VALUE
      ),
      help=audio_channel_count_help,
  )


def AddFeatureFlagsToParser(parser, use_store_true=False):
  """Adds feature flags to parser."""
  features_group = parser.add_group(help='ASR Features')
  speaker_diarization_group = features_group.add_group(
      help='Speaker Diarization'
  )
  features_group.add_argument(
      '--profanity-filter',
      action='store_true'
      if use_store_true
      else arg_parsers.StoreTrueFalseAction,
      help="""\
      If set, the server will censor profanities.
      """,
  )
  features_group.add_argument(
      '--enable-word-time-offsets',
      action='store_true'
      if use_store_true
      else arg_parsers.StoreTrueFalseAction,
      help="""\
      If set, the top result includes a list of words and their timestamps.
      """,
  )
  features_group.add_argument(
      '--enable-word-confidence',
      action='store_true'
      if use_store_true
      else arg_parsers.StoreTrueFalseAction,
      help="""\
      If set, the top result includes a list of words and the confidence for
      those words.
      """,
  )
  features_group.add_argument(
      '--enable-automatic-punctuation',
      action='store_true'
      if use_store_true
      else arg_parsers.StoreTrueFalseAction,
      help="""\
      If set, adds punctuation to recognition result hypotheses.
      """,
  )
  features_group.add_argument(
      '--enable-spoken-punctuation',
      action='store_true'
      if use_store_true
      else arg_parsers.StoreTrueFalseAction,
      help="""\
      If set, replaces spoken punctuation with the corresponding symbols in the request.
      """,
  )
  features_group.add_argument(
      '--enable-spoken-emojis',
      action='store_true'
      if use_store_true
      else arg_parsers.StoreTrueFalseAction,
      help="""\
      If set, adds spoken emoji formatting.
      """,
  )
  min_speaker_count_help = (
      'Minimum number of speakers in the conversation. Must be less than or'
      ' equal to --max-speaker-count. Must be set to a value between {} and {}.'
      .format(SPEAKER_COUNT_MIN_VALUE, SPEAKER_COUNT_MAX_VALUE)
  )
  max_speaker_count_help = (
      'Maximum number of speakers in the conversation. Must be greater than or'
      ' equal to --min-speaker-count. Must be set to a value between {} and {}.'
      .format(SPEAKER_COUNT_MIN_VALUE, SPEAKER_COUNT_MAX_VALUE)
  )
  speaker_diarization_group.add_argument(
      '--min-speaker-count',
      required=True,
      type=arg_parsers.BoundedInt(
          SPEAKER_COUNT_MIN_VALUE, SPEAKER_COUNT_MAX_VALUE
      ),
      help=min_speaker_count_help,
  )
  speaker_diarization_group.add_argument(
      '--max-speaker-count',
      required=True,
      type=arg_parsers.BoundedInt(
          SPEAKER_COUNT_MIN_VALUE, SPEAKER_COUNT_MAX_VALUE
      ),
      help=max_speaker_count_help,
  )
  features_group.add_argument(
      '--separate-channel-recognition',
      action='store_true'
      if use_store_true
      else arg_parsers.StoreTrueFalseAction,
      help="""\
        Mode for recognizing multi-channel audio using Separate Channel Recognition.
        When set, the service will recognize each channel independently.
        """,
  )
  max_alternatives_help = (
      'Maximum number of recognition hypotheses to be returned. Must be set to'
      ' a value between {} and {}.'.format(
          ALTERNATIVES_MIN_VALUE, ALTERNATIVES_MAX_VALUE
      )
  )
  features_group.add_argument(
      '--max-alternatives',
      type=arg_parsers.BoundedInt(
          ALTERNATIVES_MIN_VALUE, ALTERNATIVES_MAX_VALUE
      ),
      help=max_alternatives_help,
  )
