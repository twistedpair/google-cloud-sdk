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
"""This file provides the implementation of the `functions list` command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib
import itertools

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.functions.v1 import util as api_v1_util
from googlecloudsdk.api_lib.functions.v2 import util as api_util
from googlecloudsdk.command_lib.functions.v1.list import command
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def _YieldFromLocations(locations, project, limit, messages, client):
  """Yield the functions from the given locations.

  Args:
    locations: List[str], list of gcp regions.
    project: str, Name of the API to modify. E.g. "cloudfunctions"
    limit: int, List messages limit.
    messages: module, Generated messages module.
    client: base_api.BaseApiClient, cloud functions client library.

  Yields:
    protorpc.message.Message, The resources listed by the service.
  """

  def _ReadAttrAndLogUnreachable(message, attribute):
    if message.unreachable:
      log.warning(
          'The following regions were fully or partially unreachable '
          'for query: %s', ', '.join(message.unreachable))
    return getattr(message, attribute)

  for location in locations:
    location_ref = resources.REGISTRY.Parse(
        location,
        params={'projectsId': project},
        collection='cloudfunctions.projects.locations')
    for function in list_pager.YieldFromList(
        service=client.projects_locations_functions,
        request=messages.CloudfunctionsProjectsLocationsFunctionsListRequest(
            parent=location_ref.RelativeName()),
        limit=limit,
        field='functions',
        batch_size_attribute='pageSize',
        get_field_func=_ReadAttrAndLogUnreachable):
      yield function


@contextlib.contextmanager
def _OverrideEndpointOverrides(api_name, override):
  """Context manager to override an API's endpoint overrides for a while.

  Usage:
    with _OverrideEndpointOverrides(api_name, override):
      client = apis.GetClientInstance(api_name, api_version)


  Args:
    api_name: str, Name of the API to modify. E.g. "cloudfunctions"
    override: str, New value for the endpoint.

  Yields:
    None.
  """
  endpoint_property = getattr(properties.VALUES.api_endpoint_overrides,
                              api_name)
  old_endpoint = endpoint_property.Get()
  try:
    endpoint_property.Set(override)
    yield
  finally:
    endpoint_property.Set(old_endpoint)


def Run(args, release_track):
  """List Google Cloud Functions."""
  client = api_util.GetClientInstance(release_track=release_track)
  messages = api_util.GetMessagesModule(release_track=release_track)
  project = properties.VALUES.core.project.GetOrFail()
  limit = args.limit

  list_v2_generator = _YieldFromLocations(args.regions, project, limit,
                                          messages, client)

  # Currently GCF v2 exists in staging so users of GCF v2 have in their config
  # the api_endpoint_overrides of cloudfunctions.
  # To list GCF v1 resources use _OverrideEndpointOverrides to forcibly
  # overwrites's the user config's override with the original v1 endpoint.
  with _OverrideEndpointOverrides('cloudfunctions',
                                  'https://cloudfunctions.googleapis.com/'):
    client = api_v1_util.GetApiClientInstance()
    messages = api_v1_util.GetApiMessagesModule()
    list_v1_generator = command.YieldFromLocations(args.regions, project, limit,
                                                   messages, client)

  combined_generator = itertools.chain(list_v2_generator, list_v1_generator)
  return combined_generator
