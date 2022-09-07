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
"""Base classes for [enable|disable|describe] commands for Feature resource."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.container.fleet import util
from googlecloudsdk.api_lib.services import enable_api
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.api_lib.util import exceptions as core_api_exceptions
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.container.fleet import api_util
from googlecloudsdk.command_lib.container.fleet import base as hub_base
from googlecloudsdk.command_lib.container.fleet import resources
from googlecloudsdk.command_lib.container.fleet.features import info
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import retry


class FeatureCommand(hub_base.HubCommand):
  """FeatureCommand is a mixin adding common utils to the Feature commands."""
  feature_name = ''  # Derived commands should set this to their Feature.

  # TODO(b/181242245): Remove this once all remaining features use v1alpha+.
  @property
  def v1alpha1_client(self):
    """A raw v1alpha1 gkehub API client. PLEASE AVOID NEW USES!"""
    # Build the client lazily, but only once.
    if not hasattr(self, '_v1alpha1_client'):
      self._v1alpha1_client = core_apis.GetClientInstance('gkehub', 'v1alpha1')
    return self._v1alpha1_client

  # TODO(b/181242245): Remove this once all remaining features use v1alpha+.
  @property
  def v1alpha1_messages(self):
    """The v1alpha1 gkehub messages module. PLEASE AVOID NEW USES!"""
    return core_apis.GetMessagesModule('gkehub', 'v1alpha1')

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

  # TODO(b/181242245): Remove v1alpha1 once all remaining features use v1alpha+.
  def GetFeature(self, v1alpha1=False):
    """Fetch this command's Feature from the API, handling common errors."""
    try:
      if v1alpha1:
        return self.v1alpha1_client.projects_locations_global_features.Get(
            self.v1alpha1_messages
            .GkehubProjectsLocationsGlobalFeaturesGetRequest(
                name=self.FeatureResourceName()))
      return self.hubclient.GetFeature(self.FeatureResourceName())
    except apitools_exceptions.HttpNotFoundError:
      raise self.FeatureNotEnabledError()


