# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Commands for interacting with Immersive Stream for XR service instances."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.immersive_stream.xr import api_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties


def ProjectLocation(project, location):
  return 'projects/{}/locations/{}'.format(project, location)


def ParseLocationConfigsFromArg(region_configs_arg):
  """Converts region configs args into a LocationConfigsValue proto message.

  Args:
    region_configs_arg: List of region config dicts of the form: [{'region':
      region1, 'capacity': capacity1}, ...]. Both region and capacity fields are
      in string format.

  Returns:
    A LocationConfigsValue proto message.
  """
  messages = api_util.GetMessages()

  location_configs_value = messages.StreamInstance.LocationConfigsValue()
  for region_config in region_configs_arg:
    region = region_config['region']
    capacity = int(region_config['capacity'])
    location_config = messages.LocationConfig(
        location=region, capacity=capacity)
    location_configs_value.additionalProperties.append(
        messages.StreamInstance.LocationConfigsValue.AdditionalProperty(
            key=region, value=location_config))

  return location_configs_value


def Get(instance_relative_name):
  """Get resource details of an Immersive Stream for XR service instance.

  Args:
    instance_relative_name: string - canonical resource name of the instance

  Returns:
    A service instance resource object.
  """
  client = api_util.GetClient()
  messages = api_util.GetMessages()
  service = client.ProjectsLocationsStreamInstancesService(client)

  return service.Get(
      messages.StreamProjectsLocationsStreamInstancesGetRequest(
          name=instance_relative_name))


def Create(instance_name, content, location, version, region_configs):
  """Create a new Immersive Stream for XR service instance.

  Args:
    instance_name: string - name of the service instance
    content: string - resource path of the content resource that is served by
      the instance
    location: string - location where the resource will be created
    version: string - content build version tag
    region_configs: List of region config dicts of the form: [{'region':
      region1, 'capacity': capacity1}, ...] These specify the deployment
      configuration of the instance in regions.

  Returns:
    An Operation object which can be used to check on the progress of the
    service instance creation.
  """
  client = api_util.GetClient()
  messages = api_util.GetMessages()
  build_version = messages.BuildVersion(contentVersionTag=version)

  instance = messages.StreamInstance(
      content=content,
      contentBuildVersion=build_version,
      name=instance_name,
      locationConfigs=ParseLocationConfigsFromArg(region_configs))
  service = client.ProjectsLocationsStreamInstancesService(client)
  return service.Create(
      messages.StreamProjectsLocationsStreamInstancesCreateRequest(
          parent=ProjectLocation(properties.VALUES.core.project.Get(),
                                 location),
          streamInstance=instance,
          streamInstanceId=instance_name))


def UpdateCapacity(instance_ref, current_instance, region_configs):
  """Update capacity of a region for an Immersive Stream for XR service instance.

  Args:
    instance_ref: resource object - service instance to be updated
    current_instance: instance object - current state of the service instance
      before update
    region_configs: List of a single region config dict of the form: [{'region':
      region1, 'capacity': capacity1}]. This specifies the deployment
      configuration of the instance in the region.

  Returns:
    An Operation object which can be used to check on the progress of the
    service instance update.
  """
  client = api_util.GetClient()
  messages = api_util.GetMessages()
  service = client.ProjectsLocationsStreamInstancesService(client)
  # TODO(b/230366148)
  if not region_configs:
    raise exceptions.Error('Region configs must not be empty')
  new_location_configs = ParseLocationConfigsFromArg(region_configs)

  # Stores current location_configs into a dict
  location_configs_dict = {}
  for location_config in current_instance.locationConfigs.additionalProperties:
    location_configs_dict[location_config.key] = location_config.value

  # Merges current location_configs with new location_configs
  for location_config in new_location_configs.additionalProperties:
    if location_config.key not in location_configs_dict:
      error_message = (
          '{} is not an existing region for instance {}. Capacity'
          ' updates can only be applied to existing regions, '
          'adding a new region is not currently supported.').format(
              location_config.key, instance_ref.RelativeName())
      # TODO(b/240487545): create ISXR own subclass of exceptions.
      raise exceptions.Error(error_message)
    location_configs_dict[location_config.key] = location_config.value

  # Puts merged location_configs into a StreamInstance
  instance = messages.StreamInstance()
  instance.locationConfigs = messages.StreamInstance.LocationConfigsValue()
  # NOTE: we need this sort to make sure the order is fixed. Otherwise, tests
  # may pass in one platform but fail in another one.
  for key in sorted(location_configs_dict):
    location_config = location_configs_dict[key]
    item = messages.StreamInstance.LocationConfigsValue.AdditionalProperty(
        key=location_config.location, value=location_config)
    instance.locationConfigs.additionalProperties.append(item)

  return service.Patch(
      messages.StreamProjectsLocationsStreamInstancesPatchRequest(
          name=instance_ref.RelativeName(),
          streamInstance=instance,
          updateMask='location_configs'))


def UpdateContentBuildVersion(instance_ref, version):
  """Update content build version of an Immersive Stream for XR service instance.

  Args:
    instance_ref: resource object - service instance to be updated
    version: string - content build version tag

  Returns:
    An Operation object which can be used to check on the progress of the
    service instance update.
  """
  client = api_util.GetClient()
  messages = api_util.GetMessages()
  service = client.ProjectsLocationsStreamInstancesService(client)

  build_version = messages.BuildVersion(contentVersionTag=version)
  instance = messages.StreamInstance()
  instance.contentBuildVersion = build_version
  return service.Patch(
      messages.StreamProjectsLocationsStreamInstancesPatchRequest(
          name=instance_ref.RelativeName(),
          streamInstance=instance,
          updateMask='content_build_version'))
