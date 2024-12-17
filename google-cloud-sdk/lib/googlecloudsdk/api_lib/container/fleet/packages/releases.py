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
"""Utilities for Package Rollouts Releases API."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.fleet.packages import variants as variants_apis
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import resources

_LIST_REQUEST_BATCH_SIZE_ATTRIBUTE = 'pageSize'
_VARIANT_STORAGE_STRATEGY_LABEL_KEY = 'configdelivery-variant-storage-strategy'
_VARIANT_STORAGE_STRATEGY_LABEL_VALUE_NESTED = 'nested'


def GetClientInstance(no_http=False):
  """Returns instance of generated Config Delivery gapic client."""
  return apis.GetClientInstance('configdelivery', 'v1alpha', no_http=no_http)


def GetMessagesModule(client=None):
  """Returns generated Config Delivery gapic messages."""
  client = client or GetClientInstance()
  return client.MESSAGES_MODULE


def GetReleaseURI(resource):
  """Returns URI of Release for use with gapic client."""
  release = resources.REGISTRY.ParseRelativeName(
      resource.name,
      collection='configdelivery.projects.locations.resourceBundles.releases',
  )
  return release.SelfLink()


def _ParentPath(project, location, parent_bundle):
  return (
      f'projects/{project}/locations/{location}/resourceBundles/{parent_bundle}'
  )


def _FullyQualifiedPath(project, location, resource_bundle, release):
  name = release.replace('.', '-')
  return f'projects/{project}/locations/{location}/resourceBundles/{resource_bundle}/releases/{name}'


class ReleasesClient(object):
  """Client for Releases in Config Delivery Package Rollouts API."""

  def __init__(self, client=None, messages=None):
    self.client = client or GetClientInstance()
    self.messages = messages or GetMessagesModule(client)
    self._service = self.client.projects_locations_resourceBundles_releases
    self.release_waiter = waiter.CloudOperationPollerNoResources(
        operation_service=self.client.projects_locations_operations,
        get_name_func=lambda x: x.name,
    )

  def GetLifecycleEnum(self, lifecycle_str):
    """Converts input-format lifecycle to internal enum."""
    if lifecycle_str and lifecycle_str.upper() == 'DRAFT':
      return self.messages.Release.LifecycleValueValuesEnum.DRAFT
    else:
      return self.messages.Release.LifecycleValueValuesEnum.PUBLISHED

  def _VariantsValueFromInputVariants(self, variants):
    """Converts input-format variants to internal variant objects.

    Args:
      variants: input-format variants

    Returns:
      A VariantsValue object, that contains a list of variants. To be used in
      API requests.
    """
    additional_properties = []
    for variant_entry in variants:
      variant = self.messages.Variant(
          labels=None, resources=variants[variant_entry]
      )
      if len(variants) == 1:
        additional_properties.append(
            self.messages.Release.VariantsValue.AdditionalProperty(
                key='default', value=variant
            )
        )
      else:
        additional_properties.append(
            self.messages.Release.VariantsValue.AdditionalProperty(
                key=variant_entry, value=variant
            )
        )
    return self.messages.Release.VariantsValue(
        additionalProperties=additional_properties
    )

  def List(self, project, location, parent_bundle, limit=None, page_size=100):
    """List Releases of a ResourceBundle.

    Args:
      project: GCP project id.
      location: Valid GCP location (e.g. us-central1).
      parent_bundle: Name of parent ResourceBundle.
      limit: int or None, the total number of results to return.
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results).

    Returns:
      Generator of matching devices.
    """
    list_request = self.messages.ConfigdeliveryProjectsLocationsResourceBundlesReleasesListRequest(
        parent=_ParentPath(project, location, parent_bundle)
    )
    return list_pager.YieldFromList(
        self._service,
        list_request,
        field='releases',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute=_LIST_REQUEST_BATCH_SIZE_ATTRIBUTE,
    )

  def Create(
      self,
      resource_bundle,
      version,
      project,
      location,
      lifecycle=None,
      variants=None,
      use_nested_variants=False,
      clh_variants=False,
  ):
    """Create Release for a ResourceBundle.

    Args:
      resource_bundle: Name of parent ResourceBundle.
      version: Version of the Release.
      project: GCP Project ID.
      location: Valid GCP location (e.g., uc-central1)
      lifecycle: Lifecycle of the Release.
      variants: Variants of the Release.
      use_nested_variants: Whether to create nested variant resources.
      clh_variants: Boolean flag to create variants sent in the request as a
        separate resource.

    Returns:
      Created Release resource.
    """
    fully_qualified_path = _FullyQualifiedPath(
        project, location, resource_bundle, version
    )
    variants_value = self._VariantsValueFromInputVariants(variants)
    if not use_nested_variants:
      # Obsolete behavior, create Release with variants sent inline
      labels_value = None
      if clh_variants:
        labels_value = self.messages.Release.LabelsValue(
            additionalProperties=[
                self.messages.Release.LabelsValue.AdditionalProperty(
                    key='configdelivery-variant-storage-strategy',
                    value='nested',
                )
            ]
        )
      release = self.messages.Release(
          name=fully_qualified_path,
          labels=labels_value,
          lifecycle=self.GetLifecycleEnum(lifecycle),
          variants=variants_value,
          version=version,
      )
      create_request = self.messages.ConfigdeliveryProjectsLocationsResourceBundlesReleasesCreateRequest(
          parent=_ParentPath(project, location, resource_bundle),
          release=release,
          releaseId=version.replace('.', '-'),
      )
      return waiter.WaitFor(
          self.release_waiter,
          self._service.Create(create_request),
          f'Creating Release {fully_qualified_path}',
      )
    # Create Draft Release, create nested Variant resources, then updates
    # release to have those variants. Publishes release at update step, if
    # necessary.
    labels = self.messages.Release.LabelsValue(
        additionalProperties=[
            self.messages.Release.LabelsValue.AdditionalProperty(
                key=_VARIANT_STORAGE_STRATEGY_LABEL_KEY,
                value=_VARIANT_STORAGE_STRATEGY_LABEL_VALUE_NESTED,
            )
        ]
    )
    release = self.messages.Release(
        name=fully_qualified_path,
        labels=labels,
        lifecycle=self.GetLifecycleEnum('DRAFT'),
        version=version,
    )
    create_request = self.messages.ConfigdeliveryProjectsLocationsResourceBundlesReleasesCreateRequest(
        parent=_ParentPath(project, location, resource_bundle),
        release=release,
        releaseId=version.replace('.', '-'),
    )
    _ = waiter.WaitFor(
        self.release_waiter,
        self._service.Create(create_request),
        f'Creating Release {fully_qualified_path}',
    )
    full_variant_names = {}
    for variant, variant_resources in variants.items():
      variants_client = variants_apis.VariantsClient()
      variants_client.Create(
          resource_bundle=resource_bundle,
          release=version.replace('.', '-'),
          name=variant,
          project=project,
          location=location,
          variant_resources=variant_resources,
      )
      full_name = variants_apis.GetFullyQualifiedPath(
          project,
          location,
          resource_bundle,
          version.replace('.', '-'),
          variant,
      )
      full_variant_names[full_name] = ['...']
    return self.Update(
        release=version,
        project=project,
        location=location,
        resource_bundle=resource_bundle,
        labels=labels,
        lifecycle=lifecycle,
        variants=full_variant_names,
    )

  def Delete(self, project, location, resource_bundle, release, force=False):
    """Delete a Release resource.

    Args:
      project: GCP project ID.
      location: GCP location of Release.
      resource_bundle: Name of ResourceBundle.
      release: Name of Release.
      force: Whether to force deletion of any child variants.

    Returns:
      Empty Response Message.
    """
    fully_qualified_path = _FullyQualifiedPath(
        project,
        location,
        resource_bundle,
        release,
    )
    delete_req = self.messages.ConfigdeliveryProjectsLocationsResourceBundlesReleasesDeleteRequest(
        name=fully_qualified_path,
        force=force,
    )
    return waiter.WaitFor(
        self.release_waiter,
        self._service.Delete(delete_req),
        f'Deleting Release {fully_qualified_path}',
    )

  def Describe(self, project, location, resource_bundle, release):
    """Describe a Release resource.

    Args:
      project: GCP project ID.
      location: GCP location of Release.
      resource_bundle: Name of ResourceBundle.
      release: Name of Release.

    Returns:
      Requested Release resource.
    """
    fully_qualified_path = _FullyQualifiedPath(
        project, location, resource_bundle, release
    )
    describe_req = self.messages.ConfigdeliveryProjectsLocationsResourceBundlesReleasesGetRequest(
        name=fully_qualified_path
    )
    return self._service.Get(describe_req)

  def Update(
      self,
      release,
      project,
      location,
      resource_bundle,
      labels=None,
      lifecycle=None,
      variants=None,
      update_mask=None,
  ):
    """Update Release for a ResourceBundle.

    Args:
      release: Name of Release (e.g., v1).
      project: GCP project ID.
      location: GCP location of Release.
      resource_bundle: Name of parent ResourceBundle.
      labels: Labels of the Release.
      lifecycle: Lifecycle of the Release.
      variants: Variants of the Release.
      update_mask: Fields to be updated.

    Returns:
      Updated Release resource.
    """
    fully_qualified_path = _FullyQualifiedPath(
        project, location, resource_bundle, release
    )
    variants_value = self._VariantsValueFromInputVariants(variants)
    release = self.messages.Release(
        name=fully_qualified_path,
        labels=labels,
        lifecycle=self.GetLifecycleEnum(lifecycle),
        variants=variants_value,
        version=release,
    )
    update_request = self.messages.ConfigdeliveryProjectsLocationsResourceBundlesReleasesPatchRequest(
        name=fully_qualified_path, release=release, updateMask=update_mask
    )
    return waiter.WaitFor(
        self.release_waiter,
        self._service.Patch(update_request),
        f'Updating Release {fully_qualified_path}',
    )
