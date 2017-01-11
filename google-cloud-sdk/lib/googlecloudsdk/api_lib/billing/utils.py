# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Util for billing."""

from googlecloudsdk.core import apis
from googlecloudsdk.core import resources

ACCOUNT_ID_ARG_PARAMS = dict(
    metavar='ACCOUNT_ID',
    completion_resource='cloudbilling.billingAccounts',
    list_command_path='billing.accounts',
    help=(
        'Specify a billing account id. Billing account '
        'ids look like: 0X0X0X-0X0X0X-0X0X0X, and can '
        'be listed with, gcloud alpha billing accounts list.'
    )
)

PROJECT_ID_ARG_PARAMS = dict(
    metavar='PROJECT_ID',
    completion_resource='cloudresourcemanager.projects',
    list_command_path='projects',
    help='Specify a project id.'
)


def GetMessages():
  """Import and return the appropriate projects messages module."""
  return apis.GetMessagesModule('cloudbilling', 'v1')


def GetClient():
  """Import and return the appropriate projects client.

  Returns:
    a cloudbilling client
  """
  return apis.GetClientInstance('cloudbilling', 'v1')


def MessageToResource(message, collection):
  """Convert a protorpclite Message to a gcloud Resource.

  Args:
    message: a protorpclite message
    collection: a collection from the resource_registry
  Returns:
    a resource of type Collection
  """
  return resources.Create(
      collection,
      **dict([
          (field.name, message.get_assigned_value(field.name))
          for field in message.__class__.all_fields()
      ])
  )
