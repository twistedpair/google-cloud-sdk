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
"""Utilities for gcloud ml language commands."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


def AddVisionFlags(parser, with_max_results=True):
  """Adds flags common to all gcloud ml vision commands to the parser.

  Adds positional IMAGE_PATH, and [--max-results] if with_max_results is True.

  Args:
    parser: the parser for the command line.
    with_max_results: whether to add the --max-results flag

  Returns:
    None
  """
  parser.add_argument(
      'image_path',
      help=('The path to the image to be analyzed. This can be either '
            'a local path or a URL. If you provide a local file, the '
            'contents will be sent directly to Google Cloud Vision. If you '
            'provide a URL, it must be in Google Cloud Storage format '
            '(`gs://bucket/object`) or an HTTP URL '
            '(`http://...` or `https://...`)'))
  if with_max_results:
    parser.add_argument(
        '--max-results',
        metavar='MAX_RESULTS',
        help=('The maximum number of results to be provided.'))


# Help text to be used by commands that have a --language-hints flag.
LANGUAGE_HINTS = ("""\
Language hints can be provided to Google Cloud Vision API. In most cases,
an empty value yields the best results since it enables automatic language
detection. For languages based on the Latin alphabet, setting
`language_hints` is not needed. Text detection returns an error if one or
more of the specified languages is not one of the supported languages.
(See https://cloud.google.com/vision/docs/languages.) To provide language
hints run:

  $ {command} --language-hints ja,ko
""")


LANGUAGE_HINTS_FLAG = base.Argument(
    '--language-hints',
    type=arg_parsers.ArgList(),
    metavar='LANGUAGE_HINTS',
    help=('List of languages to use for text detection.'))
