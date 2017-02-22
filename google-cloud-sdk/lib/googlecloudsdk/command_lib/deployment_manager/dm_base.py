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

"""Base functions for DM commands targeting the v2 API."""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import properties
from googlecloudsdk.core import resolvers
from googlecloudsdk.core import resources


def GetMessages():
  return apis.GetMessagesModule('deploymentmanager', 'v2')


def GetClient():
  return apis.GetClientInstance('deploymentmanager', 'v2')


def GetProject():
  return properties.VALUES.core.project.Get(required=True)


def GetResources():
  resolver = resolvers.FromProperty(properties.VALUES.core.project)
  resources.REGISTRY.SetParamDefault('deploymentmanager',
                                     None,
                                     'project',
                                     resolver)
  return resources.REGISTRY
