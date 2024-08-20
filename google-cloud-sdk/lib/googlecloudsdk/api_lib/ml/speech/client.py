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
"""Speech-to-text V2 client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib
import os

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import exceptions
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.command_lib.ml.speech import flag_validations
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import files
from six.moves import urllib


_API_NAME = 'speech'
_API_VERSION = 'v2'


@contextlib.contextmanager
def _OverrideEndpoint(override):
  """Context manager to override an API's endpoint overrides for a while."""
  endpoint_property = getattr(
      properties.VALUES.api_endpoint_overrides, _API_NAME
  )
  old_endpoint = endpoint_property.Get()
  try:
    endpoint_property.Set(override)
    yield
  finally:
    endpoint_property.Set(old_endpoint)


class SpeechV2Client(object):
  """Speech V2 API client wrappers."""

  def __init__(self):
    client_class = apis.GetClientClass(_API_NAME, _API_VERSION)
    self._net_loc = urllib.parse.urlsplit(client_class.BASE_URL).netloc
    messages = apis.GetMessagesModule(_API_NAME, _API_VERSION)

    self._resource_parser = resources.Registry()
    self._resource_parser.RegisterApiByName(_API_NAME, _API_VERSION)
    self._encoding_to_message = {
        'LINEAR16': (
            messages.ExplicitDecodingConfig.EncodingValueValuesEnum.LINEAR16
        ),
        'MULAW': messages.ExplicitDecodingConfig.EncodingValueValuesEnum.MULAW,
        'ALAW': messages.ExplicitDecodingConfig.EncodingValueValuesEnum.ALAW,
    }
    self._messages = messages

  def _GetClientForLocation(self, location):
    with _OverrideEndpoint('https://{}-{}/'.format(location, self._net_loc)):
      return apis.GetClientInstance(_API_NAME, _API_VERSION)

  def _RecognizerServiceForLocation(self, location):
    return self._GetClientForLocation(location).projects_locations_recognizers

  def _OperationsServiceForLocation(self, location):
    return self._GetClientForLocation(location).projects_locations_operations

  def _LocationsServiceForLocation(self, location):
    return self._GetClientForLocation(location).projects_locations

  def CreateRecognizer(
      self,
      resource,
      display_name,
      model,
      language_codes,
      recognition_config,
  ):
    """Call API CreateRecognizer method with provided arguments."""
    recognizer = self._messages.Recognizer(displayName=display_name)

    recognizer.model = model
    recognizer.languageCodes = language_codes

    recognizer.defaultRecognitionConfig = recognition_config

    request = self._messages.SpeechProjectsLocationsRecognizersCreateRequest(
        parent=resource.Parent(
            parent_collection='speech.projects.locations'
        ).RelativeName(),
        recognizerId=resource.Name(),
        recognizer=recognizer,
    )
    return self._RecognizerServiceForLocation(
        location=resource.Parent().Name()
    ).Create(request)

  def GetRecognizer(self, resource):
    request = self._messages.SpeechProjectsLocationsRecognizersGetRequest(
        name=resource.RelativeName()
    )
    return self._RecognizerServiceForLocation(
        location=resource.Parent().Name()
    ).Get(request)

  def DeleteRecognizer(self, resource):
    request = self._messages.SpeechProjectsLocationsRecognizersDeleteRequest(
        name=resource.RelativeName()
    )
    return self._RecognizerServiceForLocation(
        location=resource.Parent().Name()
    ).Delete(request)

  def ListRecognizers(self, location_resource, limit=None, page_size=None):
    request = self._messages.SpeechProjectsLocationsRecognizersListRequest(
        parent=location_resource.RelativeName()
    )
    if page_size:
      request.page_size = page_size
    return list_pager.YieldFromList(
        self._RecognizerServiceForLocation(location_resource.Name()),
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='recognizers',
    )

  def UpdateRecognizer(
      self,
      resource,
      display_name,
      model,
      language_codes,
      recognition_config,
      update_mask,
  ):
    """Call API UpdateRecognizer method with provided arguments."""
    recognizer = self._messages.Recognizer()

    if display_name is not None:
      recognizer.displayName = display_name
      update_mask.append('display_name')
    if model is not None:
      recognizer.model = model
      update_mask.append('model')
    if language_codes is not None:
      recognizer.languageCodes = language_codes
      update_mask.append('language_codes')

    recognizer.defaultRecognitionConfig = recognition_config

    request = self._messages.SpeechProjectsLocationsRecognizersPatchRequest(
        name=resource.RelativeName(),
        recognizer=recognizer,
        updateMask=','.join(update_mask),
    )
    return self._RecognizerServiceForLocation(
        location=resource.Parent().Name()
    ).Patch(request)

  def RunShort(
      self,
      resource,
      audio,
      recognition_config,
      update_mask,
  ):
    """Call API Recognize method with provided arguments."""
    recognize_req = self._messages.RecognizeRequest()
    if os.path.isfile(audio):
      recognize_req.content = files.ReadBinaryFileContents(audio)
    elif storage_util.ObjectReference.IsStorageUrl(audio):
      recognize_req.uri = audio

    recognizer_service = self._RecognizerServiceForLocation(
        location=resource.Parent().Name()
    )

    recognize_req.config = recognition_config

    recognize_req.configMask = ','.join(update_mask)

    request = self._messages.SpeechProjectsLocationsRecognizersRecognizeRequest(
        recognizeRequest=recognize_req,
        recognizer=resource.RelativeName(),
    )
    return recognizer_service.Recognize(request)

  def RunBatch(
      self,
      resource,
      audio,
      recognition_config,
      update_mask,
  ):
    """Call API Recognize method with provided arguments in batch mode."""
    batch_audio_metadata = self._messages.BatchRecognizeFileMetadata(uri=audio)
    recognize_req = self._messages.BatchRecognizeRequest(
        recognizer=resource.RelativeName(),
        files=[batch_audio_metadata],
    )

    recognizer_service = self._RecognizerServiceForLocation(
        location=resource.Parent().Name()
    )

    recognize_req.config = recognition_config

    recognize_req.recognitionOutputConfig = (
        self._messages.RecognitionOutputConfig(
            inlineResponseConfig=self._messages.InlineOutputConfig()
        )
    )

    recognize_req.configMask = ','.join(update_mask)

    return recognizer_service.BatchRecognize(recognize_req)

  def GetOperationRef(self, operation):
    """Converts an Operation to a Resource."""
    return self._resource_parser.ParseRelativeName(
        operation.name, 'speech.projects.locations.operations'
    )

  def WaitForRecognizerOperation(self, location, operation_ref, message):
    """Waits for a Recognizer operation to complete.

    Polls the Speech Operation service until the operation completes, fails, or
      max_wait_ms elapses.

    Args:
      location: The location of the resource.
      operation_ref: A Resource created by GetOperationRef describing the
        Operation.
      message: The message to display to the user while they wait.

    Returns:
      An Endpoint entity.
    """
    poller = waiter.CloudOperationPoller(
        result_service=self._RecognizerServiceForLocation(location),
        operation_service=self._OperationsServiceForLocation(location),
    )

    return waiter.WaitFor(
        poller=poller,
        operation_ref=operation_ref,
        message=message,
        pre_start_sleep_ms=100,
        max_wait_ms=20000,
    )

  def WaitForBatchRecognizeOperation(self, location, operation_ref, message):
    """Waits for a Batch Recognize operation to complete.

    Polls the Speech Operation service until the operation completes, fails, or
      max_wait_ms elapses.

    Args:
      location: The location of the resource.
      operation_ref: A Resource created by GetOperationRef describing the
        Operation.
      message: The message to display to the user while they wait.

    Returns:
      An Endpoint entity.
    """
    poller = waiter.CloudOperationPollerNoResources(
        self._OperationsServiceForLocation(location),
        lambda x: x,
    )

    return waiter.WaitFor(
        poller,
        operation_ref,
        message=message,
        wait_ceiling_ms=86400000,
    )

  def GetLocation(self, location_resource):
    request = self._messages.SpeechProjectsLocationsGetRequest(
        name=location_resource.RelativeName()
    )
    return self._LocationsServiceForLocation(
        location=location_resource.Name()
    ).Get(request)

  def ListLocations(self, filter_str=None, limit=None, page_size=None):
    request = self._messages.SpeechProjectsLocationsListRequest(
        name=properties.VALUES.core.project.Get()
    )
    if filter_str:
      request.filter = filter_str
    if page_size:
      request.page_size = page_size
    return list_pager.YieldFromList(
        self._LocationsServiceForLocation('global'),
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='locations',
    )

  def InitializeRecognitionConfig(
      self, model=None, language_codes=None, update_mask=None
  ):
    """creates a recognition config object and initializes it with model and language codes."""
    recognition_config = self._messages.RecognitionConfig()
    if model is not None:
      recognition_config.model = model
    if language_codes is not None:
      recognition_config.languageCodes = language_codes

    if update_mask is None:
      return recognition_config, update_mask

    if model is not None:
      update_mask.append('model')
    if language_codes is not None:
      update_mask.append('language_codes')
    return recognition_config, update_mask

  def InitializeDecodingConfigFromArgs(
      self,
      recognition_config,
      args,
      default_to_auto_decoding_config=False,
      update_mask=None,
  ):

    return self._InitializeDecodingConfigRecognizerCommand(
        recognition_config,
        args.encoding,
        args.sample_rate,
        args.audio_channel_count,
        default_to_auto_decoding_config=default_to_auto_decoding_config,
        update_mask=update_mask,
    )

  def _InitializeDecodingConfigRecognizerCommand(
      self,
      recognition_config,
      encoding,
      sample_rate,
      audio_channel_count,
      default_to_auto_decoding_config=False,
      update_mask=None,
  ):
    """Initializes encoding type based on auto (or explicit decoding option), sample rate and audio channel count."""
    if encoding is not None:
      if encoding == 'AUTO':
        recognition_config.autoDecodingConfig = (
            self._messages.AutoDetectDecodingConfig()
        )

      elif encoding in flag_validations.EXPLICIT_ENCODING_OPTIONS:
        recognition_config.explicitDecodingConfig = (
            self._messages.ExplicitDecodingConfig()
        )

        recognition_config.explicitDecodingConfig.encoding = (
            self._encoding_to_message[encoding]
        )

        if sample_rate is not None:
          recognition_config.explicitDecodingConfig.sampleRateHertz = (
              sample_rate
          )

        if audio_channel_count is not None:
          recognition_config.explicitDecodingConfig.audioChannelCount = (
              audio_channel_count
          )
      else:
        raise exceptions.InvalidArgumentException(
            '--encoding',
            '[--encoding] must be set to LINEAR16, MULAW, ALAW, or AUTO.',
        )
    elif default_to_auto_decoding_config:
      recognition_config.autoDecodingConfig = (
          self._messages.AutoDetectDecodingConfig()
      )

    if update_mask is None:
      return recognition_config, update_mask

    if encoding == 'AUTO':
      update_mask.append('auto_decoding_config')
    elif encoding in flag_validations.EXPLICIT_ENCODING_OPTIONS:
      update_mask.append('explicit_decoding_config')
    elif default_to_auto_decoding_config:
      update_mask.append('auto_decoding_config')
    if sample_rate is not None:
      if recognition_config.explicitDecodingConfig is None:
        recognition_config.explicitDecodingConfig = (
            self._messages.ExplicitDecodingConfig()
        )
      recognition_config.explicitDecodingConfig.sampleRateHertz = sample_rate
      update_mask.append('explicit_decoding_config.sample_rate_hertz')
    if audio_channel_count is not None:
      if recognition_config.explicitDecodingConfig is None:
        recognition_config.explicitDecodingConfig = (
            self._messages.ExplicitDecodingConfig()
        )
      recognition_config.explicitDecodingConfig.audioChannelCount = (
          audio_channel_count
      )
      update_mask.append('explicit_decoding_config.audio_channel_count')

    return recognition_config, update_mask

  def InitializeAdaptationConfigFromArgs(
      self,
      args,
      update_mask=None,
  ):
    """Initializes PhraseSets based on hints."""
    return self._InitializeAdaptationConfigRecognizeRequest(
        args.hint_phrases, args.hint_phrase_sets, args.hint_boost, update_mask
    )

  def _InitializeAdaptationConfigRecognizeRequest(
      self, hint_phrases, hint_phrase_sets, hint_boost=5.0, update_mask=None
  ):
    """Initializes PhraseSets based on phrases and phrase sets."""
    speech_adaptation_phrase_sets = []

    if hint_phrases:
      inline_phrase_set = self._messages.PhraseSet(
          phrases=[
              self._messages.Phrase(value=hint_phrase, boost=5.0)
              for hint_phrase in hint_phrases
          ],
          boost=hint_boost,
      )
      inline_adaptation_phrase_set = self._messages.AdaptationPhraseSet(
          inlinePhraseSet=inline_phrase_set
      )
      speech_adaptation_phrase_sets.append(inline_adaptation_phrase_set)

    if hint_phrase_sets:
      for hint_phrase_set in hint_phrase_sets:
        adaptation_phrase_set = self._messages.AdaptationPhraseSet(
            phraseSet=hint_phrase_set
        )
        speech_adaptation_phrase_sets.append(adaptation_phrase_set)

    speech_adaptation_config = self._messages.SpeechAdaptation(
        phraseSets=speech_adaptation_phrase_sets
    )

    if update_mask is not None:
      update_mask.append('adaptation')
    return speech_adaptation_config, update_mask

  def InitializeASRFeaturesFromArgs(
      self,
      args,
      update_mask=None,
  ):
    """Collects features from the provided arguments."""
    features_config = self._messages.RecognitionFeatures()
    inner_update_mask = []
    if args.profanity_filter is not None:
      features_config.profanityFilter = args.profanity_filter
      inner_update_mask.append('features.profanityFilter')

    if args.enable_word_time_offsets is not None:
      features_config.enableWordTimeOffsets = args.enable_word_time_offsets
      inner_update_mask.append('features.enableWordTimeOffsets')
    if args.enable_word_confidence is not None:
      features_config.enableWordConfidence = args.enable_word_confidence
      inner_update_mask.append('features.enableWordConfidence')
    if args.enable_automatic_punctuation is not None:
      features_config.enableAutomaticPunctuation = (
          args.enable_automatic_punctuation
      )
      inner_update_mask.append('features.enableAutomaticPunctuation')
    if args.enable_spoken_punctuation is not None:
      features_config.enableSpokenPunctuation = args.enable_spoken_punctuation
      inner_update_mask.append('features.enableSpokenPunctuation')
    if args.enable_spoken_emojis is not None:
      features_config.enableSpokenEmojis = args.enable_spoken_emojis
      inner_update_mask.append('features.enableSpokenEmojis')
    if (
        args.min_speaker_count is not None
        and args.max_speaker_count is not None
    ):
      features_config.diarizationConfig = (
          self._messages.SpeakerDiarizationConfig(
              minSpeakerCount=args.min_speaker_count,
              maxSpeakerCount=args.max_speaker_count,
          )
      )
      inner_update_mask.append('features.diarizationConfig.minSpeakerCount')
      inner_update_mask.append('features.diarizationConfig.maxSpeakerCount')
    if args.separate_channel_recognition:
      features_config.multiChannelMode = (
          self._messages.RecognitionFeatures.MultiChannelModeValueValuesEnum.SEPARATE_RECOGNITION_PER_CHANNEL
      )
      inner_update_mask.append('features.multiChannelMode')
    elif args.separate_channel_recognition is not None:
      features_config.multiChannelMode = (
          self._messages.RecognitionFeatures.MultiChannelModeValueValuesEnum.MULTI_CHANNEL_MODE_UNSPECIFIED
      )
      inner_update_mask.append('features.multiChannelMode')
    if args.max_alternatives is not None:
      features_config.maxAlternatives = args.max_alternatives
      inner_update_mask.append('features.maxAlternatives')

    if update_mask is not None:
      update_mask.extend(inner_update_mask)

    return features_config, update_mask
