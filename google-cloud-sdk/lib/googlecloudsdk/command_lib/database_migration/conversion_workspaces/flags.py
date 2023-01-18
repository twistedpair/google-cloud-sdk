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
"""Flags and helpers for the conversion workspace related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers


def AddNoAsyncFlag(parser):
  """Adds a --no-async flag to the given parser."""
  help_text = ('Waits for the operation in progress to complete before '
               'returning.')
  parser.add_argument('--no-async', action='store_true', help=help_text)


def AddDisplayNameFlag(parser):
  """Adds a --display-name flag to the given parser."""
  help_text = """
    A user-friendly name for the conversion workspace. The display name can
    include letters, numbers, spaces, and hyphens, and must start with a letter.
    """
  parser.add_argument('--display-name', help=help_text)


def AddDatabaseEngineFlag(parser):
  """Adds the --source-database-engine and --destination-database-engine flags to the given parser.
  """
  help_text = """\
    Database engine type.
    """
  choices = ['MYSQL', 'POSTGRESQL', 'SQLSERVER', 'ORACLE', 'SPANNER']

  parser.add_argument(
      '--source-database-engine',
      help=help_text,
      choices=choices,
      required=True)

  parser.add_argument(
      '--destination-database-engine',
      help=help_text,
      choices=choices,
      required=True)


def AddDatabaseVersionFlag(parser):
  """Adds the --source-database-version and --destination-database-version flags to the given parser.
  """
  help_text = """
    Version number for the database engine.
    """
  parser.add_argument(
      '--source-database-version', help=help_text, required=True)
  parser.add_argument(
      '--destination-database-version', help=help_text, required=True)


def AddGlobalSettingsFlag(parser):
  """Adds a --global-settings flag to the given parser."""
  help_text = """\
    A generic list of settings for the workspace. The settings are database pair
    dependant and can indicate default behavior for the mapping rules engine or
    turn on or off specific features. An object containing a list of
    "key": "value" pairs.
    """
  parser.add_argument(
      '--global-settings',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      help=help_text)


def AddCommitNameFlag(parser):
  """Adds a --commit-name flag to the given parser."""
  help_text = """
    A user-friendly name for the conversion workspace commit. The commit name
    can include letters, numbers, spaces, and hyphens, and must start with a
    letter.
    """
  parser.add_argument('--commit-name', help=help_text)


def AddAutoCommitFlag(parser):
  """Adds a --auto-commit flag to the given parser."""
  help_text = ('Auto commits the conversion workspace.')
  parser.add_argument('--auto-commit', action='store_true', help=help_text)


def AddFilterFlag(parser):
  """Adds a --filter-string flag to the given parser."""
  help_text = 'Filter the entities based on AIP-160 standard.'
  parser.add_argument('--filter-string', help=help_text)
