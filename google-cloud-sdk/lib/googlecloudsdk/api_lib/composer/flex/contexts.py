# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Base of Flex API services."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.composer.flex import base as api_base
from googlecloudsdk.calliope import base


class ContextService(api_base.Service):
  """The Composer Flex Context Service.

  Usage:

    # Fetch GA version of ContextService
    context_service = ContextService()
    # -- or --
    # Fetch Other versions
    # context_service = ContextService(release_track=ReleaseTrack.Beta)

    context_service.Create(...)
    context_service.Delete(...)
  """

  def __init__(self, api=api_base.API, release_track=base.ReleaseTrack.GA):
    super(ContextService, self).__init__(api, release_track)
    self.service = self.client.projects_locations_contexts

  def Create(self, context, location_ref):
    raise NotImplementedError('Context Create not yet supported.')

  def Delete(self, context_ref):
    req = self.messages.ComposerflexProjectsLocationsContextsDeleteRequest(
        name=context_ref)
    self.service.Delete(req)

  def Get(self, context_ref):
    raise NotImplementedError('Context Get not yet supported.')

  def List(self, location_ref, page_size, limit):
    raise NotImplementedError('Context List not yet supported.')
