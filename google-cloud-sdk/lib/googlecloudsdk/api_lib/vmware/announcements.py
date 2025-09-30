# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Cloud vmware Announcements client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.vmware import util


class AnnouncementsClient(util.VmwareClientBase):
  """cloud vmware Announcements client."""

  def __init__(self):
    super(AnnouncementsClient, self).__init__()
    self.service = self.client.projects_locations_announcements

  def List(self, location, announcement_type):
    request = (
        self.messages.VmwareengineProjectsLocationsAnnouncementsListRequest(
            parent=location.RelativeName()
        )
    )

    # At the moment we only support active announcements of a given type.
    request.filter = f'state:ACTIVE AND code:{announcement_type}'

    return list_pager.YieldFromList(
        self.service,
        request,
        batch_size_attribute='pageSize',
        field='announcements',
    )
