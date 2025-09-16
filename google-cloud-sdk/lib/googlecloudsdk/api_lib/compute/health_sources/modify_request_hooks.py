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
"""Modify request hooks, specifically for health-sources."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from googlecloudsdk.core import resources


def add_name_to_payload(
    resource_ref: resources.Resource,
    _,
    request_msg,
):
  """Modify the request message, carrying resource name into it.

  Args:
    resource_ref: the resource reference.
    request_msg: the request message constructed by the framework

  Returns:
    the modified request message.
  """
  request_msg.healthSource.name = resource_ref.healthSource
  return request_msg


def parse_health_aggregation_policy(
    resource_ref, health_aggregation_policy: str
):
  """Helper function for parsing the health aggregation policy string.

  Args:
    resource_ref: the resource reference.
    health_aggregation_policy: the health aggregation policy string to parse.

  Returns:
    the parsed health aggregation policy self link.
  """

  # If the health aggregation policy is a self link, return it as is.
  # This is to support the case where the user specifies a health aggregation
  # policy from a different api version.
  if '://' in health_aggregation_policy:
    return health_aggregation_policy
  # If the health aggregation policy is a relative path, parse it with the
  # correct collection and api version. This is to support the case where the
  # resource is from a different project or region.
  elif 'projects/' in health_aggregation_policy:
    return resources.REGISTRY.Parse(
        health_aggregation_policy,
        collection='compute.regionHealthAggregationPolicies',
        api_version=resource_ref.GetCollectionInfo().api_version,
    ).SelfLink()
  # Only the resource name is provided. Automatically assume the resource is in
  # the same project and region as the health source.
  return resources.REGISTRY.Parse(
      health_aggregation_policy,
      collection='compute.regionHealthAggregationPolicies',
      api_version=resource_ref.GetCollectionInfo().api_version,
      params={'project': resource_ref.project, 'region': resource_ref.region},
  ).SelfLink()


def parse_health_aggregation_policy_create(
    resource_ref: resources.Resource,
    args,
    request_msg,
):
  """Modify the request message, parsing the health aggregation policy.

  Args:
    resource_ref: the resource reference.
    args: the arguments passed to the command.
    request_msg: the request message constructed by the framework

  Returns:
    the modified request message.
  """
  if not args.health_aggregation_policy:
    return request_msg

  request_msg.healthSource.healthAggregationPolicy = (
      parse_health_aggregation_policy(
          resource_ref, args.health_aggregation_policy
      )
  )
  return request_msg


def parse_health_aggregation_policy_update(
    resource_ref: resources.Resource,
    args,
    request_msg,
):
  """Modify the request message, parsing the health aggregation policy.

  Args:
    resource_ref: the resource reference.
    args: the arguments passed to the command.
    request_msg: the request message constructed by the framework

  Returns:
    the modified request message.
  """

  if not args.health_aggregation_policy:
    return request_msg

  request_msg.healthSourceResource.healthAggregationPolicy = (
      parse_health_aggregation_policy(
          resource_ref, args.health_aggregation_policy
      )
  )
  return request_msg


def parse_sources(resource_ref, sources: list[str]):
  """Helper function for parsing the sources list.

  Args:
    resource_ref: the resource reference.
    sources: the list of sources to parse.

  Returns:
    the list of parsed sources self links.
  """

  result = []
  for source in sources:
    # If the source is a self link, return it as is. This is to support the
    # case where the user specifies a source from a different api version.
    if '://' in source:
      result.append(source)
    # If the source is a relative path, parse it with the correct collection and
    # api version. This is to support the case where the resource is from a
    # different project or region.
    elif 'projects/' in source:
      result.append(
          resources.REGISTRY.Parse(
              source,
              collection='compute.regionBackendServices',
              api_version=resource_ref.GetCollectionInfo().api_version,
          ).SelfLink()
      )
    # Only the resource name is provided. Automatically assume the resource is
    # in the same project and region as the health source.
    else:
      result.append(
          resources.REGISTRY.Parse(
              source,
              collection='compute.regionBackendServices',
              api_version=resource_ref.GetCollectionInfo().api_version,
              params={
                  'project': resource_ref.project,
                  'region': resource_ref.region,
              },
          ).SelfLink()
      )
  return result


def parse_sources_create(
    resource_ref: resources.Resource,
    args,
    request_msg,
):
  """Modify the request message, parsing the sources list.

  Args:
    resource_ref: the resource reference.
    args: the arguments passed to the command.
    request_msg: the request message constructed by the framework

  Returns:
    the modified request message.
  """
  if not args.sources:
    return request_msg

  request_msg.healthSource.sources.clear()
  request_msg.healthSource.sources.extend(
      parse_sources(resource_ref, args.sources)
  )
  return request_msg


def parse_sources_update(
    resource_ref: resources.Resource,
    args,
    request_msg,
):
  """Modify the request message, parsing the sources list.

  Args:
    resource_ref: the resource reference.
    args: the arguments passed to the command.
    request_msg: the request message constructed by the framework

  Returns:
    the modified request message.
  """

  if not args.sources:
    return request_msg

  request_msg.healthSourceResource.sources.clear()
  request_msg.healthSourceResource.sources.extend(
      parse_sources(resource_ref, args.sources)
  )
  return request_msg
