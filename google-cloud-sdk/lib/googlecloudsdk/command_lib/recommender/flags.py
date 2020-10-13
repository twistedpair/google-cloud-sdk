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
"""parsing flags for Recommender APIs."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def AddParentFlagsToParser(parser):
  """Adding argument mutex group project, billing-account, folder, organization to parser.

  Args:
      parser: An argparse parser that you can use to add arguments that go on
        the command line after this command.
  """
  resource_group = parser.add_mutually_exclusive_group(
      required=True, help='Resource that is associated with cloud entity type.')
  resource_group.add_argument(
      '--project',
      metavar='PROJECT_NUMBER',
      help='Project Number to use as a parent.')
  resource_group.add_argument(
      '--billing-account',
      metavar='BILLING_ACCOUNT',
      help='Billing Account ID to use as a parent.')
  resource_group.add_argument(
      '--organization',
      metavar='ORGANIZATION_ID',
      help='Organization ID to use as a parent.')
  resource_group.add_argument(
      '--folder', metavar='FOLDER_ID', help='Folder ID to use as a parent.')


def GetLocationAndRecommender(location, recommender):
  return '/locations/{0}/recommenders/{1}'.format(location, recommender)


def GetParentFromFlags(args):
  """Parsing args to get full url string.

  Args:
      args: argparse.Namespace, The arguments that this command was invoked
        with.

  Returns:
      the full url string in one of the following format beased on
      cloud_entity_type(projects, billingAccounts, folders, organizations),
      locations, recommender:
      $cloud_entity_type/[CLOUD_NETITY_ID]/locations/[LOCATION]/recommenders/[RECOMMENDER_ID]/recommendations.
  """
  url = ''
  if args.project:
    url = 'projects/{0}'.format(args.project)
  elif args.billing_account:
    url = 'billingAccounts/{0}'.format(args.billing_account)
  elif args.folder:
    url = 'folders/{0}'.format(args.folder)
  elif args.organization:
    url = 'organizations/{0}'.format(args.organization)
  return url + GetLocationAndRecommender(args.location, args.recommender)
