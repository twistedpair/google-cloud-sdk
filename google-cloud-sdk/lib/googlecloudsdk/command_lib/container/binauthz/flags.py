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
"""Flags for binauthz command group."""


def AddCommonFlags(parser):
  parser.add_argument(
      '--artifact-url',
      type=str,
      help=('Container URL.  May be in the '
            '`*.gcr.io/repository/image` format, or may '
            'optionally contain the `http` or `https` scheme'))


def AddSignatureSpecifierFlags(parser):
  """Flags for Binary Authorization signature management."""
  parser.add_argument(
      '--public-key-file',
      type=str,
      help='Path to file containing the public key to store')
  parser.add_argument(
      '--signature-file',
      type=str,
      help=('Path to file containing the signature to store, or `-` to read '
            'signature from stdin'))
