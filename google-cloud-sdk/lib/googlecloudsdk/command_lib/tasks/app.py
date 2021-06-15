# -*- coding: utf-8 -*- #
# Copyright 2017 Google LLC. All Rights Reserved.
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
"""Utilities for App Engine apps for `gcloud tasks` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.app import appengine_api_client as app_engine_api
from googlecloudsdk.api_lib.tasks import GetApiAdapter
from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.core import exceptions


class RegionResolvingError(exceptions.Error):
  """Error for when the app's region cannot be ultimately determined."""


def AppEngineAppExists():
  """Returns whether an AppEngine app exists for the current project.

  Previously we were relying on the output of ListLocations for Cloud Tasks &
  Cloud Scheduler to determine if an AppEngine exists. Previous behaviour was
  to return only one location which would be the AppEngine app location and an
  empty list otherwise if no app existed. Now with AppEngine dependency removal,
  ListLocations will return an actual list of valid regions. If an AppEngine app
  does exist, that location will be returned indexed at 0 in the result list.
  """
  app_engine_api_client = app_engine_api.GetApiClientForTrack(
      calliope_base.ReleaseTrack.GA)
  found_app = True
  try:
    # Should raise NotFoundError if no app exists.
    app_engine_api_client.GetApplication()
  except apitools_exceptions.HttpNotFoundError:
    found_app = False
  return found_app


def ResolveAppLocation(project_ref, locations_client=None):
  """Gets the default location from the Cloud Tasks API.

  If an AppEngine app exists, the default location is the location where the
  app exists.

  Args:
    project_ref: The project resource to look up the location for.
    locations_client: The project resource used to look up locations.

  Returns:
    The location. Some examples: 'us-central1', 'us-east4'

  Raises:
    RegionResolvingError: If we are unable to determine a default location
      for the given project.
  """
  if not locations_client:
    locations_client = GetApiAdapter(calliope_base.ReleaseTrack.GA).locations
  locations = list(locations_client.List(project_ref))
  if len(locations) >= 1 and AppEngineAppExists():
    return locations[0].labels.additionalProperties[0].value
  raise RegionResolvingError(
      'There is no AppEngine app associated with the project so unable to use '
      'the same location as default location. Please use the location flag to '
      'manually specify a location.'
  )