class EnableCommand(FeatureCommand, calliope_base.CreateCommand):
  """Base class for the command that enables a Feature."""

  def Run(self, args):
    return self.Enable(self.messages.Feature())

  def Enable(self, feature):
    project = properties.VALUES.core.project.GetOrFail()
    enable_api.EnableServiceIfDisabled(project, self.feature.api)
    parent = util.LocationResourceName(project)
    try:
      # Retry if we still get "API not activated"; it can take a few minutes
      # for Chemist to catch up. See b/28800908.
      # TODO(b/177098463): Add a spinner here?
      retryer = retry.Retryer(max_retrials=4, exponential_sleep_multiplier=1.75)
      op = retryer.RetryOnException(
          self.hubclient.CreateFeature,
          args=(parent, self.feature_name, feature),
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
      # TODO(b/177098463): Decide if this should be a hard error if a spec was
      # set, but not applied, because the Feature already existed.
      log.status.Print('{} Feature for project [{}] is already enabled'.format(
          self.feature.display_name, project))
      return
    msg = 'Waiting for Feature {} to be created'.format(
        self.feature.display_name)
    return self.WaitForHubOp(self.hubclient.feature_waiter, op=op, message=msg)

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


class DisableCommand(FeatureCommand, calliope_base.DeleteCommand):
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


class DescribeCommand(FeatureCommand, calliope_base.DescribeCommand):
  """Base class for the command that describes the status of a Feature."""

  def Run(self, args):
    return self.GetFeature()


class UpdateCommand(FeatureCommand, calliope_base.UpdateCommand):
  """Base class for the command that updates a Feature.

  Because Features updates are often bespoke actions, there is no default
  `Run` override like some of the other classes.
  """

  # TODO(b/181242245): Remove v1alpha1 helpers once all features use v1alpha+.
  def Update(self, mask, patch, v1alpha1=False):
    """Update provides common API, display, and error handling logic."""
    update = self._PatchV1alpha1 if v1alpha1 else self.hubclient.UpdateFeature
    poller = (
        self._V1alpha1Waiter() if v1alpha1 else self.hubclient.feature_waiter)

    try:
      op = update(self.FeatureResourceName(), mask, patch)
    except apitools_exceptions.HttpNotFoundError:
      raise self.FeatureNotEnabledError()

    msg = 'Waiting for Feature {} to be updated'.format(
        self.feature.display_name)
    # TODO(b/177098463): Update all downstream tests to handle warnings.
    return self.WaitForHubOp(poller, op, message=msg, warnings=False)

  def _V1alpha1Waiter(self):
    return waiter.CloudOperationPoller(
        self.v1alpha1_client.projects_locations_global_features,
        self.v1alpha1_client.projects_locations_operations)

  def _PatchV1alpha1(self, name, mask, patch):
    req = self.v1alpha1_messages.GkehubProjectsLocationsGlobalFeaturesPatchRequest(
        name=name,
        updateMask=','.join(mask),
        feature=patch,
    )
    return self.v1alpha1_client.projects_locations_global_features.Patch(req)


def ParseMemberships(args,
                     membership_flag=False,
                     memberships_flag=False,
                     membership_name_flag=False,
                     all_memberships_flag=False,
                     prompt=False,
                     allow_cross_project=False):
  """Returns a list of memberships to which to run the command, given the arguments.

  Args:
    args: object containing arguments passed as flags with the command
    membership_flag: whether a --membership flag is included in this command
    memberships_flag: whether a plural --memberships flag is included
    membership_name_flag: whether a positional MEMBERSHIP_NAME flag is included
    all_memberships_flag: whether --all-memberships is included in this commmand
    prompt: whether to prompt in console for a membership when none are provided
      in args
    allow_cross_project: whether to allow memberships from different projects

  Returns:
    memberships: A list of membership resource name strings

  Raises:
    exceptions.Error if no memberships were found or memberships are invalid
    calliope_exceptions.RequiredArgumentException if membership was not provided
  """
  memberships = []

  # If running for all memberships
  if all_memberships_flag and hasattr(
      args, 'all_memberships') and args.all_memberships:
    all_memberships, unreachable = api_util.ListMembershipsFull()
    if unreachable:
      raise exceptions.Error(
          'Locations {} are currently unreachable. Please try again or '
          'specify memberships for this command.'.format(unreachable))
    if not all_memberships:
      raise exceptions.Error('No Memberships available in the fleet.')
    return all_memberships

  # If a membership is provided
  if membership_flag and hasattr(args, 'membership') and args.membership:
    memberships += resources.GetExistingMembershipResourceNames(args)

  # If a membership is provided (positional arg)
  if membership_name_flag and hasattr(
      args, 'MEMBERSHIP_NAME') and args.MEMBERSHIP_NAME:
    memberships += resources.GetExistingMembershipResourceNames(
        args, positional=True)

  # If a membership list is provided
  if memberships_flag and hasattr(args, 'memberships') and args.memberships:
    memberships += resources.GetExistingMembershipResourceNames(
        args, plural=True)

  if memberships:
    # Verify memberships
    # @wenjung
    # for membership in memberships:
    #   if membership not in all_memberships:
    #     raise exceptions.Error(
    #         'Membership {} does not exist in the fleet.'.format(membership))
    if not allow_cross_project and len(
        resources.GetMembershipProjects(memberships)) > 1:
      raise CrossProjectError(resources.GetMembershipProjects(memberships))
    return memberships

  # If nothing is provided
  flag = '--memberships' if memberships_flag else 'MEMBERSHIP_NAME' if membership_name_flag else '--membership'
  if not prompt:
    raise calliope_exceptions.RequiredArgumentException(
        flag, 'At least one membership is required for this command.')

  membership = resources.PromptForMembership()
  if membership:
    memberships.append(membership)
  else:
    raise calliope_exceptions.RequiredArgumentException(
        flag, 'At least one membership is required for this command.')

  return memberships


# This should not be used in the future and will be deleted
# once all features support regional memberships
def ListMemberships():
  """Lists Membership IDs in the fleet for the current project.

  Returns:
    A list of Membership resource IDs in the fleet.
  """
  client = core_apis.GetClientInstance('gkehub', 'v1beta1')
  response = client.projects_locations_memberships.List(
      client.MESSAGES_MODULE.GkehubProjectsLocationsMembershipsListRequest(
          parent=hub_base.HubCommand.LocationResourceName()))

  return [
      util.MembershipShortname(m.name)
      for m in response.resources
      if not _ClusterMissing(m.endpoint)
  ]


def CrossProjectError(projects):
  return exceptions.Error('Memberships for this command must belong to the '
                          'same project and cannot mix project number and '
                          'project ID ({}).'.format(projects))


def _ClusterMissing(m):
  for t in ['gkeCluster', 'multiCloudCluster', 'onPremCluster']:
    if hasattr(m, t):
      return getattr(getattr(m, t), 'clusterMissing', False)
