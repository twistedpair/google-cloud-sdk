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


# TODO(b/62478975): Define custom collection so core operations poller can
# be used instead.
class VideoOperationPoller(waiter.CloudOperationPoller):
  """Poller for cloud longrunning.Operations that do not create resources.

  Necessary because the video operations collection defines relative names
  in a way not compatible with core operations poller.
  """

  def __init__(self, operation_service):
    super(VideoOperationPoller, self).__init__(
        result_service=None, operation_service=operation_service)

  def GetResult(self, operation):
    """Gets result of finished operation.

    Args:
      operation: messages.GoogleLongrunningOperation, the
        finished operation.

    Returns:
      messages.LongRunningRecognizeResponse
    """
    return operation.response

  def Poll(self, operation_ref):
    """Polls operation.

    Args:
      operation_ref: the resource reference for the operation.

    Returns:
      messages.GoogleLongrunningOperation
    """
    request_type = self.operation_service.GetRequestType('Get')
    return self.operation_service.Get(
        request_type(name=operation_ref.operationsId))
