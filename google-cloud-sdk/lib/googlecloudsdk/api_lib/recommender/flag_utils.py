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
"""recommender API utlities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.recommender import service as recommender_service


def GetServiceFromArgs(args):
  """Returns the service from the user-specified arguments.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
  """
  if args.project:
    service = recommender_service.ProjectsRecommenderListRecommendationsService(
    )
  elif args.billing_account:
    service = recommender_service.BillingAccountsRecommenderListRecommendationsService(
    )
  elif args.folder:
    service = recommender_service.FoldersRecommenderListRecommendationsService()
  elif args.organization:
    service = recommender_service.OrganizationsRecommenderListRecommendationsService(
    )

  return service


def GetListRequestFromArgs(args, parent_resource):
  """Returns the get_request from the user-specified arguments.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
    parent_resource: resource url string, the flags are already defined in
      argparse namespace, including project, billing-account, folder,
      organization, etc.
  """

  messages = recommender_service.RecommenderMessages()

  if args.project:
    get_request = messages.RecommenderProjectsLocationsRecommendersRecommendationsListRequest(
        parent=parent_resource)
  elif args.billing_account:
    get_request = messages.RecommenderBillingAccountsLocationsRecommendersRecommendationsListRequest(
        parent=parent_resource)
  elif args.organization:
    get_request = messages.RecommenderOrganizationsLocationsRecommendersRecommendationsListRequest(
        parent=parent_resource)
  elif args.folder:
    get_request = messages.RecommenderFoldersLocationsRecommendersRecommendationsListRequest(
        parent=parent_resource)

  return get_request
