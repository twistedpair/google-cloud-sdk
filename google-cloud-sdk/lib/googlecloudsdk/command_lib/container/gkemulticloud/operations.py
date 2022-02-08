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

from apitools.base.py import encoding
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkemulticloud import util as api_util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.container.gkemulticloud import constants
from googlecloudsdk.core import log
from googlecloudsdk.core.console import progress_tracker

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
  """Client for managing Anthos Multi-cloud operations."""

  def __init__(self, client=None, messages=None, track=base.ReleaseTrack.GA):
    self.client = client or api_util.GetClientInstance(release_track=track)
    self.messages = messages or api_util.GetMessagesModule(release_track=track)
    self.service = self.client.projects_locations_operations
    self.track = track

  def Describe(self, operation_ref):
    """Describes an Anthos Multi-cloud operation."""
    req = self.messages.GkemulticloudProjectsLocationsOperationsGetRequest(
        name=operation_ref.RelativeName())
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

  def Wait(self, operation_ref, message):
    """Waits for an Anthos Multi-cloud operation to complete.

    Args:
      operation_ref: object, passed to operation poller poll method.
      message: str, string to display for the progress tracker.
    """
    poller = _Poller(self.service)
    waiter.WaitFor(
        poller=poller,
        operation_ref=operation_ref,
        custom_tracker=progress_tracker.ProgressTracker(
            message=message,
            detail_message_callback=poller.GetDetailMessage,
            aborted_message='Aborting wait for operation {}.\n'.format(
                operation_ref)),
        wait_ceiling_ms=constants.MAX_LRO_POLL_INTERVAL_MS)


class _Poller(waiter.CloudOperationPollerNoResources):
  """Poller for Anthos Multi-cloud operations.

  The poller stores the status detail from the operation message to update
  the progress tracker.
  """

  def __init__(self, operation_service):
    """See base class."""
    self.operation_service = operation_service
    self.status_detail = None
    self.last_error_detail = None

  def Poll(self, operation_ref):
    """See base class."""
    request_type = self.operation_service.GetRequestType('Get')
    operation = self.operation_service.Get(
        request_type(name=operation_ref.RelativeName()))
    if operation.metadata is not None:
      metadata = encoding.MessageToPyValue(operation.metadata)
      if 'statusDetail' in metadata:
        self.status_detail = metadata['statusDetail']
      if 'errorDetail' in metadata:
        error_detail = metadata['errorDetail']
        if error_detail != self.last_error_detail:
          log.error(error_detail)
        self.last_error_detail = error_detail
    return operation

  def GetDetailMessage(self):
    return self.status_detail
