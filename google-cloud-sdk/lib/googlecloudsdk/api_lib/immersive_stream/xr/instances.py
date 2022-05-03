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


def ValidateRealmExists(current_realm_configs, realm_configs_arg):
  """Validates the realm in the argument exists in current_realm_configs.

  Args:
    current_realm_configs: List of repeated RealmConfig proto messages. This
      should be the current realm configs of an existing instance.
    realm_configs_arg: List of a single realm config dict of the form:
        [{'realm': realm1, 'capacity': capacity1}]

  Returns:
    A boolean indicating if the realm argument exists in current_realm_configs.
  """
  new_realm_configs = ParseRealmConfigsFromArg(realm_configs_arg)
  if not new_realm_configs:
    return False
  return any((realm_config.realm == new_realm_configs[0].realm
              for realm_config in current_realm_configs))


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


def UpdateCapacity(instance_ref, current_instance, realm_configs):
  """Update capacity of a realm for an Immersive Stream for XR service instance.

  Args:
    instance_ref: resource object - service instance to be updated
    current_instance: instance object - current state of the service instance
      before update
    realm_configs: List of a single realm config dict of the form:
      [{'realm': realm1, 'capacity': capacity1}]. This specifies the deployment
        configuration of the instance in the realm.

  Returns:
    An Operation object which can be used to check on the progress of the
    service instance update.
  """
  client = api_util.GetClient()
  messages = api_util.GetMessages()
  service = client.ProjectsLocationsStreamInstancesService(client)
  new_realm_configs = ParseRealmConfigsFromArg(realm_configs)
  # TODO(b/230366148)
  if not new_realm_configs:
    raise exceptions.Error('Realm configs must not be empty')

  new_realm_config = ParseRealmConfigsFromArg(realm_configs)[0]

  instance = messages.StreamInstance()
  instance.realmConfigs = []
  for realm_config in current_instance.realmConfigs:
    if realm_config.realm == new_realm_config.realm:
      instance.realmConfigs.append(new_realm_config)
    else:
      instance.realmConfigs.append(realm_config)

  return service.Patch(
      messages.StreamProjectsLocationsStreamInstancesPatchRequest(
          name=instance_ref.RelativeName(),
          streamInstance=instance,
          updateMask='realm_configs'))


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
