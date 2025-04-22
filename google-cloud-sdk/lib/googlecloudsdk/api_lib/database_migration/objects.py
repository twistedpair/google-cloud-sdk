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
"""Database Migration Service connection profiles API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.database_migration import api_util


class ObjectsClient(object):
  """Client for migration job objects service in the API."""

  def __init__(self, release_track):
    self._api_version = api_util.GetApiVersion(release_track)
    self.client = api_util.GetClientInstance(release_track)
    self.messages = api_util.GetMessagesModule(release_track)
    self._service = self.client.projects_locations_migrationJobs_objects
    self.resource_parser = api_util.GetResourceParser(release_track)
    self._release_track = release_track

  def List(self, migration_job_ref, args):
    """Get the list of objects in a migration job.

    Args:
      migration_job_ref: The migration job for which to list objects.
      args: parsed command line arguments

    Returns:
      An iterator over all the matching migration job objects.
    """
    list_req_type = (
        self.messages.DatamigrationProjectsLocationsMigrationJobsObjectsListRequest
    )
    list_req = list_req_type(parent=migration_job_ref.RelativeName())

    return list_pager.YieldFromList(
        service=self._service,
        request=list_req,
        limit=args.limit,
        batch_size=args.page_size,
        field='migrationJobObjects',
        batch_size_attribute='pageSize',
    )

  def Lookup(self, migration_job_ref, args):
    """Lookup a migration job object.

    Args:
      migration_job_ref: The migration job name to which the object belongs.
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Returns:
      MigrationJobObject: the looked up  migration job object.
    """
    source_object_identifier = self.messages.SourceObjectIdentifier(
        database=args.database,
        schema=args.schema,
        table=args.table,
        type=self.GetType(args)
    )

    lookup_req_type = (
        self.messages.DatamigrationProjectsLocationsMigrationJobsObjectsLookupRequest
    )
    lookup_req = lookup_req_type(
        lookupMigrationJobObjectRequest=self.messages.LookupMigrationJobObjectRequest(
            sourceObjectIdentifier=source_object_identifier
        ),
        parent=migration_job_ref.RelativeName(),
    )
    return self._service.Lookup(lookup_req)

  def GetType(self, args):
    if  args.IsKnownAndSpecified('type'):
      return self.messages.SourceObjectIdentifier.TypeValueValuesEnum.lookup_by_name(
          args.type
          )
    return (self.messages.SourceObjectIdentifier.TypeValueValuesEnum
            .lookup_by_name('DATABASE'))


