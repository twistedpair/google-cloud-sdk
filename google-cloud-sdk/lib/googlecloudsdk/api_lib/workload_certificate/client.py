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
"""Version-agnostic Workload Certificate API client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.api_lib.workload_certificate import error
from googlecloudsdk.api_lib.workload_certificate import util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.workload_certificate import resource
from googlecloudsdk.core import log


class WIPClient(object):
  """Client for the Workload Certificate API with related helper methods.

  This client is a thin wrapper around the base client, and does not handle
  any exceptions.

  Fields:
    client: The raw Workload Certificate API client for the specified release
      track.
    messages: The matching messages module for the client.
    poller: A poller for WorkloadCertificateFeature.
  """

  def __init__(self, release_track=base.ReleaseTrack.GA):
    self.client = util.GetClientInstance(release_track)
    self.messages = util.GetMessagesModule(release_track)
    self.poller = WorkloadCertificateFeaturePoller(
        self.client.projects_locations_global,
        self.client.projects_locations_operations,
    )

  def GetFeature(self, feature_name):
    """Fetch this command's Feature from the API, handling common errors."""
    try:
      return self.client.projects_locations_global.GetWorkloadCertificateFeature(
          self.messages.WorkloadcertificateProjectsLocationsGlobalGetWorkloadCertificateFeatureRequest(
              name=feature_name
          )
      )
    # GetWorkloadCertificateFeature never returns NotFound error when it works
    # as intended, since we model it as a singleton that always exists.
    except apitools_exceptions.HttpUnauthorizedError:
      raise error.ConstructNotAuthorizedError()

  # TODO(b/265384705): Print the consequence of disabling feature and ask the
  # user to confirm before proceeding.
  def DisableFeature(self, feature_name):
    """Disable Workload Certificate feature."""
    op = self.client.projects_locations_global.UpdateWorkloadCertificateFeature(
        self.messages.WorkloadCertificateFeature(
            name=feature_name,
            defaultSpec=self.messages.WorkloadCertificateFeatureSpec(
                mode=self.messages.WorkloadCertificateFeatureSpec.ModeValueValuesEnum.MODE_DISABLED
            ),
        )
    )
    op_resource = resource.OperationName(op.name)

    log.status.Print(
        'Waiting for workload certificate feature disable operation to'
        ' complete.'
    )

    try:
      result = waiter.WaitFor(
          self.poller, op_resource, 'Operation: [{}]  '.format(op.name)
      )
    except waiter.TimeoutError:
      log.status.Print(
          'The operations may still be underway remotely and may still'
          ' succeed. You may check the operation status for the following'
          ' operation  [{}]'.format(op.name)
      )
      return
    log.status.Print(
        'Successfully disabled WorkloadCertificate feature: {}'.format(
            result.name
        )
    )

  def EnableFeature(self, feature_name):
    """Enable Workload Certificate feature."""
    op = self.client.projects_locations_global.UpdateWorkloadCertificateFeature(
        self.messages.WorkloadCertificateFeature(
            name=feature_name,
            defaultSpec=self.messages.WorkloadCertificateFeatureSpec(
                mode=self.messages.WorkloadCertificateFeatureSpec.ModeValueValuesEnum.MODE_ENABLED_WITH_MANAGED_CA
            ),
        )
    )

    op_resource = resource.OperationName(op.name)

    log.status.Print(
        'Waiting for workload certificate feature enablement operation to'
        ' complete.'
    )

    try:
      result = waiter.WaitFor(
          self.poller, op_resource, 'Operation: [{}]  '.format(op.name)
      )
    except waiter.TimeoutError:
      log.status.Print(
          'The operations may still be underway remotely and may still succeed.'
          ' You may check the operation status for the following operation '
          ' [{}]'.format(op.name)
      )
      return
    log.status.Print(
        'Successfully enabled WorkloadCertificate feature: {}'.format(
            result.name
        )
    )


class WorkloadCertificateFeaturePoller(waiter.CloudOperationPoller):
  """Poller specifically for WorkloadCertificateFeature."""

  def GetResult(self, operation):
    """Overrides.

    Calls GetWorkloadCertificateFeature to get the created workload certificate
    feature.

    Args:
      operation: api_name_messages.Operation.

    Returns:
      result of result_service.Get request.
    """
    request_type = self.result_service.GetRequestType(
        'GetWorkloadCertificateFeature'
    )
    response_dict = encoding.MessageToPyValue(operation.response)
    return self.result_service.GetWorkloadCertificateFeature(
        request_type(name=response_dict['name'])
    )
