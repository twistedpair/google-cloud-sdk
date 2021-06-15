# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Base classes for [enable|disable|describe] commands for Feature resource."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.services import enable_api
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.api_lib.util import exceptions as core_api_exceptions
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.container.hub import base as hub_base
from googlecloudsdk.command_lib.container.hub.features import info
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import retry


class FeatureCommand(hub_base.HubCommand):
  """FeatureCommand is a mixin adding common utils to the Feature commands."""
  feature_name = ''  # Derived commands should set this to their Feature.

  @property
  def feature(self):
    """The Feature info entry for this command's Feature."""
    return info.Get(self.feature_name)

  def FeatureResourceName(self):
    """Builds the full resource name, using the core project property."""
    return super(FeatureCommand, self).FeatureResourceName(self.feature_name)

  def FeatureNotEnabledError(self):
    """Constructs a new Error for reporting when this Feature is not enabled."""
    project = properties.VALUES.core.project.GetOrFail()
    return exceptions.Error('{} Feature for project [{}] is not enabled'.format(
        self.feature.display_name, project))

  def GetFeature(self):
    """Fetch this command's Feature from the API, handling common errors."""
    try:
      return self.hubclient.GetFeature(self.FeatureResourceName())
    except apitools_exceptions.HttpNotFoundError:
      raise self.FeatureNotEnabledError()


class EnableCommand(FeatureCommand, base.CreateCommand):
  """Base class for the command that enables a Feature."""

  def RunCommand(self, args, **kwargs):
    project = properties.VALUES.core.project.GetOrFail()
    enable_api.EnableServiceIfDisabled(project, self.feature.api)
    try:
      # Retry if we still get "API not activated"; it can take a few minutes
      # for Chemist to catch up. See b/28800908.
      # TODO(b/177098463): Add a spinner here?
      retryer = retry.Retryer(max_retrials=4, exponential_sleep_multiplier=1.75)
      return retryer.RetryOnException(
          CreateFeature,
          args=(project, self.feature_name, self.feature.display_name),
          kwargs=kwargs,
          should_retry_if=self._FeatureAPINotEnabled,
          sleep_ms=1000)
    except retry.MaxRetrialsException:
      raise exceptions.Error(
          'Retry limit exceeded waiting for {} to enable'.format(
              self.feature.api))
    except apitools_exceptions.HttpConflictError as e:
      # If the error is not due to the object already existing, re-raise.
      error = core_api_exceptions.HttpErrorPayload(e)
      if error.status_description != 'ALREADY_EXISTS':
        raise
      log.status.Print('{} Feature for project [{}] is already enabled'.format(
          self.feature.display_name, project))

  def _FeatureAPINotEnabled(self, exc_type, exc_value, traceback, state):
    del traceback, state  # Unused
    if exc_type != apitools_exceptions.HttpBadRequestError:
      return False
    error = core_api_exceptions.HttpErrorPayload(exc_value)
    # TODO(b/188807249): Add a reference to this error in the error package.
    if not (error.status_description == 'FAILED_PRECONDITION' and
            self.feature.api in error.message and
            'is not enabled' in error.message):
      return False
    log.status.Print('Waiting for service API enablement to finish...')
    return True


