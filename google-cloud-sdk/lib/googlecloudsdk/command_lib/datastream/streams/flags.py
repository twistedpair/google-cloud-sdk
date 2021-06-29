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
  help_text = """Friendly name for the stream."""
  parser.add_argument('--display-name', help=help_text, required=True)


def AddValidateOnlyFlag(parser):
  """Adds a --validate-only flag to the given parser."""
  help_text = """Only validate the stream, but do not create any resources.
  The default is false."""
  parser.add_argument(
      '--validate-only', help=help_text, action='store_true', default=False)


def AddForceFlag(parser):
  """Adds a --force flag to the given parser."""
  help_text = """Create the stream without validating it."""
  parser.add_argument(
      '--force', help=help_text, action='store_true', default=False)


def AddBackfillStrategyGroup(parser):
  """Adds a --backfiill-all or --backfill-none flag to the given parser."""
  backfill_group = parser.add_group(required=True, mutex=True)
  backfill_group.add_argument(
      '--backfill-none',
      help="""Do not automatically backfill any objects.""",
      action='store_true')
  backfill_all_group = backfill_group.add_group()
  backfill_all_group.add_argument(
      '--backfill-all',
      help="""Automatically backfill objects included in the stream source
      configuration. Specific objects can be excluded.""",
      action='store_true')
  backfill_all_excluded_objects = backfill_all_group.add_group(mutex=True)
  backfill_all_excluded_objects.add_argument(
      '--oracle-excluded-objects',
      help="""Oracle data source objects to avoid backfilling.""")
  backfill_all_excluded_objects.add_argument(
      '--mysql-excluded-objects',
      help="""MySQL data source objects to avoid backfilling.""")

