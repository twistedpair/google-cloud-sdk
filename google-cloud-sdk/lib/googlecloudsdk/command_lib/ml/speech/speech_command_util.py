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
"""Library for gcloud ml speech commands."""

from googlecloudsdk.api_lib.ml.speech import speech_api_client
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.core import resources


def RunRecognizeCommand(path_to_audio, language, long_running=False,
                        sample_rate=None, hints=None, max_alternatives=None,
                        filter_profanity=False, async=False, encoding=None):
  """Runs the gcloud recognize speech commands.

  Args:
    path_to_audio: str, the path to the audio.
    language: str, the BCP-47 language code of the audio.
    long_running: bool, True if the recognize-long-running command is being run.
    sample_rate: None|int, the sample rate in Hertz of the audio, if any.
    hints: None|[str], the hints given, if any.
    max_alternatives: None|int, the max number of choices desired from the API.
    filter_profanity: bool, True if the API should filter profanities.
    async: bool, True if the API should return the operation right away instead
        of waiting for completion.
    encoding: None|str, the encoding of the audio.

  Raises:
    googlecloudsdk.api_lib.ml.speech.exceptions.AudioException: if the audio
        file is not recognized as local or a valid Google Cloud Storage URL.
    googlecloudsdk.api_lib.util.exceptions.HttpException: arbitrary errors
        returned by the API.
    googlecloudsdk.api_lib.util.waiter.OperationError: if polling the operation
        results in an operation with an error.

  Returns:
    the result of the command (speech_v1_messages.RecognizeResponse,
        speech_v1_messages.Operation, or speech_v1_messages.LongRunningRecognize
        Response).
  """
  client = speech_api_client.SpeechClient()
  audio = client.GetAudio(path_to_audio)
  config = client.GetRecognitionConfig(
      language, max_alternatives, sample_rate=sample_rate, encoding=encoding,
      filter_profanity=filter_profanity, hints=hints)
  result = client.Recognize(audio, config, long_running)
  if not long_running or async:
    return result
  operation_ref = resources.REGISTRY.Parse(result.name,
                                           collection='speech.operations')
  return client.WaitOperation(operation_ref)


def AddRecognizeFlags(parser, require_sample_rate=False):
  """Adds flags for gcloud speech recognize commands."""
  sample_rate_help = ('The sample rate in Hertz. For best results, set the '
                      'sampling rate of the audio source to 16000 Hz. If '
                      'that\'s not possible, use the native sample rate of '
                      'the audio source (instead of re-sampling).')
  if not require_sample_rate:
    sample_rate_help += (' Required if the file format is not WAV or FLAC.')
  parser.add_argument('audio',
                      help=('The location of the audio file to transcribe. '
                            'Must be a local path or a Google Cloud Storage '
                            'URL (in the format gs://bucket/object).'))
  parser.add_argument('--sample-rate',
                      type=int,
                      help=sample_rate_help,
                      required=require_sample_rate)
  parser.add_argument('--language',
                      help=('The language of the supplied audio as a '
                            'BCP-47 '
                            '(https://www.rfc-editor.org/rfc/bcp/bcp47.txt) '
                            'language tag. Example: "en-US". See '
                            'https://cloud.google.com/speech/docs/languages '
                            'for a list of the currently supported language '
                            'codes.'),
                      required=True)
  parser.add_argument('--hints',
                      metavar='HINTS',
                      help=('A list of strings containing word and phrase '
                            '"hints" so that the speech recognition is more '
                            'likely to recognize them. This can be used to '
                            'improve the accuracy for specific words and '
                            'phrases, for example, if specific commands are '
                            'typically spoken by the user. This can also be '
                            'used to add additional words to the vocabulary '
                            'of the recognizer. See '
                            'https://cloud.google.com/speech/limits#content.'
                           ),
                      type=arg_parsers.ArgList())
  parser.add_argument('--max-alternatives',
                      help=('Maximum number of recognition hypotheses to be '
                            'returned. The server may return fewer than '
                            '`max_alternatives`. Valid values are `0`-`30`. '
                            'A value of `0` or `1` will return a maximum of '
                            'one.'),
                      type=int,
                      default=1)
  parser.add_argument('--filter-profanity',
                      help=('If True, the server will attempt to filter out '
                            'profanities, replacing all but the initial '
                            'character in each filtered word with asterisks, '
                            'e.g. "```f***```".'),
                      action='store_true')
  parser.add_argument('--encoding',
                      help=('The type of encoding of the file. Required if '
                            'the file format is not WAV or FLAC.'),
                      choices=['LINEAR16', 'FLAC', 'MULAW', 'AMR', 'AMR_WB',
                               'OGG_OPUS', 'SPEEX_WITH_HEADER_BYTE'])


SPEECH_AUTH_HELP = ("""\
To use the Google Cloud Speech API, use a service account belonging to a
project that has Google Cloud Speech enabled. Please see
https://cloud.google.com/speech/docs/common/auth
for directions on setting up an account to use with the API. After setting up
the account, download the key file and run:

  $ gcloud auth activate-service-account --key-file=$KEY_FILE
""")
