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
"""Flags and helpers for the Datastream related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def AddDisplayNameFlag(parser):
  """Adds a --display-name flag to the given parser."""
  help_text = """Friendly name for the private connection."""
  parser.add_argument('--display-name', help=help_text, required=True)


def AddNetworkAttachmentFlag(parser):
  """Adds the `--network-attachment` flag to the parser."""
  parser.add_argument(
      '--network-attachment',
      required=True,
      type=str,
      help=(
          'Full URI of the network attachment that datastream will connect to.'
          'For example, this would be of the form:'
          '`network-attachment=projects/test-project/regions/us-central1/networkAttachments/my-na`'
      ),
  )


def AddValidateOnlyFlag(parser):
  """Adds the `--validate-only` flag to the parser."""
  parser.add_argument(
      '--validate-only',
      required=False,
      action='store_true',
      help=(
          'If set, the request will retrieve the project id to allow in the '
          ' network attachment Datastream will connect to.'
      ),
  )
