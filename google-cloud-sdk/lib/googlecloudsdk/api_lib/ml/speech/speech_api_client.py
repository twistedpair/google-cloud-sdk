# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Wrapper for interacting with speech API."""

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.ml import content_source
from googlecloudsdk.api_lib.ml.speech import exceptions
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import exceptions as api_lib_exceptions
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import log

SPEECH_API = 'speech'
SPEECH_API_VERSION = 'v1'


def GetSpeechClient(version=SPEECH_API_VERSION):
  return apis.GetClientInstance(SPEECH_API, version)


def GetSpeechMessages(version=SPEECH_API_VERSION):
  return apis.GetMessagesModule(SPEECH_API, version)


class SpeechClient(object):
  """Wrapper for the Cloud Language API client class."""

  def __init__(self, version=None):
    version = version or SPEECH_API_VERSION
    self.client = GetSpeechClient(version=version)
    self.messages = GetSpeechMessages(version=version)

  def GetAudio(self, audio_path):
    """Determine whether path to audio is local, build RecognitionAudio message.

    Args:
      audio_path: str, the path to the audio.

    Raises:
      googlecloudsdk.api_lib.ml.speech.exceptions.AudioException, if audio
          is not found locally and does not appear to be Google Cloud Storage
          URL.

    Returns:
      speech_v1_messages.RecognitionAudio, the audio message.
    """
    try:
      source = content_source.ContentSource.FromContentPath(
          audio_path, SPEECH_API,
          url_validator=storage_util.ObjectReference.IsStorageUrl)
    except content_source.UnrecognizedContentSourceError:
      raise exceptions.AudioException(
          'Invalid audio source [{}]. The source must either '
          'be a local path or a Google Cloud Storage URL '
          '(such as gs://bucket/object).'.format(audio_path))
    audio = self.messages.RecognitionAudio()
    source.UpdateContent(audio)
    return audio

  def GetRecognitionConfig(self, language, max_alternatives, sample_rate=None,
                           encoding=None, filter_profanity=False, hints=None):
    """Build the RecognitionConfig message.

    Args:
      language: str, the language the audio is in.
      max_alternatives: int, the maximum alternatives to be provided.
      sample_rate: int, the sample rate. Required if long_running is True.
      encoding: str, the format of the audio.
      filter_profanity: bool, whether profanity should be filtered.
      hints: [str], list of hints provided by user.

    Returns:
      speech_v1_messages.RecognitionConfig, the config message.
    """
    hints = hints or []
    encoding = encoding or 'ENCODING_UNSPECIFIED'
    config = self.messages.RecognitionConfig(
        languageCode=language,
        maxAlternatives=max_alternatives,
        profanityFilter=filter_profanity,
        speechContexts=[self.messages.SpeechContext(phrases=hints)],
        encoding=self.messages.RecognitionConfig.EncodingValueValuesEnum(
            encoding))
    if sample_rate:
      config.sampleRateHertz = sample_rate
    return config

  def Recognize(self, audio, config, long_running=False):
    """Builds and sends the recognize request to the speech API.

    Args:
      audio: speech_v1_messages.RecognitionAudio, the audio message.
      config: speech_v1_messages.RecognitionConfig, the config message.
      long_running: bool, True if the audio is longer than 60 seconds.

    Raises:
      googlecloudsdk.api_lib.util.exceptions.HttpException, if there is an
          error returned by the API.

    Returns:
      The result from the client.
    """
    if long_running:
      request = self.messages.LongRunningRecognizeRequest(audio=audio,
                                                          config=config)
      try:
        response = self.client.speech.Longrunningrecognize(request)
      except apitools_exceptions.HttpError as e:
        log.debug(e)
        raise api_lib_exceptions.HttpException(e)
    else:
      request = self.messages.RecognizeRequest(audio=audio, config=config)
      try:
        response = self.client.speech.Recognize(request)
      except apitools_exceptions.HttpError as e:
        log.debug(e)
        raise api_lib_exceptions.HttpException(e)
    return response

  def DescribeOperation(self, operation_ref):
    """Describes a long-running operation by the speech API.

    Args:
      operation_ref: the reference to the operation.

    Returns:
      dict, the json representation of the operation.
    """
    return self.client.operations.Get(self.messages.SpeechOperationsGetRequest(
        name=operation_ref.operationsId))

  def WaitOperation(self, operation_ref):
    """Waits for a long-running operation.

    Args:
      operation_ref: the operation reference.

    Returns:
      speech_v1_messages.LongRunningRecognizeResponse, the final result of
          the operation.
    """
    message = 'Waiting for operation [{}] to complete'.format(
        operation_ref.operationsId)
    return waiter.WaitFor(
        waiter.CloudOperationPollerNoResources(
            self.client.operations,
            # TODO(b/62478975): remove this workaround when operation resources
            # are compatible with gcloud parsing.
            get_name_func=lambda x: x.operationsId),
        operation_ref,
        message,
        exponential_sleep_multiplier=2.0,
        sleep_ms=5000,
        wait_ceiling_ms=20000)

