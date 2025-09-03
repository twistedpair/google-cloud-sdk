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
import six


class FeatureCommand(hub_base.HubCommand):
  """FeatureCommand is a mixin adding common utils to the Feature commands."""
  feature_name = ''  # Derived commands should set this to their Feature.

  @property
  def feature(self):
    """The Feature info entry for this command's Feature."""
    return info.Get(self.feature_name)

  def FeatureResourceName(self, project=None):
    """Builds the full resource name, using the core project property if no project is specified."""
    return super(FeatureCommand,
                 self).FeatureResourceName(self.feature_name, project)

  def FeatureNotEnabledError(self, project=None):
    """Constructs a new Error for reporting when this Feature is not enabled."""
    project = project or properties.VALUES.core.project.GetOrFail()
    return exceptions.Error('{} Feature for project [{}] is not enabled'.format(
        self.feature.display_name, project))

  def NotAuthorizedError(self, project=None):
    """Constructs a new Error for reporting when accessing this Feature is not authorized."""
    project = project or properties.VALUES.core.project.GetOrFail()
    return exceptions.Error(
        'Not authorized to access {} Feature for project [{}]'.format(
            self.feature.display_name, project))

  def GetFeature(self, project=None):
    """Fetch this command's Feature from the API, handling common errors."""
    try:
      return self.hubclient.GetFeature(self.FeatureResourceName(project))
    except apitools_exceptions.HttpNotFoundError:
      raise self.FeatureNotEnabledError(project)
    except apitools_exceptions.HttpUnauthorizedError:
      raise self.NotAuthorizedError(project)


class EnableCommandMixin(FeatureCommand):
  """A mixin for functionality to enable a Feature."""

  def Enable(self, feature):
    project = properties.VALUES.core.project.GetOrFail()
    if self.feature.api:
      enable_api.EnableServiceIfDisabled(project, self.feature.api)
    parent = util.LocationResourceName(project)
    try:
      # Retry if we still get "API not activated"; it can take a few minutes
      # for Chemist to catch up. See b/28800908.
      retryer = retry.Retryer(max_retrials=4, exponential_sleep_multiplier=1.75)
      op = retryer.RetryOnException(
          self.hubclient.CreateFeature,
          args=(parent, self.feature_name, feature),
          should_retry_if=self._FeatureAPINotEnabled,
          sleep_ms=1000)
    except retry.MaxRetrialsException:
      raise exceptions.Error(
          'Retry limit exceeded waiting for {} to enable'.format(
              self.feature.display_name))
    except apitools_exceptions.HttpConflictError as e:
      # If the error is not due to the object already existing, re-raise.
      error = core_api_exceptions.HttpErrorPayload(e)
      if error.status_description != 'ALREADY_EXISTS':
        raise
      log.status.Print('{} Feature for project [{}] is already enabled'.format(
          self.feature.display_name, project))
      return
    msg = 'Waiting for Feature {} to be created'.format(
        self.feature.display_name)
    return self.WaitForHubOp(self.hubclient.feature_waiter, op=op, message=msg)

  def _FeatureAPINotEnabled(self, exc_type, exc_value, traceback, state):
    del traceback, state  # Unused
    if not self.feature.api:
      return False
    if exc_type != apitools_exceptions.HttpBadRequestError:
      return False
    error = core_api_exceptions.HttpErrorPayload(exc_value)
    if not (error.status_description == 'FAILED_PRECONDITION' and
            self.feature.api in error.message and
            'is not enabled' in error.message):
      return False
    log.status.Print('Waiting for service API enablement to finish...')
    return True


class EnableCommand(EnableCommandMixin, calliope_base.CreateCommand):
  """Base class for the command that enables a Feature."""

  def Run(self, _):
    return self.Enable(self.messages.Feature())


