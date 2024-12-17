# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Utilities for Package Rollouts Variants API."""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import resources

_LIST_REQUEST_BATCH_SIZE_ATTRIBUTE = 'pageSize'


def GetClientInstance(no_http=False):
  """Returns instance of generated Config Delivery gapic client."""
  return apis.GetClientInstance('configdelivery', 'v1alpha', no_http=no_http)


def GetMessagesModule(client=None):
  """Returns generated Config Delivery gapic messages."""
  client = client or GetClientInstance()
  return client.MESSAGES_MODULE


def GetVariantURI(resource):
  """Returns URI of Variant for use with gapic client."""
  variant = resources.REGISTRY.ParseRelativeName(
      resource.name,
      collection=(
          'configdelivery.projects.locations.resourceBundles.releases.variants'
      ),
  )
  return variant.SelfLink()


def _ParentPath(project, location, parent_bundle, parent_release):
  return f'projects/{project}/locations/{location}/resourceBundles/{parent_bundle}/releases/{parent_release}'


def _FullyQualifiedPath(project, location, resource_bundle, release, variant):
  name = release.replace('.', '-')
  return f'projects/{project}/locations/{location}/resourceBundles/{resource_bundle}/releases/{name}/variants/{variant}'


def GetFullyQualifiedPath(project, location, resource_bundle, release, variant):
  return _FullyQualifiedPath(
      project, location, resource_bundle, release, variant
  )


class VariantsClient(object):
  """Client for Variants in Config Delivery Package Rollouts API."""

  def __init__(self, client=None, messages=None):
    self.client = client or GetClientInstance()
    self.messages = messages or GetMessagesModule(client)
    self._service = (
        self.client.projects_locations_resourceBundles_releases_variants
    )
    self.variant_waiter = waiter.CloudOperationPollerNoResources(
        operation_service=self.client.projects_locations_operations,
        get_name_func=lambda x: x.name,
    )

  def Create(
      self,
      resource_bundle,
      release,
      name,
      project,
      location,
      variant_resources=None,
  ):
    """Create Variant for a Release.

    Args:
      resource_bundle: Name of parent ResourceBundle.
      release: Name of parent Release.
      name: Name of the Variant.
      project: GCP Project ID.
      location: Valid GCP location (e.g., uc-central1)
      variant_resources: Resources of the Variant.

    Returns:
      Created Variant resource.
    """
    fully_qualified_path = _FullyQualifiedPath(
        project, location, resource_bundle, release, name
    )
    variant = self.messages.Variant(
        name=fully_qualified_path,
        labels=None,
        resources=variant_resources,
    )
    create_request = self.messages.ConfigdeliveryProjectsLocationsResourceBundlesReleasesVariantsCreateRequest(
        parent=_ParentPath(project, location, resource_bundle, release),
        variant=variant,
        variantId=name,
    )
    return waiter.WaitFor(
        self.variant_waiter,
        self._service.Create(create_request),
        f'Creating Variant {fully_qualified_path}',
    )
