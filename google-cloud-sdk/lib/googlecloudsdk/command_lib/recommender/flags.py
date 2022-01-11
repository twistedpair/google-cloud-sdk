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

from googlecloudsdk.api_lib.recommender import base
from googlecloudsdk.command_lib.util.args import common_args


def AddParentFlagsToParser(parser):
  """Adding argument mutex group project, billing-account, folder, organization to parser.

  Args:
      parser: An argparse parser that you can use to add arguments that go on
        the command line after this command.
  """
  resource_group = parser.add_mutually_exclusive_group(
      required=True,
      help='Resource that is associated with cloud entity type. Currently four mutually exclusive flags are supported, --project, --billing-account, --folder, --organization.'
  )
  common_args.ProjectArgument(
      help_text_to_overwrite='The Google Cloud Platform project ID.'
  ).AddToParser(resource_group)
  resource_group.add_argument(
      '--billing-account',
      metavar='BILLING_ACCOUNT',
      help='The Google Cloud Platform Billing Account ID to use for this invocation.'
  )
  resource_group.add_argument(
      '--organization',
      metavar='ORGANIZATION_ID',
      help='The Google Cloud Platform Organization ID to use for this invocation.'
  )
  resource_group.add_argument(
      '--folder',
      metavar='FOLDER_ID',
      help='Folder ID to use for this invocation.')


def AddEntityFlagsToParser(parser, entities):
  """Adds argument mutex group of specified entities to parser.

  Args:
      parser: An argparse parser that you can use to add arguments that go on
        the command line after this command.
      entities: The entities to add.
  """
  resource_group = parser.add_mutually_exclusive_group(
      required=True, help='Resource that is associated with cloud entity type.')
  if base.EntityType.ORGANIZATION in entities:
    resource_group.add_argument(
        '--organization',
        metavar='ORGANIZATION_ID',
        help='The Google Cloud Organization ID to use for this invocation.')
  if base.EntityType.FOLDER in entities:
    resource_group.add_argument(
        '--folder',
        metavar='FOLDER_ID',
        help='The Google Cloud Folder ID to use for this invocation.')
  if base.EntityType.BILLING_ACCOUNT in entities:
    resource_group.add_argument(
        '--billing-account',
        metavar='BILLING_ACCOUNT',
        help='The Google Cloud Billing Account ID to use for this invocation.')
  if base.EntityType.PROJECT in entities:
    common_args.ProjectArgument(
        help_text_to_overwrite='The Google Cloud Project ID.').AddToParser(
            resource_group)


def AddRecommenderFlagsToParser(parser, entities):
  """Adds argument mutex group of specified entities and recommender to parser.

  Args:
      parser: An argparse parser that you can use to add arguments that go on
        the command line after this command.
      entities: The entities to add.
  """
  AddEntityFlagsToParser(parser, entities)
  parser.add_argument(
      '--location',
      metavar='LOCATION',
      required=True,
      help='Location to use for this invocation.')
  parser.add_argument(
      'recommender',
      metavar='RECOMMENDER',
      help='Recommender to use for this invocation.')


def GetResourceSegment(args):
  """Returns the resource from up to the cloud entity."""
  if args.project:
    return 'projects/%s' % args.project
  elif args.folder:
    return 'folders/%s' % args.folder
  elif args.billing_account:
    return 'billingAccounts/%s' % args.billing_account
  else:
    return 'organizations/%s' % args.organization


def GetLocationSegment(args):
  """Returns the resource name up to the location."""
  parent = GetResourceSegment(args)
  return '{}/locations/{}'.format(parent, args.location)


def GetRecommenderName(args):
  """Returns the resource name up to the recommender."""
  parent = GetLocationSegment(args)
  return '{}/recommenders/{}'.format(parent, args.recommender)


def GetRecommenderConfigName(args):
  """Returns the resource name for the Recommender Config."""
  return GetRecommenderName(args) + '/config'


def GetConfigsParentFromFlags(args, is_insight_api):
  """Parsing args for url string for recommender and insigh type configs apis.

  Args:
      args: argparse.Namespace, The arguments that this command was invoked
        with.
      is_insight_api: whether this is an insight api.

  Returns:
      The full url string based on flags given by user.
  """
  url = 'projects/{0}'.format(args.project)
  url = url + '/locations/{0}'.format(args.location)

  if is_insight_api:
    url = url + '/insightTypes/{0}'.format(args.insight_type)
  else:
    url = url + '/recommenders/{0}'.format(args.recommender)
  return url + '/config'


def GetParentFromFlags(args, is_list_api, is_insight_api):
  """Parsing args to get full url string.

  Args:
      args: argparse.Namespace, The arguments that this command was invoked
        with.
      is_list_api: Boolean value specifying whether this is a list api, if not
        append recommendation id or insight id to the resource name.
      is_insight_api: whether this is an insight api, if so, append
        insightTypes/[INSIGHT_TYPE] rather than recommenders/[RECOMMENDER_ID].

  Returns:
      The full url string based on flags given by user.
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

  url = url + '/locations/{0}'.format(args.location)

  if is_insight_api:
    url = url + '/insightTypes/{0}'.format(args.insight_type)
    if not is_list_api:
      url = url + '/insights/{0}'.format(args.INSIGHT)
  else:
    url = url + '/recommenders/{0}'.format(args.recommender)
    if not is_list_api:
      url = url + '/recommendations/{0}'.format(args.RECOMMENDATION)
  return url
