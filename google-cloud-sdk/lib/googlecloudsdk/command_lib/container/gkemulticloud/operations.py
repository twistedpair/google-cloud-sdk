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
"""Utilities for operations command groups."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkemulticloud import util as api_util
from googlecloudsdk.calliope import base

_OPERATION_TABLE_FORMAT = """\
    table(
        name.basename():label=OPERATION_NAME,
        name.segment(3):label=LOCATION,
        metadata.target.basename(),
        done.yesno(yes='DONE', no='RUNNING'):label=STATUS,
        metadata.createTime.date():sort=1,
        duration(start=metadata.createTime,end=metadata.endTime,precision=0,calendar=false).slice(2:).join("").yesno(no="<1S"):label=DURATION
    )"""


def AddFilter(parser, noun):
  parser.display_info.AddFilter(
      'metadata.target ~ projects/\\d+/locations/.+/{}*'.format(noun))


def AddFormat(parser):
  parser.display_info.AddFormat(_OPERATION_TABLE_FORMAT)


class Client(object):
  """Client for managing Anthos Multicloud operations."""

  def __init__(self, client=None, messages=None, track=base.ReleaseTrack.GA):
    self.client = client or api_util.GetClientInstance(release_track=track)
    self.messages = messages or api_util.GetMessagesModule(release_track=track)
    self.service = self.client.projects_locations_operations
    self.track = track

  def Describe(self, args, region_ref):
    """Describes an Anthos Mulitcloud operation."""
    req = self.messages.GkemulticloudProjectsLocationsOperationsGetRequest(
        name='{}/operations/{}'.format(region_ref.RelativeName(),
                                       args.operation_id))
    return self.client.projects_locations_operations.Get(req)

  def List(self, args, region_ref):
    """Lists Anthos Multicloud operations."""
    request = self.messages.GkemulticloudProjectsLocationsOperationsListRequest(
        name=region_ref.RelativeName())
    for operation in list_pager.YieldFromList(
        service=self.service,
        request=request,
        limit=args.limit,
        field='operations',
        batch_size_attribute='pageSize'):
      yield operation
