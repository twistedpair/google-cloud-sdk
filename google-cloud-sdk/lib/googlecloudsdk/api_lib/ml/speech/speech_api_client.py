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

from googlecloudsdk.api_lib.ml import content_source
from googlecloudsdk.api_lib.ml.speech import exceptions
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.api_lib.util import apis


SPEECH_API = 'speech'
SPEECH_API_VERSION = 'v1'


def GetAudio(audio_path):
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
  audio = apis.GetMessagesModule(
      SPEECH_API, SPEECH_API_VERSION).RecognitionAudio()
  source.UpdateContent(audio)
  return audio
