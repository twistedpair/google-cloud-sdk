# Copyright 2013 Google Inc. All Rights Reserved.
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

"""IAM completers."""

from googlecloudsdk.command_lib.util import completers
from googlecloudsdk.core import resources


class IamRolesCompleter(completers.NoCacheCompleter):
  """An IAM role completer for a resource argument.

  This completer bypasses the resource parser and completion cache.

  Attributes:
    _resource_dest: The argparse Namespace dest string for the resource
      argument that has the roles.
    _resource_collection: The resource argument collection.
  """

  def __init__(self, resource_dest=None, resource_collection=None, **kwargs):
    super(IamRolesCompleter, self).__init__(**kwargs)
    self._resource_dest = resource_dest
    self._resource_collection = resource_collection

  def Complete(self, prefix, parameter_info):
    """Returns the list of role names for the resource that match prefix."""
    resource_ref = resources.REGISTRY.Parse(
        parameter_info.GetValue(self._resource_dest),
        collection=self._resource_collection)
    resource_uri = resource_ref.SelfLink()
    roles = parameter_info.Execute(
        ['beta', 'iam', 'list-grantable-roles',
         '--format=disable', resource_uri])
    return [role.name for role in roles if role.name.startswith(prefix)]