class DescribeCommand(FeatureCommand, calliope_base.DescribeCommand):
  """Base class for the command that describes the status of a Feature."""

  def Run(self, _):
    return self.GetFeature()

  # TODO(b/440616932): Add Python unit tests for this function instead of
  # relying on the unit tests of the describe command on the config-management
  # surface.
  def filter_feature_for_memberships(self, feature, memberships):
    """Leave only specs and states of Memberships in the Feature.

    Respects the order of the Membership specs in the original Feature.

    Args:
      feature: Feature in the v1 API.
      memberships: List of resource names according to go/resource-names.
        Ideally, the existence of these Memberships will have been verified.
    Returns:
      None
    Raises:
      exceptions.Error: if any of Memberships does not have a spec in Feature.
    """
    # Hash Memberships without project to remove project number vs. id
    # inconsistency.
    memberships_by_location_and_name = {
        util.MembershipPartialName(m): m for m in memberships
    }
    membership_specs_by_location_and_name = {}
    if feature.membershipSpecs:
      membership_specs_by_location_and_name = {
          util.MembershipPartialName(entry.key): entry
          for entry in feature.membershipSpecs.additionalProperties
          # Optimization: only include specs for the specified Memberships.
          if util.MembershipPartialName(entry.key)
          in memberships_by_location_and_name
      }
    missing_memberships = [
        m
        for location_name, m in memberships_by_location_and_name.items()
        if location_name not in membership_specs_by_location_and_name
    ]
    if missing_memberships:
      raise exceptions.Error(
          ('The following requested memberships are not configured on the {}'
           ' feature, under membershipSpecs: {}'
          ).format(self.feature.display_name, missing_memberships)
      )
    membership_states_by_location_and_name = {}
    if feature.membershipStates:
      membership_states_by_location_and_name = {
          util.MembershipPartialName(entry.key): entry
          for entry in feature.membershipStates.additionalProperties
          if util.MembershipPartialName(entry.key)
          in membership_specs_by_location_and_name
      }
    # Dictionaries preserve insertion order, which increases ease of test.
    feature.membershipSpecs = self.messages.Feature.MembershipSpecsValue(
        additionalProperties=list(
            membership_specs_by_location_and_name.values()
        )
    )
    feature.membershipStates = self.messages.Feature.MembershipStatesValue(
        additionalProperties=[
            membership_states_by_location_and_name[m]
            for m in membership_specs_by_location_and_name
            if m in membership_states_by_location_and_name
        ]
    )


class UpdateCommandMixin(FeatureCommand):
  """A mixin for functionality to update a Feature."""

  def Update(self, mask, patch):
    """Update provides common API, display, and error handling logic."""
    try:
      op = self.hubclient.UpdateFeature(self.FeatureResourceName(), mask, patch)
    except apitools_exceptions.HttpNotFoundError:
      raise self.FeatureNotEnabledError()

    msg = 'Waiting for Feature {} to be updated'.format(
        self.feature.display_name)
    return self.WaitForHubOp(
        self.hubclient.feature_waiter, op, message=msg, warnings=False
    )


class UpdateCommand(UpdateCommandMixin, calliope_base.UpdateCommand):
  """Base class for the command that updates a Feature.

  Because Features updates are often bespoke actions, there is no default
  `Run` override like some of the other classes.
  """


