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
"""CRM API Folders utilities."""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import resources


FOLDERS_API_VERSION = 'v2beta1'


def FoldersClient():
  return apis.GetClientInstance('cloudresourcemanager', FOLDERS_API_VERSION)


def FoldersRegistry():
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName('cloudresourcemanager', FOLDERS_API_VERSION)
  return registry


def FoldersService():
  return FoldersClient().folders


def FoldersMessages():
  return apis.GetMessagesModule('cloudresourcemanager', FOLDERS_API_VERSION)


def FolderNameToId(folder_name):
  return folder_name[len('folders/'):]


def FolderIdToName(folder_id):
  return 'folders/{0}'.format(folder_id)


def GetFolder(folder_id):
  return FoldersService().Get(
      FoldersMessages().CloudresourcemanagerFoldersGetRequest(
          foldersId=folder_id))


def GetIamPolicy(folder_id):
  messages = FoldersMessages()
  request = messages.CloudresourcemanagerFoldersGetIamPolicyRequest(
      foldersId=folder_id, getIamPolicyRequest=messages.GetIamPolicyRequest())
  return FoldersService().GetIamPolicy(request)


def SetIamPolicy(folder_id, policy):
  messages = FoldersMessages()
  request = messages.CloudresourcemanagerFoldersSetIamPolicyRequest(
      foldersId=folder_id,
      setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy))
  return FoldersService().SetIamPolicy(request)


def GetUri(resource):
  """Returns the uri for resource."""
  folder_id = FolderNameToId(resource.name)
  folder_ref = FoldersRegistry().Parse(
      None, params={'foldersId': folder_id},
      collection='cloudresourcemanager.folders')
  return folder_ref.SelfLink()
