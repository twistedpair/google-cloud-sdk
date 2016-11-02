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

"""Base class for Folder commands."""

from googlecloudsdk.api_lib.resource_manager import folders
from googlecloudsdk.calliope import base


class FolderCommand(base.Command):
  """Common methods for a folder command."""

  def Collection(self):
    return folders.FOLDERS_COLLECTION

  def GetFolderRef(self, folder_id):
    return folders.FoldersRegistry().Parse(
        None, params={'foldersId': folder_id}, collection=self.Collection())

  def GetUriFunc(self):
    def _GetUri(resource):
      folder_id = folders.FolderNameToId(resource.name)
      return self.GetFolderRef(folder_id).SelfLink()
    return _GetUri
