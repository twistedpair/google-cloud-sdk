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
"""Flags and helpers for the Database Migration related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def AddNoAsyncFlag(parser):
  """Adds a --no-async flag to the given parser."""
  help_text = (
      'Waits for the operation in progress to complete before returning.'
  )
  parser.add_argument('--no-async', action='store_true', help=help_text)


def AddDisplayNameFlag(parser):
  """Adds a --display-name flag to the given parser."""
  help_text = (
      'A user-friendly name for the private connection. The display name can'
      ' include letters, numbers, spaces, and hyphens, and must start with a'
      ' letter. The maximum length allowed is 60 characters.'
  )
  parser.add_argument('--display-name', help=help_text, required=True)


def AddSkipValidationFlag(parser):
  """Adds a --skip-validation flag to the given parser."""
  help_text = """\
    Creates the private connection without running prior verifications.
    """
  parser.add_argument(
      '--skip-validation',
      action='store_true',
      help=help_text,
  )


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
