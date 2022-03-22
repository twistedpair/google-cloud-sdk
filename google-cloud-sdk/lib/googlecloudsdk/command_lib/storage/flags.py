# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Generic flags that apply to multiple commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers


def add_precondition_flags(parser):
  """Add flags indicating a precondition for an operation to happen."""
  parser.add_argument(
      '--if-generation-match',
      metavar='GENERATION',
      help='Execute only if the generation matches the generation of the'
      ' requested object.')
  parser.add_argument(
      '--if-metageneration-match',
      metavar='METAGENERATION',
      help='Execute only if the metageneration matches the metageneration of'
      ' the requested object.')


def add_object_metadata_flags(parser, allow_patch=False):
  """Add flags that allow setting object metadata."""
  parser.add_argument(
      '--cache-control',
      help='How caches should handle requests and responses.')
  parser.add_argument(
      '--content-disposition',
      help='How content should be displayed.')
  parser.add_argument(
      '--content-encoding', help='How content is encoded (e.g. ``gzip\'\').')
  parser.add_argument(
      '--content-md5',
      metavar='MD5_DIGEST',
      help=('Manually specified MD5 hash digest for the contents of an uploaded'
            ' file. This flag cannot be used when uploading multiple files. The'
            ' custom digest is used by the cloud provider for validation.'))
  parser.add_argument(
      '--content-language',
      help='Content\'s language (e.g. ``en\'\' signifies "English").')
  parser.add_argument(
      '--content-type',
      help='Type of data contained in the object (e.g. ``text/html\'\').')
  parser.add_argument(
      '--custom-metadata',
      metavar='CUSTOM_METADATA',
      type=arg_parsers.ArgDict(),
      help='Custom metadata fields set by user.')
  parser.add_argument(
      '--custom-time',
      type=arg_parsers.Datetime.Parse,
      help='Custom time for Google Cloud Storage objects in RFC 3339 format.')

  if allow_patch:
    parser.add_argument(
        '--clear-cache-control',
        action='store_true',
        help='Clears object cache control.')
    parser.add_argument(
        '--clear-content-disposition',
        action='store_true',
        help='Clears object content disposition.')
    parser.add_argument(
        '--clear-content-encoding',
        action='store_true',
        help='Clears content encoding.')
    parser.add_argument(
        '--clear-content-md5',
        action='store_true',
        help='Clears object content MD5.')
    parser.add_argument(
        '--clear-content-language',
        action='store_true',
        help='Clears object content language.')
    parser.add_argument(
        '--clear-content-type',
        action='store_true',
        help='Clears object content type.')
    parser.add_argument(
        '--clear-custom-metadata',
        action='store_true',
        help='Clears object custom metadata.')
    parser.add_argument(
        '--clear-custom-time',
        action='store_true',
        help='Clears object custom time.')


def add_encryption_flags(parser, allow_patch=False):
  """Adds flags for encryption and decryption keys."""
  parser.add_argument(
      '--encryption-key',
      hidden=True,
      help=(
          'A customer-supplied encryption key (An RFC 4648 section'
          ' 4 base64-encoded AES256 string), or customer-managed encryption key'
          ' of the form `projects/{project}/locations/{location}/keyRings/'
          '{key-ring}/cryptoKeys/{crypto-key}`. This key will be'
          ' used for all data written to Google Cloud Storage.'
      )
  )
  parser.add_argument(
      '--decryption-keys',
      type=arg_parsers.ArgList(),
      metavar='DECRYPTION_KEY',
      hidden=True,
      help=(
          'A comma separated list of customer-supplied encryption keys'
          ' (RFC 4648 section 4 base64-encoded AES256 strings) that will'
          ' be used to decrypt Google Cloud Storage objects. Data encrypted'
          ' with a customer-managed encryption key (CMEK) is decrypted'
          ' automatically, so CMEKs do not need to be listed here.'
      )
  )
  if allow_patch:
    parser.add_argument(
        '--clear-encryption-key',
        action='store_true',
        hidden=True,
        help='Clears encryption key associated with an object.')


def add_continue_on_error_flag(parser):
  """Adds flag to indicate error should be skipped instead of being raised."""
  parser.add_argument(
      '-c',
      '--continue-on-error',
      action='store_true',
      help='If any operations are unsuccessful, the command will exit with'
      ' a non-zero exit status after completing the remaining operations.'
      ' This flag takes effect only in sequential execution mode (i.e.'
      ' processor and thread count are set to 1). Parallelism is default.')
