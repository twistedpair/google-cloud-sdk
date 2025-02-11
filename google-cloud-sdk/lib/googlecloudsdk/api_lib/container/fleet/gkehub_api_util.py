# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""GKEHUB API client utils."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base


GKEHUB_API_NAME = 'gkehub'
GKEHUB_ALPHA_API_VERSION = 'v1alpha'
GKEHUB_BETA_API_VERSION = 'v1beta'
GKEHUB_GA_API_VERSION = 'v1'


def GetApiVersionForTrack(release_track=None):
  if not release_track:
    return core_apis.ResolveVersion(GKEHUB_API_NAME)
  elif release_track == base.ReleaseTrack.ALPHA:
    return GKEHUB_ALPHA_API_VERSION
  elif release_track == base.ReleaseTrack.BETA:
    return GKEHUB_BETA_API_VERSION
  elif release_track == base.ReleaseTrack.GA:
    return GKEHUB_GA_API_VERSION
  return core_apis.ResolveVersion(GKEHUB_API_NAME)


def GetApiClientForApiVersion(api_version=None):
  if not api_version:
    api_version = core_apis.ResolveVersion(GKEHUB_API_NAME)
  return core_apis.GetClientInstance(GKEHUB_API_NAME, api_version)


def GetApiClientForTrack(release_track=base.ReleaseTrack.GA):
  return GetApiClientForApiVersion(
      GetApiVersionForTrack(release_track=release_track)
  )


class HubFeatureOperationPoller(waiter.CloudOperationPoller):
  """Poller for GKE Hub Feature API.

  This is necessary because the CloudOperationPoller library doesn't support
  setting the `returnPartialSuccess` field in the Get request.
  """

  def __init__(self, result_service, operation_service):
    """Sets up poller for cloud operations.

    Args:
      result_service: apitools.base.py.base_api.BaseApiService, api service for
        retrieving created result of initiated operation.
      operation_service: apitools.base.py.base_api.BaseApiService, api service
        for retrieving information about ongoing operation.

      Note that result_service and operation_service Get request must have
      single attribute called 'name'.
    """
    self.result_service = result_service
    self.operation_service = operation_service

  def GetResult(self, operation):
    """Overrides.

    Args:
      operation: api_name_messages.Operation.

    Returns:
      result of result_service.Get request.
    """
    request_type = self.result_service.GetRequestType('Get')
    response_dict = encoding.MessageToPyValue(operation.response)
    return self.result_service.Get(
        request_type(name=response_dict['name'], returnPartialSuccess=True),
    )
