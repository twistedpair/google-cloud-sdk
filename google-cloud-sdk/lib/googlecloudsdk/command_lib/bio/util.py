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

"""Common utility functions for all bio commands."""

from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


BIO_API_VERSION = 'v1'


def ParseOperation(name):
  """Parse an operation name and return an operation resource object.

  The input operation name can be of the form:
    <operation-name>
    https://bio.googleapis.com/v1/projects/<project>/operations/<operation-name>

  Args:
    name: The operation name in one of the supported formats

  Returns:
    Resource: resource object of the operation
  """
  return resources.REGISTRY.Parse(
      name,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='bio.projects.operations')


def _GetUri(resource, undefined=None):
  """Transforms an operations resource item to a URI."""
  ref = ParseOperation(resource.name)
  return ref.SelfLink() or undefined


def GetTransforms():
  """Returns the bio display transforms table."""
  return {
      'uri': _GetUri,
  }
