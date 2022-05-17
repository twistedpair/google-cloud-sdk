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
"""Helper class to handle non-compute references."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib import network_security
from googlecloudsdk.api_lib import network_services


def BuildFullResourceUrl(base_uri, project_name, location, collection_name,
                         resource_name):
  """Creates a reference to a non-compute resource in the full URL format."""
  return '{}projects/{}/locations/{}/{}/{}'.format(base_uri, project_name,
                                                   location, collection_name,
                                                   resource_name)


def BuildServerTlsPolicyUrl(project_name, location, policy_name):
  return BuildFullResourceUrl(
      base_uri=network_security.GetApiBaseUrl(),
      project_name=project_name,
      location=location,
      collection_name='serverTlsPolicies',
      resource_name=policy_name)


def BuildServiceLbPolicyUrl(project_name, location, policy_name):
  return BuildFullResourceUrl(
      base_uri=network_services.GetApiBaseUrl(),
      project_name=project_name,
      location=location,
      collection_name='serviceLbPolicies',
      resource_name=policy_name)


def BuildServiceBindingUrl(project_name, location, binding_name):
  return BuildFullResourceUrl(
      base_uri=network_services.GetApiBaseUrl(
          network_services.base.ReleaseTrack.GA),
      project_name=project_name,
      location=location,
      collection_name='serviceBindings',
      resource_name=binding_name)


def CompareUrlRelativeReferences(url1, url2):
  """Compares relative resource references (skips namespace)."""
  return url1.split('projects')[1] == url2.split('projects')[1]


def UrlInReferences(url, references):
  return bool(
      list(
          filter(lambda ref: CompareUrlRelativeReferences(url, ref),
                 references)))


def FilterReferences(references, references_to_remove):
  return list(
      filter(lambda ref: not (UrlInReferences(ref, references_to_remove)),
             references))
