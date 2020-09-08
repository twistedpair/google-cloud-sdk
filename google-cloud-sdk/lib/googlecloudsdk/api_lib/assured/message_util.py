# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Utilities for constructing Assured api messages."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.assured import workloads


def GetWorkloadsMessages(no_http):
  client = workloads.GetClientInstance(no_http)
  return workloads.GetMessagesModule(client)


def GetV1Beta1Workload(no_http):
  return GetWorkloadsMessages(
      no_http).GoogleCloudAssuredworkloadsV1beta1Workload


def CreateAssuredParent(organization_id, location):
  return 'organizations/{}/locations/{}'.format(organization_id, location)


def CreateAssuredWorkload(display_name=None,
                          compliance_regime=None,
                          billing_account=None,
                          next_rotation_time=None,
                          rotation_period=None,
                          labels=None,
                          etag=None,
                          no_http=False):
  workloads_messages = GetWorkloadsMessages(no_http)
  v1beta1_workload = GetV1Beta1Workload(no_http)
  workload = v1beta1_workload()
  if etag:
    workload.etag = etag
  if billing_account:
    workload.billingAccount = billing_account
  if display_name:
    workload.displayName = display_name
  if labels:
    workload.labels = CreateLabels(labels)
  if compliance_regime:
    workload.complianceRegime = v1beta1_workload.ComplianceRegimeValueValuesEnum(
        compliance_regime)
    if compliance_regime == 'FEDRAMP_MODERATE':
      settings = workloads_messages.GoogleCloudAssuredworkloadsV1beta1WorkloadFedrampModerateSettings(
      )
      settings.kmsSettings = CreateKmsSettings(next_rotation_time,
                                               rotation_period)
      workload.fedrampModerateSettings = settings
    elif compliance_regime == 'FEDRAMP_HIGH':
      settings = workloads_messages.GoogleCloudAssuredworkloadsV1beta1WorkloadFedrampHighSettings(
      )
      settings.kmsSettings = CreateKmsSettings(next_rotation_time,
                                               rotation_period)
      workload.fedrampHighSettings = settings
    elif compliance_regime == 'CJIS':
      settings = workloads_messages.GoogleCloudAssuredworkloadsV1beta1WorkloadCJISSettings(
      )
      settings.kmsSettings = CreateKmsSettings(next_rotation_time,
                                               rotation_period)
      workload.cjisSettings = settings
    elif compliance_regime == 'IL4':
      settings = workloads_messages.GoogleCloudAssuredworkloadsV1beta1WorkloadIL4Settings(
      )
      settings.kmsSettings = CreateKmsSettings(next_rotation_time,
                                               rotation_period)
      workload.il4Settings = settings
  return workload


def CreateKmsSettings(next_rotation_time, rotation_period, no_http=False):
  return GetWorkloadsMessages(
      no_http).GoogleCloudAssuredworkloadsV1beta1WorkloadKMSSettings(
          nextRotationTime=next_rotation_time, rotationPeriod=rotation_period)


def CreateLabels(labels, no_http=False):
  v1beta1_workload = GetV1Beta1Workload(no_http)
  workload_labels = []
  for key, value in labels.items():
    new_label = v1beta1_workload.LabelsValue.AdditionalProperty(
        key=key, value=value)
    workload_labels.append(new_label)
  return v1beta1_workload.LabelsValue(additionalProperties=workload_labels)


def CreateUpdateMask(display_name, labels):
  update_mask = []
  if display_name:
    update_mask.append('workload.display_name')
  if labels:
    update_mask.append('workload.labels')
  return ','.join(update_mask)