class DisableCommand(UpdateCommandMixin, calliope_base.DeleteCommand):
  """Base class for the command that disables an entire or parts of a Feature.
  """

  FORCE_FLAG = calliope_base.Argument(
      '--force',
      action='store_true',
      help=(
          'Force disablement.'
          ' Bypasses any prompts for confirmation.'
          ' When disabling the entire feature, proceeds'
          ' even if the feature is in use.'
          ' Might result in unexpected behavior.'
      ),
  )
  FLEET_DEFAULT_MEMBER_CONFIG_FLAG = calliope_base.Argument(
      '--fleet-default-member-config',
      # Note that this flag should actually follow
      # yaqs/eng/q/4400496223010684928, but many
      # feature surfaces have already adopted store_true.
      action='store_true',
      help=(
          'Disable the [fleet-default membership configuration]('
          'https://cloud.google.com/kubernetes-engine/fleet-management/docs/manage-features).'
          ' Does not change existing membership configurations.'
          ' Does nothing if the feature is disabled.'
      ),
  )
  support_fleet_default = False

  @classmethod
  def Args(cls, parser):
    cls.FORCE_FLAG.AddToParser(parser)
    if cls.support_fleet_default:
      cls.FLEET_DEFAULT_MEMBER_CONFIG_FLAG.AddToParser(parser)

  def Run(self, args):
    if self.support_fleet_default and args.fleet_default_member_config:
      self.clear_fleet_default()
    else:
      self.Disable(args.force)

  def Disable(self, force):
    try:
      op = self.hubclient.DeleteFeature(self.FeatureResourceName(), force=force)
    except apitools_exceptions.HttpNotFoundError:
      return  # Already disabled.
    message = 'Waiting for Feature {} to be deleted'.format(
        self.feature.display_name)
    self.WaitForHubOp(
        self.hubclient.resourceless_waiter, op, message=message, warnings=False)

  def clear_fleet_default(self):
    mask = ['fleet_default_member_config']
    # Feature cannot be empty on update, which would be the case without the
    # placeholder name field when we try to clear the fleet default config.
    # The placeholder name field must not be in the mask, lest we actually
    # change the feature name.
    # TODO(b/302390572): Replace with better solution if found.
    patch = self.messages.Feature(name='placeholder')
    try:
      return self.Update(mask, patch)
    except exceptions.Error as e:
      # Do not error or log if feature does not exist.
      if six.text_type(e) != six.text_type(self.FeatureNotEnabledError()):
        raise e


def ParseMembership(args,
                    prompt=False,
                    autoselect=False,
                    search=False,
                    flag_override=''):
  """Returns a membership on which to run the command, given the arguments.

  Allows for a `--membership` flag or a `MEMBERSHIP_NAME` positional flag.

  Args:
    args: object containing arguments passed as flags with the command
    prompt: whether to prompt in console for a membership when none are provided
      in args
    autoselect: if no membership is provided and only one exists,
      automatically use that one
    search: whether to search for the membership and error if it does not exist
      (not recommended)
    flag_override: to use a custom membership flag name

  Returns:
    membership: A membership resource name string

  Raises:
    exceptions.Error: no memberships were found or memberships are invalid
    calliope_exceptions.RequiredArgumentException: membership was not provided
  """

  # If a membership is provided
  if args.IsKnownAndSpecified('membership') or args.IsKnownAndSpecified(
      'MEMBERSHIP_NAME') or args.IsKnownAndSpecified(flag_override):
    if resources.MembershipLocationSpecified(args,
                                             flag_override) or not search:
      return resources.MembershipResourceName(args, flag_override)
    else:
      return resources.SearchMembershipResource(
          args, flag_override, filter_cluster_missing=True)

  # If nothing is provided
  if not prompt and not autoselect:
    raise MembershipRequiredError(args, flag_override)

  all_memberships, unreachable = api_util.ListMembershipsFull(
      filter_cluster_missing=True)
  if unreachable:
    raise exceptions.Error(
        ('Locations {} are currently unreachable. Please specify '
         'memberships using `--location` or the full resource name '
         '(projects/*/locations/*/memberships/*)').format(unreachable))
  if autoselect and len(all_memberships) == 1:
    log.status.Print('Selecting membership [{}].'.format(all_memberships[0]))
    return all_memberships[0]
  if prompt:
    membership = resources.PromptForMembership(all_memberships)
    if membership is not None:
      return membership
  raise MembershipRequiredError(args, flag_override)


