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
      help='Execute only if the generation matches the generation of the'
      ' requested object.')
  parser.add_argument(
      '--if-metageneration-match',
      help='Execute only if the metageneration matches the metageneration of'
      ' the requested object.')


def add_object_metadata_flags(parser):
  """Add flags that allow setting object metadata."""
  parser.add_argument(
      '--cache-control',
      help='Influences how backend caches requests and responses.')
  parser.add_argument(
      '--content-disposition',
      help='Information on how content should be displayed.')
  parser.add_argument(
      '--content-encoding', help='How content is encoded (e.g. "gzip").')
  parser.add_argument('--content-md5', help='MD5 digest to use for validation.')
  parser.add_argument(
      '--content-language', help='Content\'s language (e.g. "en" = "English).')
  parser.add_argument(
      '--content-type',
      help='Type of data contained in content (e.g. "text/html").')
  parser.add_argument(
      '--custom-headers',
      type=arg_parsers.ArgDict(),
      help='Custom HTTP headers for AWS that will be prepended with "x-aws-".')
  parser.add_argument(
      '--custom-metadata',
      type=arg_parsers.ArgDict(),
      help='Custom metadata fields set by user.')
  parser.add_argument(
      '--custom-time',
      type=arg_parsers.Datetime.Parse,
      help='Custom time user can set for GCS objects in RFC 3339 format.')
