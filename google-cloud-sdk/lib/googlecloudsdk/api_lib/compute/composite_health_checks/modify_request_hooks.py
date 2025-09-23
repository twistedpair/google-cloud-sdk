# -*- coding: utf-8 -*- #
# Copyright 2025 Google Inc. All Rights Reserved.
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
"""Modify request hooks, specifically for composite health checks."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from googlecloudsdk.core import resources


def add_name_to_payload(resource_ref, _, request_msg):
  """Modify the request message, carrying resource name into it.

  Args:
    resource_ref: the resource reference.
    request_msg: the request message constructed by the framework

  Returns:
    the modified request message.
  """
  request_msg.compositeHealthCheck.name = resource_ref.compositeHealthCheck
  return request_msg


def parse_health_sources(resource_ref, health_sources: list[str]):
  """Helper function for parsing the health_sources list.

  Args:
    resource_ref: the resource reference.
    health_sources: the list of health_sources to parse.

  Returns:
    the list of parsed health_sources self links.
  """

  result = []
  for source in health_sources:
    # If the source is a full URL, parse it as is. This is to support the case
    # where the resource is from a different API version.
    if '://' in source:
      result.append(source)
    # If the source is a relative path, parse it with the correct collection and
    # api version. This is to support the case where the resource is from a
    # different project or region.
    elif 'projects/' in source:
      result.append(
          resources.REGISTRY.Parse(
              source,
              collection='compute.regionHealthSources',
              api_version=resource_ref.GetCollectionInfo().api_version,
          ).SelfLink()
      )
    # Only the resource name is provided. Automatically assume the resource is
    # in the same project and region as the composite health check.
    else:
      result.append(
          resources.REGISTRY.Parse(
              source,
              collection='compute.regionHealthSources',
              api_version=resource_ref.GetCollectionInfo().api_version,
              params={
                  'project': resource_ref.project,
                  'region': resource_ref.region,
              },
          ).SelfLink()
      )
  return result


def parse_health_sources_create(
    resource_ref: resources.Resource,
    args,
    request_msg,
):
  """Modify the request message, parsing the health_sources list.

  Args:
    resource_ref: the resource reference.
    args: the arguments passed to the command.
    request_msg: the request message constructed by the framework.

  Returns:
    the modified request message.
  """
  if not args.health_sources:
    return request_msg

  request_msg.compositeHealthCheck.healthSources.clear()
  request_msg.compositeHealthCheck.healthSources.extend(
      parse_health_sources(resource_ref, args.health_sources)
  )
  return request_msg


def parse_health_sources_update(
    resource_ref: resources.Resource,
    args,
    request_msg,
):
  """Modify the request message, parsing the health_sources list.

  Args:
    resource_ref: the resource reference.
    args: the arguments passed to the command.
    request_msg: the request message constructed by the framework.

  Returns:
    the modified request message.
  """

  if not args.health_sources:
    return request_msg

  request_msg.compositeHealthCheckResource.healthSources.clear()
  request_msg.compositeHealthCheckResource.healthSources.extend(
      parse_health_sources(resource_ref, args.health_sources)
  )
  return request_msg


def parse_health_destination(resource_ref, health_destination: str):
  """Helper function for parsing the health destination string.

  Args:
    resource_ref: the resource reference.
    health_destination: the health destination string to parse.

  Returns:
    the parsed health destination self link.
  """

  # If the health destination is a full URL, parse it as is. This is to
  # support the case where the resource is from a different API version.
  if '://' in health_destination:
    return health_destination
  # If the health destination is a relative path, parse it with the correct
  # collection and api version. This is to support the case where the resource
  # is from a different project or region.
  elif 'projects/' in health_destination:
    return resources.REGISTRY.Parse(
        health_destination,
        collection='compute.forwardingRules',
        api_version=resource_ref.GetCollectionInfo().api_version,
    ).SelfLink()

  # Only the resource name is provided. Automatically assume the resource is
  # in the same project and region as the composite health check.
  return resources.REGISTRY.Parse(
      health_destination,
      collection='compute.forwardingRules',
      api_version=resource_ref.GetCollectionInfo().api_version,
      params={'project': resource_ref.project, 'region': resource_ref.region},
  ).SelfLink()


def parse_health_destination_create(
    resource_ref: resources.Resource,
    args,
    request_msg,
):
  """Modify the request message, parsing the health destination.

  Args:
    resource_ref: the resource reference.
    args: the arguments passed to the command.
    request_msg: the request message constructed by the framework.

  Returns:
    the modified request message.
  """
  if not args.health_destination:
    return request_msg

  request_msg.compositeHealthCheck.healthDestination = parse_health_destination(
      resource_ref, args.health_destination
  )
  return request_msg


def parse_health_destination_update(
    resource_ref: resources.Resource,
    args,
    request_msg,
):
  """Modify the request message, parsing the health destination.

  Args:
    resource_ref: the resource reference.
    args: the arguments passed to the command.
    request_msg: the request message constructed by the framework.

  Returns:
    the modified request message.
  """

  if not args.health_destination:
    return request_msg

  request_msg.compositeHealthCheckResource.healthDestination = (
      parse_health_destination(resource_ref, args.health_destination)
  )
  return request_msg
