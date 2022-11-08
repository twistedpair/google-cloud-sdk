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
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from six.moves import urllib

_API_NAME = 'speech'
_API_VERSION = 'v2'


@contextlib.contextmanager
def _OverrideEndpoint(override):
  """Context manager to override an API's endpoint overrides for a while."""
  endpoint_property = getattr(properties.VALUES.api_endpoint_overrides,
                              _API_NAME)
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
    self._messages = apis.GetMessagesModule(_API_NAME, _API_VERSION)

    self._resource_parser = resources.Registry()
    self._resource_parser.RegisterApiByName(_API_NAME, _API_VERSION)

  def _RecognizerServiceForLocation(self, location):
    with _OverrideEndpoint('https://{}-{}/'.format(location, self._net_loc)):
      client = apis.GetClientInstance(_API_NAME, _API_VERSION)
    return client.projects_locations_recognizers

  def _OperationsServiceForLocation(self, location):
    with _OverrideEndpoint('https://{}-{}/'.format(location, self._net_loc)):
      client = apis.GetClientInstance(_API_NAME, _API_VERSION)
    return client.projects_locations_operations

  def CreateRecognizer(self,
                       resource,
                       display_name,
                       model,
                       language_codes,
                       profanity_filter=False,
                       enable_word_time_offsets=False,
                       enable_word_confidence=False,
                       enable_automatic_punctuation=False,
                       enable_spoken_punctuation=False,
                       enable_spoken_emojis=False,
                       min_speaker_count=None,
                       max_speaker_count=None):
    """Call API CreateRecognizer method with provided arguments."""
    recognizer = self._messages.Recognizer(
        displayName=display_name, model=model, languageCodes=language_codes)
    recognizer.defaultRecognitionConfig = self._messages.RecognitionConfig()
    recognizer.defaultRecognitionConfig.features = (
        self._messages.RecognitionFeatures())
    recognizer.defaultRecognitionConfig.features.profanityFilter = (
        profanity_filter)
    recognizer.defaultRecognitionConfig.features.enableWordTimeOffsets = (
        enable_word_time_offsets)
    recognizer.defaultRecognitionConfig.features.enableWordConfidence = (
        enable_word_confidence)
    recognizer.defaultRecognitionConfig.features.enableAutomaticPunctuation = (
        enable_automatic_punctuation)
    recognizer.defaultRecognitionConfig.features.enableSpokenPunctuation = (
        enable_spoken_punctuation)
    recognizer.defaultRecognitionConfig.features.enableSpokenEmojis = (
        enable_spoken_emojis)

    if min_speaker_count is not None and max_speaker_count is not None:
      recognizer.defaultRecognitionConfig.features.diarizationConfig = self._messages.SpeakerDiarizationConfig(
      )
      recognizer.defaultRecognitionConfig.features.diarizationConfig.minSpeakerCount = min_speaker_count
      recognizer.defaultRecognitionConfig.features.diarizationConfig.maxSpeakerCount = max_speaker_count

    request = self._messages.SpeechProjectsLocationsRecognizersCreateRequest(
        parent=resource.Parent().RelativeName(),
        recognizerId=resource.Name(),
        recognizer=recognizer)
    return self._RecognizerServiceForLocation(
        location=resource.Parent().Name()).Create(request)

  def GetRecognizer(self, resource):
    request = self._messages.SpeechProjectsLocationsRecognizersGetRequest(
        name=resource.RelativeName())
    return self._RecognizerServiceForLocation(
        location=resource.Parent().Name()).Get(request)

  def DeleteRecognizer(self, resource):
    request = self._messages.SpeechProjectsLocationsRecognizersDeleteRequest(
        name=resource.RelativeName())
    return self._RecognizerServiceForLocation(
        location=resource.Parent().Name()).Delete(request)

  def ListRecognizers(self, location_resource, limit=None, page_size=None):
    request = self._messages.SpeechProjectsLocationsRecognizersListRequest(
        parent=location_resource.RelativeName())
    if page_size:
      request.page_size = page_size
    return list_pager.YieldFromList(
        self._RecognizerServiceForLocation(location_resource.Name()),
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='recognizers')

  def UpdateRecognizer(self,
                       resource,
                       display_name=None,
                       model=None,
                       language_codes=None,
                       profanity_filter=None,
                       enable_word_time_offsets=None,
                       enable_word_confidence=None,
                       enable_automatic_punctuation=None,
                       enable_spoken_punctuation=None,
                       enable_spoken_emojis=None,
                       min_speaker_count=None,
                       max_speaker_count=None):
    """Call API UpdateRecognizer method with provided arguments."""
    recognizer = self._messages.Recognizer()
    update_mask = []
    if display_name is not None:
      recognizer.displayName = display_name
      update_mask.append('display_name')
    if model is not None:
      recognizer.model = model
      update_mask.append('model')
    if language_codes is not None:
      recognizer.languageCodes = language_codes
      update_mask.append('language_codes')

    if recognizer.defaultRecognitionConfig is None:
      recognizer.defaultRecognitionConfig = self._messages.RecognitionConfig()
    if recognizer.defaultRecognitionConfig.features is None:
      recognizer.defaultRecognitionConfig.features = (
          self._messages.RecognitionFeatures())
    features = recognizer.defaultRecognitionConfig.features

    if profanity_filter is not None:
      features.profanityFilter = profanity_filter
      update_mask.append('default_recognition_config.features.profanity_filter')

    if enable_word_time_offsets is not None:
      features.enableWordTimeOffsets = enable_word_time_offsets
      update_mask.append(
          'default_recognition_config.features.enable_word_time_offsets')

    if enable_word_confidence is not None:
      features.enableWordConfidence = enable_word_confidence
      update_mask.append(
          'default_recognition_config.features.enable_word_confidence')

    if enable_automatic_punctuation is not None:
      features.enableAutomaticPunctuation = enable_automatic_punctuation
      update_mask.append(
          'default_recognition_config.features.enable_automatic_punctuation')

    if enable_spoken_punctuation is not None:
      features.enableSpokenPunctuation = enable_spoken_punctuation
      update_mask.append(
          'default_recognition_config.features.enable_spoken_punctuation')

    if enable_spoken_emojis is not None:
      features.enableSpokenEmojis = enable_spoken_emojis
      update_mask.append(
          'default_recognition_config.features.enable_spoken_emojis')

    if features.diarizationConfig is None and (min_speaker_count is not None or
                                               max_speaker_count is not None):
      features.diarizationConfig = self._messages.SpeakerDiarizationConfig()

    if min_speaker_count is not None:
      features.diarizationConfig.minSpeakerCount = min_speaker_count
      update_mask.append(
          'default_recognition_config.features.diarization_config.min_speaker_count'
      )

    if max_speaker_count is not None:
      features.diarizationConfig.maxSpeakerCount = max_speaker_count
      update_mask.append(
          'default_recognition_config.features.diarization_config.max_speaker_count'
      )

    request = self._messages.SpeechProjectsLocationsRecognizersPatchRequest(
        name=resource.RelativeName(),
        recognizer=recognizer,
        updateMask=','.join(update_mask))
    return self._RecognizerServiceForLocation(
        location=resource.Parent().Name()).Patch(request)

  def GetOperationRef(self, operation):
    """Converts an Operation to a Resource."""
    return self._resource_parser.ParseRelativeName(
        operation.name, 'speech.projects.locations.operations')

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
        operation_service=self._OperationsServiceForLocation(location))

    return waiter.WaitFor(
        poller=poller,
        operation_ref=operation_ref,
        message=message,
        pre_start_sleep_ms=100,
        max_wait_ms=20000)
