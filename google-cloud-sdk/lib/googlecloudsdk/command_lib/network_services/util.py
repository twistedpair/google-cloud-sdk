# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utilities for networkservices commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib import network_services as ns_api
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import multitype
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.core import properties


def ConstructServiceBindingServiceNameFromArgs(unused_ref, args, request):
  """Constructs ServiceBinding service name from args."""
  sd_service_name = (
      'projects/'
      + properties.VALUES.core.project.Get()
      + '/locations/'
      + args.service_directory_region
      + '/namespaces/'
      + args.service_directory_namespace
      + '/services/'
      + args.service_directory_service
  )
  arg_utils.SetFieldInMessage(
      request, 'serviceBinding.service', sd_service_name
  )
  return request


def AutoCapacityDrainHook(api_version='v1'):
  """Hook to transform AutoCapacityDrain flag to actual message.

  This function is called during ServiceLbPolicy create/update command to
  create the AutoCapacityDrain message. It returns a function which is called
  with arguments passed in the gcloud command.

  Args:
    api_version: Version of the networkservices api

  Returns:
     Function to transform boolean flag to AutcapacityDrain message.
  """
  messages = apis.GetMessagesModule('networkservices', api_version)

  def ConstructAutoCapacityDrain(enable):
    if enable:
      return messages.ServiceLbPolicyAutoCapacityDrain(enable=enable)

  return ConstructAutoCapacityDrain


def FailoverHealthThresholdHook(api_version='v1'):
  """Hook to transform FailoverHealthThreshold flag to actual message.

  This function is called during ServiceLbPolicy create/update command to
  create the FailoverConfig message. It returns a function which is called
  with arguments passed in the gcloud command.

  Args:
    api_version: Version of the networkservices api

  Returns:
     Function to transform integer flag to FailoverConfig message.
  """
  messages = apis.GetMessagesModule('networkservices', api_version)

  def ConstructFailoverConfig(threshold):
    return messages.ServiceLbPolicyFailoverConfig(
        failoverHealthThreshold=threshold
    )

  return ConstructFailoverConfig


def ListRouteViews(track, name, page_size=100, limit=None):
  """Calls appropriate List method based on the name."""
  if 'meshes' in name:
    return _ListMeshRouteViews(track, name, page_size, limit)
  elif 'gateways' in name:
    return _ListGatewayRouteViews(track, name, page_size, limit)
  else:
    raise ValueError('Invalid name: %s' % name)


def _ListMeshRouteViews(track, name, page_size=100, limit=None):
  """Calls ListMeshRouteViews API."""
  client = ns_api.GetClientInstance(track)
  msg = ns_api.GetMessagesModule(track)
  request = msg.NetworkservicesProjectsLocationsMeshesRouteViewsListRequest(
      parent=name
  )
  return list_pager.YieldFromList(
      service=client.projects_locations_meshes_routeViews,
      request=request,
      field='meshRouteViews',
      batch_size=page_size,
      limit=limit,
      batch_size_attribute='pageSize',
  )


def _ListGatewayRouteViews(track, name, page_size=100, limit=None):
  """Calls ListGatewayRouteViews API."""
  client = ns_api.GetClientInstance(track)
  msg = ns_api.GetMessagesModule(track)
  request = msg.NetworkservicesProjectsLocationsGatewaysRouteViewsListRequest(
      parent=name
  )

  # return client.projects_locations_gateways_routeViews.List(request)
  return list_pager.YieldFromList(
      service=client.projects_locations_gateways_routeViews,
      request=request,
      field='gatewayRouteViews',
      batch_size=page_size,
      limit=limit,
      batch_size_attribute='pageSize',
  )


def GetRouteView(track, name):
  """Calls appropriate Get method based on the name."""
  if 'meshes' in name:
    return _GetMeshRouteView(track, name)
  elif 'gateways' in name:
    return _GetGatewayRouteView(track, name)
  else:
    raise ValueError('Invalid name: %s' % name)


def _GetMeshRouteView(track, name):
  client = ns_api.GetClientInstance(track)
  msg = ns_api.GetMessagesModule(track)
  request = msg.NetworkservicesProjectsLocationsMeshesRouteViewsGetRequest(
      name=name
  )
  return client.projects_locations_meshes_routeViews.Get(request)


def _GetGatewayRouteView(track, name):
  client = ns_api.GetClientInstance(track)
  msg = ns_api.GetMessagesModule(track)
  request = msg.NetworkservicesProjectsLocationsGatewaysRouteViewsGetRequest(
      name=name
  )
  return client.projects_locations_gateways_routeViews.Get(request)


def LocationResourceSpec():
  """Reads the gateway route view resource spec from the yaml file."""
  data = yaml_data.ResourceYAMLData.FromPath('network_services.location')
  return concepts.ResourceSpec.FromYaml(data.GetData())


def MeshResourceSpec():
  """Reads the mesh resource spec from the yaml file."""
  data = yaml_data.ResourceYAMLData.FromPath('network_services.mesh')
  return concepts.ResourceSpec.FromYaml(data.GetData())


def GatewayResourceSpec():
  """Reads the gateway resource spec from the yaml file."""
  data = yaml_data.ResourceYAMLData.FromPath('network_services.gateway')
  return concepts.ResourceSpec.FromYaml(data.GetData())


def IsFullyQualifiedName(name):
  """Returns whether name is a fully qualified name."""
  return (
      'projects/' in name
      and 'locations' in name
      and ('meshes' in name or 'gateways' in name)
  )


def LocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='Location of the {resource}',
  )


def MeshAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='mesh',
      help_text='Parent Mesh of the {resource}',
  )


def GatewayAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='gateway',
      help_text='Parent Gateway of the {resource}',
  )


def RouteViewAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='route-view',
      help_text='The RouteView resource',
  )


def MeshRouteViewResourceSpec():
  return concepts.ResourceSpec(
      'networkservices.projects.locations.meshes.routeViews',
      resource_name='route-view',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      meshesId=MeshAttributeConfig(),
      routeViewsId=RouteViewAttributeConfig(),
      api_version='v1alpha1',
      is_positional=True,
  )


def GatewayRouteViewResourceSpec():
  return concepts.ResourceSpec(
      'networkservices.projects.locations.gateways.routeViews',
      resource_name='route-view',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      gatewaysId=GatewayAttributeConfig(),
      routeViewsId=RouteViewAttributeConfig(),
      api_version='v1alpha1',
      is_positional=True,
  )


def MeshOrGatewayRouteViewResourceSpec():
  return multitype.MultitypeResourceSpec(
      'mesh_or_gateway_route_view',
      MeshRouteViewResourceSpec(),
      GatewayRouteViewResourceSpec(),
      allow_inactive=True,
  )
