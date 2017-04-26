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
"""Small class to deal with operations in Cloud Speech."""

from googlecloudsdk.api_lib.util import waiter


class SpeechOperationPoller(waiter.CloudOperationPoller):
  """Poller for cloud longrunning.Operations that do not create resources.

  Necessary because resource name formats aren't compatible with
  CloudOperationPoller.
  """

  def __init__(self, operation_service):
    super(SpeechOperationPoller, self).__init__(
        result_service=None, operation_service=operation_service)

  def GetResult(self, operation):
    """Gets result of finished operation.

    Args:
      operation: speech_v1_messages.Operation, the finished operation.

    Returns:
      speech_v1_messages.LongRunningRecognizeResponse
    """
    return operation.response

  def Poll(self, operation_ref):
    """Polls operation.

    Args:
      operation_ref: the resource reference for the operation.

    Returns:
      speech_v1_messages.Operation
    """
    request_type = self.operation_service.GetRequestType('Get')
    return self.operation_service.Get(
        request_type(name=operation_ref.operationsId))