class DisableCommand(FeatureCommand, base.DeleteCommand):
  """Base class for the command that disables a Feature."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--force',
        action='store_true',
        help='Disable this feature, even if it is currently in use. '
        'Force disablement may result in unexpected behavior.')

  def Run(self, args):
    return self.Disable(args.force)

  def Disable(self, force):
    try:
      op = self.hubclient.DeleteFeature(self.FeatureResourceName(), force=force)
    except apitools_exceptions.HttpNotFoundError:
      return  # Already disabled.
    message = 'Waiting for Feature {} to be deleted'.format(
        self.feature.display_name)
    self.WaitForHubOp(
        self.hubclient.resourceless_waiter, op, message=message, warnings=False)


class DescribeCommand(FeatureCommand, base.DescribeCommand):
  """Base class for the command that describes the status of a Feature."""

  def Run(self, args):
    project_id = properties.VALUES.core.project.GetOrFail()
    name = 'projects/{0}/locations/global/features/{1}'.format(
        project_id, self.feature_name)
    return GetFeature(name)


class UpdateCommand(FeatureCommand, base.UpdateCommand):
  """Base class for the command that updates a Feature."""

  def RunCommand(self, mask, **kwargs):
    project = properties.VALUES.core.project.GetOrFail()
    return UpdateFeature(project, self.feature_name, self.feature.display_name,
                         mask, **kwargs)


def CreateMultiClusterIngressFeatureSpec(config_membership):
  client = core_apis.GetClientInstance('gkehub', 'v1alpha1')
  messages = client.MESSAGES_MODULE
  spec = messages.MultiClusterIngressFeatureSpec(
      configMembership=config_membership)
  return spec


def CreateMultiClusterServiceDiscoveryFeatureSpec():
  client = core_apis.GetClientInstance('gkehub', 'v1alpha1')
  messages = client.MESSAGES_MODULE
  return messages.MultiClusterServiceDiscoveryFeatureSpec()


def CreateServiceDirectoryFeatureSpec():
  client = core_apis.GetClientInstance('gkehub', 'v1alpha1')
  messages = client.MESSAGES_MODULE
  return messages.ServiceDirectoryFeatureSpec()


def CreateConfigManagementFeatureSpec():
  client = core_apis.GetClientInstance('gkehub', 'v1alpha1')
  messages = client.MESSAGES_MODULE
  empty_config_map = messages.ConfigManagementFeatureSpec.MembershipConfigsValue(
      additionalProperties=[])
  return messages.ConfigManagementFeatureSpec(
      membershipConfigs=empty_config_map)


def CreateIdentityServiceFeatureSpec():
  """Creates an empty Hub Feature Spec for the Anthos Identity Service.

  Returns:
    The empty Anthos Identity Service Hub Feature Spec.
  """
  client = core_apis.GetClientInstance('gkehub', 'v1alpha1')
  messages = client.MESSAGES_MODULE
  return messages.IdentityServiceFeatureSpec()


def CreateServiceMeshFeatureSpec():
  """Creates an empty Hub Feature Spec for the Service Mesh Feature.

  Returns:
    The empty Service Mesh Hub Feature Spec.
  """
  client = core_apis.GetClientInstance('gkehub', 'v1alpha1')
  messages = client.MESSAGES_MODULE
  return messages.ServiceMeshFeatureSpec()


def CreateAppDevExperienceFeatureSpec():
  """Creates an empty Hub Feature Spec for the CloudRun Service.

  Returns:
    The empty CloudRun Hub Feature Spec.
  """
  client = core_apis.GetClientInstance('gkehub', 'v1alpha1')
  messages = client.MESSAGES_MODULE
  return messages.AppDevExperienceFeatureSpec()


def CreateCloudBuildFeatureSpec():
  """Creates an empty Hub Feature Spec for the Cloud Build Service.

  Returns:
    The empty Cloud Build Hub Feature Spec.
  """
  client = core_apis.GetClientInstance('gkehub', 'v1alpha1')
  messages = client.MESSAGES_MODULE
  empty_config_map = messages.CloudBuildFeatureSpec.MembershipConfigsValue(
      additionalProperties=[])
  return messages.CloudBuildFeatureSpec(membershipConfigs=empty_config_map)


def CreateFeature(project, feature_id, feature_display_name, **kwargs):
  """Creates a Feature resource in Hub.

  Args:
    project: the project in which to create the Feature
    feature_id: the value to use for the feature_id
    feature_display_name: the display name of this Feature
    **kwargs: arguments for Feature object. For eg, multiclusterFeatureSpec

  Returns:
    the created Feature resource.

  Raises:
    - apitools.base.py.HttpError: if the request returns an HTTP error
    - exceptions raised by waiter.WaitFor()
  """
  client = core_apis.GetClientInstance('gkehub', 'v1alpha1')
  messages = client.MESSAGES_MODULE
  request = messages.GkehubProjectsLocationsGlobalFeaturesCreateRequest(
      feature=messages.Feature(**kwargs),
      parent='projects/{}/locations/global'.format(project),
      featureId=feature_id,
  )

  op = client.projects_locations_global_features.Create(request)
  op_resource = resources.REGISTRY.ParseRelativeName(
      op.name, collection='gkehub.projects.locations.operations')
  result = waiter.WaitFor(
      waiter.CloudOperationPoller(client.projects_locations_global_features,
                                  client.projects_locations_operations),
      op_resource,
      'Waiting for Feature {} to be created'.format(feature_display_name))

  # This allows us pass warning messages returned from OnePlatform backends.
  request_type = client.projects_locations_operations.GetRequestType('Get')
  op = client.projects_locations_operations.Get(
      request_type(name=op_resource.RelativeName()))
  metadata_dict = encoding.MessageToPyValue(op.metadata)
  if 'statusDetail' in metadata_dict:
    log.warning(metadata_dict['statusDetail'])

  return result


def GetFeature(name):
  """Gets a Feature resource from Hub.

  Args:
    name: the full resource name of the Feature to get, e.g.,
      projects/foo/locations/global/features/name.

  Returns:
    a Feature resource

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error
  """

  client = core_apis.GetClientInstance('gkehub', 'v1alpha1')
  return client.projects_locations_global_features.Get(
      client.MESSAGES_MODULE.GkehubProjectsLocationsGlobalFeaturesGetRequest(
          name=name))


def UpdateFeature(project, feature_id, feature_display_name, mask, **kwargs):
  """Updates a Feature resource in Hub.

  Args:
    project: the project in which to update the Feature
    feature_id: the value to use for the feature_id
    feature_display_name: the display name of this Feature
    mask: resource fields to be updated. For eg. multiclusterFeatureSpec
    **kwargs: arguments for Feature object. For eg, multiclusterFeatureSpec

  Returns:
    the updated Feature resource.

  Raises:
    - apitools.base.py.HttpError: if the request returns an HTTP error
    - exceptions raised by waiter.WaitFor()
  """
  client = core_apis.GetClientInstance('gkehub', 'v1alpha1')
  messages = client.MESSAGES_MODULE
  request = messages.GkehubProjectsLocationsGlobalFeaturesPatchRequest(
      name='projects/{0}/locations/global/features/{1}'.format(
          project, feature_id),
      updateMask=mask,
      feature=messages.Feature(**kwargs),
  )
  try:
    op = client.projects_locations_global_features.Patch(request)
  except apitools_exceptions.HttpUnauthorizedError as e:
    raise exceptions.Error(
        'You are not authorized to see the status of {} '
        'feature from project [{}]. Underlying error: {}'.format(
            feature_display_name, project, e))
  except apitools_exceptions.HttpNotFoundError as e:
    raise exceptions.Error('{} Feature for project [{}] is not enabled'.format(
        feature_display_name, project))
  op_resource = resources.REGISTRY.ParseRelativeName(
      op.name, collection='gkehub.projects.locations.operations')
  result = waiter.WaitFor(
      waiter.CloudOperationPoller(client.projects_locations_global_features,
                                  client.projects_locations_operations),
      op_resource,
      'Waiting for Feature {} to be updated'.format(feature_display_name))

  return result


def ListMemberships(project):
  """Lists Membership IDs in Hub.

  Args:
    project: the project in which Membership resources exist.

  Returns:
    a list of Membership resource IDs in Hub.

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error
  """
  parent = 'projects/{}/locations/global'.format(project)
  client = core_apis.GetClientInstance('gkehub', 'v1beta1')
  response = client.projects_locations_memberships.List(
      client.MESSAGES_MODULE.GkehubProjectsLocationsMembershipsListRequest(
          parent=parent))

  return [
      os.path.basename(membership.name) for membership in response.resources
  ]


def GetMembership(project, membership):
  """Gets Membership ID from the Hub.

  Args:
    project: the project to search for the Membership ID
    membership: the Membership ID to retrieve

  Returns:
    the corresponding Membership ID if it exists

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error
  """
  name = 'projects/{}/locations/global/memberships/{}'.format(
      project, membership)
  client = core_apis.GetClientInstance('gkehub', 'v1beta1')
  response = client.projects_locations_memberships.Get(
      client.MESSAGES_MODULE.GkehubProjectsLocationsMembershipsGetRequest(
          name=name))

  return response.name
