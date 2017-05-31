# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Flag definitions for gcloud billing."""
from googlecloudsdk.calliope import base


def GetAccountIdArgument(positional=True):
  metavar = 'ACCOUNT_ID'
  completion_resource = 'cloudbilling.billingAccounts'
  list_command_path = 'billing accounts list --uri'
  help_ = (
      'Specify a billing account ID. Billing account '
      'IDs are of the form `0X0X0X-0X0X0X-0X0X0X`. To see available IDs, run '
      '`$ gcloud alpha billing accounts list`.'
  )
  if positional:
    return base.Argument(
        'id',
        metavar=metavar,
        completion_resource=completion_resource,
        list_command_path=list_command_path,
        help=help_)
  else:
    return base.Argument(
        '--account-id',
        dest='account_id',
        required=True,
        metavar=metavar,
        completion_resource=completion_resource,
        list_command_path=list_command_path,
        help=help_)


def GetProjectIdArgument():
  return base.Argument(
      'project_id',
      completion_resource='cloudresourcemanager.projects',
      list_command_path='projects list --uri',
      help='Specify a project id.'
  )
