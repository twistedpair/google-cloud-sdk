# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""The Secure Source Manager repositories client module."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

VERSION_MAP = {base.ReleaseTrack.ALPHA: 'v1'}


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetClientInstance('securesourcemanager', api_version)


@contextlib.contextmanager
def OverrideApiEndpointOverrides(temp_endpoint):
  """Context manager to override securesourcemanager endpoint overrides temporarily.

  Args:
    temp_endpoint: new endpoint value

  Yields:
    None
  """
  endpoint_property = getattr(
      properties.VALUES.api_endpoint_overrides, 'securesourcemanager'
  )
  old_endpoint = endpoint_property.Get()

  try:
    endpoint_property.Set(temp_endpoint)
    yield
  finally:
    endpoint_property.Set(old_endpoint)


class RepositoriesClient(object):
  """Client for Secure Source Manager repositories."""

  def __init__(self):
    self.client = GetClientInstance(base.ReleaseTrack.ALPHA)
    self.messages = self.client.MESSAGES_MODULE
    self._service = self.client.projects_locations_repositories
    self._resource_parser = resources.Registry()
    self._resource_parser.RegisterApiByName('securesourcemanager', 'v1')

  def Create(self, repository_ref):
    """Create a new Secure Source Manager repository.

    Args:
      repository_ref: a resource reference to
        securesourcemanager.projects.locations.repositories.

    Returns:
      Created repository.
    """
    create_req = self.messages.SecuresourcemanagerProjectsLocationsRepositoriesCreateRequest(
        parent=repository_ref.Parent().RelativeName(),
        repositoryId=repository_ref.repositoriesId,
    )
    return self._service.Create(create_req)
