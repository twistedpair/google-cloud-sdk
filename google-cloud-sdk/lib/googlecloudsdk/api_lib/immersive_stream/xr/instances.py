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
from googlecloudsdk.core import properties


def ProjectLocation(project, location):
  return 'projects/{}/locations/{}'.format(project, location)


def ParseRealmConfigsFromArg(realm_configs_arg):
  """Converts realm configs arguments into a list of RealmConfig proto messages.

  Args:
    realm_configs_arg: List of realm config dicts of the form:
        [{'realm': realm1, 'capacity': capacity1}, ...] It is expected that the
          realms are valid RealmValueValuesEnum instances and capacities are
          string representations of integer values

  Returns:
    A list of repeated RealmConfig proto messages
  """
  messages = api_util.GetMessages()

  realm_configs = []
  for realm_config in realm_configs_arg:
    realm = messages.RealmConfig.RealmValueValuesEnum(realm_config['realm'])
    realm_configs.append(
        messages.RealmConfig(
            realm=realm, capacity=int(realm_config['capacity'])))
  return realm_configs


def Create(instance_name, content, location, version, realm_configs):
  """Create a new Immersive Stream for XR service instance.

  Args:
    instance_name: string - name of the service instance
    content: string - resource path of the content resource that is served by
      the instance
    location: string - location where the resource will be created
    version: string - content build version tag
    realm_configs: List of realm config dicts of the form:
      [{'realm': realm1, 'capacity': capacity1}, ...] These specify the
        deployment configuration of the instance in realms.

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
      realmConfigs=ParseRealmConfigsFromArg(realm_configs))
  service = client.ProjectsLocationsStreamInstancesService(client)
  return service.Create(
      messages.StreamProjectsLocationsStreamInstancesCreateRequest(
          parent=ProjectLocation(properties.VALUES.core.project.Get(),
                                 location),
          streamInstance=instance,
          streamInstanceId=instance_name))
