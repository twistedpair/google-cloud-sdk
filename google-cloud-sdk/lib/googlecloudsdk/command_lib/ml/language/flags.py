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
"""Flags for gcloud ml language commands."""

from googlecloudsdk.calliope import base


def AddLanguageFlags(parser):
  """Adds flags common to all gcloud ml language commands to the parser.

  Adds these flags: (--content= | --content-file=) [--content-type=]
  [--language=] [--encoding-type=]

  Args:
    parser: the parser for the command line.

  Returns:
    None.
  """
  # Content/Content File flag group
  content_group = parser.add_mutually_exclusive_group(required=True)
  content_group.add_argument(
      '--content',
      metavar='CONTENT',
      help=('Specify input text on the command line. Useful for experiments, '
            'or for extremely short text.'))
  content_group.add_argument(
      '--content-file',
      metavar='CONTENT_FILE',
      help=('Specify a local file or Google Cloud Storage (format '
            '`gs://bucket/object`) file path containing the text to '
            'be analyzed. More useful for longer text or data output from '
            'another system.'))
  # Other flags
  content_type_arg = base.Argument(
      '--content-type',
      choices=['PLAIN_TEXT', 'HTML'],
      default='PLAIN_TEXT',
      help=('Specify the format of the input text.'))
  language_arg = base.Argument(
      '--language',
      required=False,
      help=('Specify the language of the input text. If omitted, the server '
            'will attempt to auto-detect. Both ISO (such as `en` or `es`) '
            'and BCP-47 (such as `en-US` or `ja-JP`) language codes '
            'are accepted.'))
  encoding_type_arg = base.Argument(
      '--encoding-type',
      choices=['NONE', 'UTF8', 'UTF16', 'UTF32'],
      default='UTF8',
      help=('The encoding type used by the API to calculate offsets. If NONE, '
            'those offsets are not calculated. This is an optional flag '
            'only used for the entity mentions in results, and does not '
            'affect how the input is read or analyzed.'))

  content_type_arg.AddToParser(parser)
  language_arg.AddToParser(parser)
  encoding_type_arg.AddToParser(parser)
