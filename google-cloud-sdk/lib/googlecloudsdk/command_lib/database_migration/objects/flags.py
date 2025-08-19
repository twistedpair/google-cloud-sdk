# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the migration job objects related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def AddSourceObjectIdentifierFlag(parser):
  """Adds source object identifier flags to the given parser."""
  AddTypeFlag(parser)

  source_object_identifier_group = parser.add_group(
      'The source object identifier.', required=True
  )
  AddDatabaseFlag(source_object_identifier_group)
  AddSchemaFlag(source_object_identifier_group)
  AddTableFlag(source_object_identifier_group)


def AddDatabaseFlag(parser):
  """Adds a --database flag to the given parser."""
  help_text = 'The name of the database to lookup.'
  parser.add_argument('--database', help=help_text)


def AddSchemaFlag(parser):
  """Adds a --schema flag to the given parser."""
  help_text = 'The name of the schema to lookup.'
  parser.add_argument('--schema', help=help_text)


def AddTableFlag(parser):
  """Adds a --table flag to the given parser."""
  help_text = 'The name of the table to lookup.'
  parser.add_argument('--table', help=help_text)


def AddTypeFlag(parser):
  """Adds a --type flag to the given parser."""
  help_text = (
      'The type of the object to lookup. If not provided, the default is'
      ' DATABASE.'
  )
  choices = ['DATABASE', 'SCHEMA', 'TABLE']
  parser.add_argument('--type', help=help_text, choices=choices)
