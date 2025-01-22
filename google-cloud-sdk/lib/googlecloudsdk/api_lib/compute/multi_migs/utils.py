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
"""Utilities multi-MIGs."""

from apitools.base.py import list_pager
from googlecloudsdk.core import properties


def CreateInsertRequest(client, multi_mig, multi_mig_ref):
  return client.messages.ComputeRegionMultiMigsInsertRequest(
      multiMig=multi_mig,
      project=multi_mig_ref.project,
      region=multi_mig_ref.region,
  )


def Insert(client, multi_mig, multi_mig_ref):
  request = CreateInsertRequest(client, multi_mig, multi_mig_ref)
  return client.MakeRequests(
      [(client.apitools_client.regionMultiMigs, 'Insert', request)]
  )


def CreateDeleteRequest(client, multi_mig_ref):
  return client.messages.ComputeRegionMultiMigsDeleteRequest(
      multiMig=multi_mig_ref.Name(),
      project=multi_mig_ref.project,
      region=multi_mig_ref.region,
  )


def Delete(client, multi_mig_ref):
  request = CreateDeleteRequest(client, multi_mig_ref)
  return client.MakeRequests(
      [(client.apitools_client.regionMultiMigs, 'Delete', request)]
  )


def CreateGetRequest(client, multi_mig_ref):
  return client.messages.ComputeRegionMultiMigsGetRequest(
      multiMig=multi_mig_ref.multiMig,
      project=multi_mig_ref.project,
      region=multi_mig_ref.region,
  )


def Get(client, multi_mig_ref):
  request = CreateGetRequest(client, multi_mig_ref)
  return client.MakeRequests(
      [(client.apitools_client.regionMultiMigs, 'Get', request)]
  )


def CreateListRequest(client):
  return client.messages.ComputeRegionMultiMigsListRequest(
      project=properties.VALUES.core.project.GetOrFail(),
      region=properties.VALUES.compute.region.GetOrFail(),
  )


def List(client, args):
  request = CreateListRequest(client)
  return list_pager.YieldFromList(
      service=client.apitools_client.regionMultiMigs,
      request=request,
      batch_size=args.page_size,
      limit=args.limit,
  )
