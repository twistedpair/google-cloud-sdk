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
"""Base class for Operation commands."""

from googlecloudsdk.api_lib.resource_manager import operations
from googlecloudsdk.calliope import base


class OperationCommand(base.Command):
  """Common methods for an operation command."""

  def Collection(self):
    return operations.OPERATIONS_COLLECTION

  def GetOperationRef(self, operation_id):
    return operations.OperationsRegistry().Parse(
        None,
        params={'operationsId': operation_id},
        collection=self.Collection())

  def GetUriFunc(self):

    def _GetUri(resource):
      operation_id = operations.OperationNameToId(resource.name)
      return self.GetOperationRef(operation_id).SelfLink()

    return _GetUri