def ParseMembershipsPlural(args,
                           prompt=False,
                           prompt_cancel=True,
                           autoselect=False,
                           allow_cross_project=False,
                           search=False):
  """Parses a list of membership resources from args.

  Allows for a `--memberships` flag and a `--all-memberships` flag.

  Args:
    args: object containing arguments passed as flags with the command
    prompt: whether to prompt in console for a membership when none are provided
      in args
    prompt_cancel: whether to include a 'cancel' option in the prompt
    autoselect: if no memberships are provided and only one exists,
      automatically use that one
    allow_cross_project: whether to allow memberships from different projects
    search: whether to check that the membership exists in the fleet

  Returns:
    memberships: A list of membership resource name strings

  Raises:
    exceptions.Error if no memberships were found or memberships are invalid
    calliope_exceptions.RequiredArgumentException if membership was not provided
  """
  memberships = []

  # If running for all memberships
  if hasattr(args, 'all_memberships') and args.all_memberships:
    all_memberships, unreachable = api_util.ListMembershipsFull(
        filter_cluster_missing=True)
    if unreachable:
      raise exceptions.Error(
          'Locations {} are currently unreachable. Please try again or '
          'specify memberships for this command.'.format(unreachable))
    if not all_memberships:
      raise exceptions.Error('No Memberships available in the fleet.')
    return all_memberships

  # If a membership list is provided
  if args.IsKnownAndSpecified('memberships'):
    if resources.MembershipLocationSpecified(args):
      memberships += resources.PluralMembershipsResourceNames(args)
      if search:
        for membership in memberships:
          if not api_util.GetMembership(membership):
            raise exceptions.Error(
                'Membership {} does not exist in the fleet.'.format(membership))

      if not allow_cross_project and len(
          resources.GetMembershipProjects(memberships)) > 1:
        raise CrossProjectError(resources.GetMembershipProjects(memberships))

    else:
      memberships += resources.SearchMembershipResourcesPlural(
          args, filter_cluster_missing=True)

  if memberships:
    return memberships

  # If nothing is provided
  if not prompt and not autoselect:
    raise MembershipRequiredError(args)

  all_memberships, unreachable = api_util.ListMembershipsFull(
      filter_cluster_missing=True)
  if unreachable:
    raise exceptions.Error(
        ('Locations {} are currently unreachable. Please specify '
         'memberships using `--location` or the full resource name '
         '(projects/*/locations/*/memberships/*)').format(unreachable))
  if autoselect and len(all_memberships) == 1:
    log.status.Print('Selecting membership [{}].'.format(all_memberships[0]))
    return [all_memberships[0]]
  if prompt:
    membership = resources.PromptForMembership(cancel=prompt_cancel)
    if membership:
      memberships.append(membership)
    return memberships
  raise MembershipRequiredError(args)


# This should not be used in the future and only exists to support deprecated
# commands until they are deleted
def ListMemberships():
  """Lists Membership IDs in the fleet for the current project.

  Returns:
    A list of Membership resource IDs in the fleet.
  """
  client = core_apis.GetClientInstance('gkehub', 'v1beta')
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


def MembershipRequiredError(args, flag_override=''):
  """Parses a list of membership resources from args.

  Assumes a `--memberships` flag or a `MEMBERSHIP_NAME` flag unless overridden.

  Args:
    args: argparse.Namespace arguments provided for the command
    flag_override: set to override the name of the membership flag

  Returns:
    memberships: A list of membership resource name strings

  Raises:
    exceptions.Error: if no memberships were found or memberships are invalid
    calliope_exceptions.RequiredArgumentException: if membership was not
      provided
  """
  if flag_override:
    flag = flag_override
  elif args.IsKnownAndSpecified('MEMBERSHIP_NAME'):
    flag = 'MEMBERSHIP_NAME'
  else:
    flag = 'memberships'
  return calliope_exceptions.RequiredArgumentException(
      flag, 'At least one membership is required for this command.')


def _ClusterMissing(m):
  for t in ['gkeCluster', 'multiCloudCluster', 'onPremCluster']:
    if hasattr(m, t):
      return getattr(getattr(m, t), 'clusterMissing', False)
