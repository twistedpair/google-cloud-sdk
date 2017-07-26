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
"""Helpers for compute commitments commands."""


# TODO(b/35753086): Use regular service when API becomes saner.
class ServiceComposer(object):
  """Delegates calls to appropriate service.

  Appropriate service for AggregatedList calls is zonal service, regional
  service is appropriate for everything else.
  """

  def __init__(self, zonal_service, regional_service):
    self.zonal_service = zonal_service
    self.regional_service = regional_service

  def _GetServiceForRequest(self, method):
    if method == 'AggregatedList':
      return self.zonal_service
    return self.regional_service

  def GetRequestType(self, request_type):
    if request_type == 'AggregatedList':
      return self.zonal_service.GetRequestType(request_type)
    return self.regional_service.GetRequestType(request_type)

  def GetMethodConfig(self, method):
    self.latest_service = self._GetServiceForRequest(method)
    return self.latest_service.GetMethodConfig(method)

  def GetUploadConfig(self, method):
    self.latest_service = self._GetServiceForRequest(method)
    return self.latest_service.GetUploadConfig(method)

  def PrepareHttpRequest(self, *args, **kwargs):
    return self.latest_service.PrepareHttpRequest(*args, **kwargs)

  def AggregatedList(self, *args, **kwargs):
    return self.zonal_service.AggregatedList(*args, **kwargs)

  def List(self, *args, **kwargs):
    return self.regional_service.List(*args, **kwargs)

  def ProcessHttpResponse(self, *args, **kwargs):
    return self.regional_service.ProcessHttpResponse(*args, **kwargs)
