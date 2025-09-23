# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Utilities for the cloud deploy custom target type resource."""


from googlecloudsdk.api_lib.clouddeploy import custom_target_type
from googlecloudsdk.core import resources


def CustomTargetTypeReference(name, project, region):
  """Creates the custom target type reference base on the parameters.

    Returns the shared custom target type reference.

  Args:
    name: str, custom target type ID
    project: str,project number or ID.
    region: str, region ID.

  Returns:
    custom target type reference.
  """
  return resources.REGISTRY.Parse(
      name,
      collection='clouddeploy.projects.locations.customTargetTypes',
      params={
          'projectsId': project,
          'locationsId': region,
          'customTargetTypesId': name,
      },
  )


def PatchCustomTargetType(resource):
  """Patches a custom target type resource.

  Args:
    resource: apitools.base.protorpclite.messages.Message, custom target type
      message.

  Returns:
    The operation message
  """
  return custom_target_type.CustomTargetTypesClient().Patch(resource)


def DeleteCustomTargetType(name):
  """Deletes a custom target type resource.

  Args:
    name: str, custom target type name.

  Returns:
    The operation message
  """
  return custom_target_type.CustomTargetTypesClient().Delete(name)
