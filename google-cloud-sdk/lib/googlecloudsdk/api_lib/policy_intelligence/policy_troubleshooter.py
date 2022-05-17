# -*- coding: utf-8 -*- #
# Copyright 2022 Google Inc. All Rights Reserved.
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
"""Utilities for Policy Troubleshooter API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base

_API_NAME = 'policytroubleshooter'
VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v2alpha1',
    base.ReleaseTrack.BETA: 'v1',
    base.ReleaseTrack.GA: 'v1'
}


def GetApiVersion(release_track):
  """Return the api version of the Policy Troubleshooter service."""
  return VERSION_MAP.get(release_track)


class PolicyTroubleshooterApi(object):
  """Base Class for Policy Troubleshooter API."""

  def __new__(cls, release_track):
    if release_track == base.ReleaseTrack.ALPHA:
      return super(PolicyTroubleshooterApi,
                   cls).__new__(PolicyTroubleshooterApiAlpha)

  def __init__(self, release_track):
    api_version = GetApiVersion(release_track)
    self.client = apis.GetClientInstance(_API_NAME, api_version)
    self.messages = apis.GetMessagesModule(_API_NAME, api_version)

  @abc.abstractmethod
  def TroubleshootIAMPolicies(self, access_tuple):
    pass

  @abc.abstractmethod
  def GetPolicyTroubleshooterAccessTuple(self,
                                         condition_context=None,
                                         full_resource_name=None,
                                         principal_email=None,
                                         permission=None):
    pass

  @abc.abstractmethod
  def GetPolicyTroubleshooterConditionContext(self,
                                              destination=None,
                                              request=None,
                                              resource=None):
    pass

  @abc.abstractmethod
  def GetPolicyTroubleshooterPeer(self,
                                  destination_ip=None,
                                  destination_port=None):
    pass

  @abc.abstractmethod
  def GetPolicyTroubleshooterRequest(self, request_time=None):
    pass

  @abc.abstractmethod
  def GetPolicyTroubleshooterResource(self,
                                      resource_name=None,
                                      resource_service=None,
                                      resource_type=None):
    pass


class PolicyTroubleshooterApiAlpha(PolicyTroubleshooterApi):
  """Base Class for Policy Troubleshooter API Alpha."""

  def TroubleshootIAMPolicies(self, access_tuple):
    request = self.messages.GoogleCloudPolicytroubleshooterV2alpha1TroubleshootIamPolicyRequest(
        accessTuple=access_tuple)
    return self.client.iam.Troubleshoot(request)

  def GetPolicyTroubleshooterAccessTuple(self,
                                         condition_context=None,
                                         full_resource_name=None,
                                         principal_email=None,
                                         permission=None):
    return self.messages.GoogleCloudPolicytroubleshooterV2alpha1AccessTuple(
        conditionContext=condition_context,
        fullResourceName=full_resource_name,
        principal=principal_email,
        permission=permission)

  def GetPolicyTroubleshooterRequest(self, request_time=None):
    return self.messages.GoogleCloudPolicytroubleshooterV2alpha1Request(
        receiveTime=request_time)

  def GetPolicyTroubleshooterResource(self,
                                      resource_name=None,
                                      resource_service=None,
                                      resource_type=None):
    return self.messages.GoogleCloudPolicytroubleshooterV2alpha1Resource(
        name=resource_name,
        service=resource_service,
        type=resource_type)

  def GetPolicyTroubleshooterPeer(self,
                                  destination_ip=None,
                                  destination_port=None):
    return self.messages.GoogleCloudPolicytroubleshooterV2alpha1Peer(
        ip=destination_ip, port=destination_port)

  def GetPolicyTroubleshooterConditionContext(self,
                                              destination=None,
                                              request=None,
                                              resource=None):
    return self.messages.GoogleCloudPolicytroubleshooterV2alpha1ConditionContext(
        destination=destination,
        request=request,
        resource=resource)
