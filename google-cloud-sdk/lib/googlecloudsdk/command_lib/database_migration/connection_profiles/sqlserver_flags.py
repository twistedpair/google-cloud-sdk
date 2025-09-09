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
"""Flags and helpers for SQL Server Connection Profiles related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.database_migration.connection_profiles import flags as cp_flags


def AddCloudSqlProjectIdFlag(parser):
  """Add the Cloud SQL project ID for the Cloud SQL instance to the parser."""
  parser.add_argument(
      '--cloudsql-project-id',
      required=False,
      help=(
          'The project id of the Cloud SQL instance. Only needed if the Cloud'
          ' SQL instance is in a different project than the connection profile.'
          ' This is only supported for source connection profiles for SQL'
          ' Server.'
      ),
  )


def AddCpDetailsFlag(parser):
  """Adds the source and destination parameters to the given parser."""
  cp_params_group = parser.add_group(required=False, mutex=True)
  AddHomogeneousSourceDetailsFlag(cp_params_group)
  AddHeterogeneousSourceOrDagDetailsFlag(cp_params_group)


def AddCloudSqlInstanceFlags(parser):
  """Adds flags for Cloud SQL instances to the given parser."""
  cp_params_group = parser.add_group()
  cp_flags.AddCloudSQLInstanceFlag(cp_params_group, required=False)
  AddCloudSqlProjectIdFlag(cp_params_group)
  cp_flags.AddUsernameFlag(
      cp_params_group,
      help_text="""\
          Username that Database Migration Service uses to connect to the
          database for metrics and observability. We highly recommend that you
          use the sqlserver user for this. Database Migration Service encrypts
          the value when storing it.
      """,
      required=True,
  )
  cp_flags.AddPasswordFlagGroup(cp_params_group, required=True)


def AddHeterogeneousSourceOrDagDetailsFlag(parser):
  """Adds heterogeneous source or DAG HMM source/destination parameters to the given parser."""
  hetero_cp_params_group = parser.add_group()
  cp_flags.AddHostFlag(hetero_cp_params_group, required=True)
  cp_flags.AddPortFlag(hetero_cp_params_group, required=True)
  cp_flags.AddDbmPortFlag(hetero_cp_params_group)


def AddHomogeneousSourceDetailsFlag(parser):
  source_cp_params_group = parser.add_group()
  AddGcsBucket(source_cp_params_group)
  AddGcsPrefix(source_cp_params_group)
  AddProviderFlag(source_cp_params_group)


def AddSourceUpdateFlag(parser):
  """Adds the source connection profile parameters to the given parser during update command."""
  source_cp_params_group = parser.add_group()
  AddGcsBucket(source_cp_params_group)
  AddGcsPrefix(source_cp_params_group)


def AddGcsBucket(parser):
  """Add the gcs bucket field to the parser."""
  parser.add_argument(
      '--gcs-bucket',
      required=True,
      help=(
          'Cloud Storage bucket for the source SQL Server connection profile'
          ' where the backups are stored. This flag is used only for SQL Server'
          ' to Cloud SQL migrations.'
      ),
  )


def AddGcsPrefix(parser):
  """Add the gcs prefix field to the parser."""
  parser.add_argument(
      '--gcs-prefix',
      help=(
          'Cloud Storage prefix path within the bucket for the source SQL'
          ' Server connection profile where the backups are stored. This flag'
          ' is used only for SQL Server to Cloud SQL migrations.'
      ),
  )


def AddProviderFlag(parser):
  """Adds --provider flag to the given parser."""
  parser.add_argument(
      '--provider',
      help='Database provider, for managed databases.',
      choices=['CLOUDSQL', 'RDS'],
  )
