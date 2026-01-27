# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Command line processing utilities for cloud access bindings."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from apitools.base.py import encoding
from googlecloudsdk.api_lib.accesscontextmanager import util
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.accesscontextmanager import common
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import iso_duration
from googlecloudsdk.core.util import times


def AddUpdateMask(ref, args, req):
  """Hook to add update mask."""
  del ref
  update_mask = []
  if args.IsKnownAndSpecified('level'):
    update_mask.append('access_levels')
  if args.IsKnownAndSpecified('dry_run_level'):
    update_mask.append('dry_run_access_levels')
  if args.IsKnownAndSpecified('session_length'):
    update_mask.append('session_settings')
  if args.IsKnownAndSpecified('binding_file'):
    update_mask.append('scoped_access_settings')

  if not update_mask:
    raise calliope_exceptions.MinimumArgumentException(
        ['--level', '--dry_run_level', '--session-length', '--binding-file']
    )

  req.updateMask = ','.join(update_mask)
  return req


def AddUpdateMaskAlpha(ref, args, req):
  """Hook to add update mask in Alpha track."""
  del ref
  update_mask = []
  if args.IsKnownAndSpecified('level'):
    update_mask.append('access_levels')
  if args.IsKnownAndSpecified('dry_run_level'):
    update_mask.append('dry_run_access_levels')
  if args.IsKnownAndSpecified(
      'restricted_client_application_client_ids'
  ) or args.IsKnownAndSpecified('restricted_client_application_names'):
    update_mask.append('restricted_client_applications')
  if args.IsKnownAndSpecified('session_length'):
    update_mask.append('session_settings')
  if args.IsKnownAndSpecified('binding_file'):
    update_mask.append('scoped_access_settings')

  if not update_mask:
    raise calliope_exceptions.MinimumArgumentException([
        '--level',
        '--dry_run_level',
        '--restricted_client_application_names',
        '--restricted_client_application_client_ids',
        '--session-length',
        '--binding-file',
    ])

  req.updateMask = ','.join(update_mask)
  return req


def ProcessOrganization(ref, args, req):
  """Hook to process organization input."""
  del ref, args
  if req.parent is not None:
    return req

  org = properties.VALUES.access_context_manager.organization.Get()
  if org is None:
    raise calliope_exceptions.RequiredArgumentException(
        '--organization',
        'The attribute can be set in the following ways: \n'
        + '- provide the argument `--organization` on the command line \n'
        + '- set the property `access_context_manager/organization`',
    )

  org_ref = resources.REGISTRY.Parse(
      org, collection='accesscontextmanager.organizations'
  )
  req.parent = org_ref.RelativeName()
  return req


def ProcessRestrictedClientApplicationsAlpha(unused_ref, args, req):
  """Hook to process restricted client applications input in Alpha track."""
  del unused_ref
  return _ProcessRestrictedClientApplications(args, req, version='v1alpha')


def _ProcessRestrictedClientApplications(args, req, version=None):
  """Process restricted client applications input for the given version."""
  # Processing application client ids if available
  if args.IsKnownAndSpecified('restricted_client_application_client_ids'):
    client_ids = args.restricted_client_application_client_ids
    restricted_client_application_refs = (
        _MakeRestrictedClientApplicationsFromIdentifiers(
            client_ids,
            'restricted_client_application_client_ids',
            version=version,
        )
    )
    # req.gcpUserAccessBinding is None when no access levels are specified
    # during update. Access Levels are optional when updating restricted client
    # applications, but they are required when creating a new binding.
    if req.gcpUserAccessBinding is None:
      req.gcpUserAccessBinding = util.GetMessages(
          version=version
      ).GcpUserAccessBinding()
    for restricted_client_application_ref in restricted_client_application_refs:
      req.gcpUserAccessBinding.restrictedClientApplications.append(
          restricted_client_application_ref
      )
  # processing application names if available
  if args.IsKnownAndSpecified('restricted_client_application_names'):
    client_names = args.restricted_client_application_names
    restricted_client_application_refs = (
        _MakeRestrictedClientApplicationsFromIdentifiers(
            client_names,
            'restricted_client_application_names',
            version=version,
        )
    )
    # req.gcpUserAccessBinding is None when no access levels are specified
    # during update. Access Levels are optional when updating restricted client
    # applications, but they are required when creating a new binding.
    if req.gcpUserAccessBinding is None:
      req.gcpUserAccessBinding = util.GetMessages(
          version=version
      ).GcpUserAccessBinding()
    for restricted_client_application_ref in restricted_client_application_refs:
      req.gcpUserAccessBinding.restrictedClientApplications.append(
          restricted_client_application_ref
      )
  return req


def _MakeRestrictedClientApplicationsFromIdentifiers(
    app_identifiers, arg_name, version=None
):
  """Parse restricted client applications and return their resource references."""
  resource_refs = []
  if app_identifiers is not None:
    app_identifiers = [
        # remove empty strings
        identifier
        for identifier in app_identifiers
        if identifier
    ]
    for app_identifier in app_identifiers:
      if arg_name == 'restricted_client_application_client_ids':
        try:
          resource_refs.append(
              util.GetMessages(version=version).Application(
                  clientId=app_identifier
              )
          )
        except:
          raise calliope_exceptions.InvalidArgumentException(
              '--{}'.format('restricted_client_application_client_ids'),
              'Unable to parse input. The input must be of type string[].',
          )
      elif arg_name == 'restricted_client_application_names':
        try:
          resource_refs.append(
              util.GetMessages(version=version).Application(name=app_identifier)
          )
        except:
          raise calliope_exceptions.InvalidArgumentException(
              '--{}'.format('restricted_client_application_names'),
              'Unable to parse input. The input must be of type string[].',
          )
      else:
        raise calliope_exceptions.InvalidArgumentException(
            '--{}'.format('arg_name'),
            'The input is not valid for Restricted Client Applications.',
        )
  return resource_refs


def _ParseLevelRefs(req, param, is_dry_run):
  """Parse level strings and return their resource references."""
  level_inputs = req.gcpUserAccessBinding.accessLevels
  if is_dry_run:
    level_inputs = req.gcpUserAccessBinding.dryRunAccessLevels

  level_refs = []
  level_inputs = [level_input for level_input in level_inputs if level_input]
  if not level_inputs:
    return level_refs

  arg_name = '--dry_run_level' if is_dry_run else '--level'

  for level_input in level_inputs:
    try:
      level_ref = resources.REGISTRY.Parse(
          level_input,
          params=param,
          collection='accesscontextmanager.accessPolicies.accessLevels',
      )
    except:
      raise calliope_exceptions.InvalidArgumentException(
          '--{}'.format(arg_name),
          'The input must be the full identifier for the access level, '
          'such as `accessPolicies/123/accessLevels/abc`.',
      )
    level_refs.append(level_ref)
  return level_refs


def ProcessLevels(ref, args, req):
  """Hook to format levels and validate all policies."""
  del ref  # Unused
  policies_to_check = {}

  param = {}
  policy_ref = None
  if args.IsKnownAndSpecified('policy'):
    try:
      policy_ref = resources.REGISTRY.Parse(
          args.GetValue('policy'),
          collection='accesscontextmanager.accessPolicies',
      )
    except:
      raise calliope_exceptions.InvalidArgumentException(
          '--policy',
          'The input must be the full identifier for the access policy, '
          'such as `123` or `accessPolicies/123.',
      )
    param = {'accessPoliciesId': policy_ref.Name()}
    policies_to_check['--policy'] = policy_ref.RelativeName()
  else:
    del policy_ref

  # Parse level and dry run level
  level_refs = (
      _ParseLevelRefs(req, param, is_dry_run=False)
      if args.IsKnownAndSpecified('level')
      else []
  )
  dry_run_level_refs = (
      _ParseLevelRefs(req, param, is_dry_run=True)
      if args.IsKnownAndSpecified('dry_run_level')
      else []
  )

  # Validate all refs in each level ref belong to the same policy
  level_parents = [x.Parent() for x in level_refs]
  dry_run_level_parents = [x.Parent() for x in dry_run_level_refs]
  if not all(x == level_parents[0] for x in level_parents):
    raise ConflictPolicyException(['--level'])
  if not all(x == dry_run_level_parents[0] for x in dry_run_level_parents):
    raise ConflictPolicyException(['--dry-run-level'])

  # Validate policies of level, dry run level and policy inputs are the same
  if level_parents:
    policies_to_check['--level'] = level_parents[0].RelativeName()
  if dry_run_level_parents:
    policies_to_check['--dry-run-level'] = dry_run_level_parents[
        0
    ].RelativeName()
  flags_to_complain = list(policies_to_check.keys())
  flags_to_complain.sort()  # Sort for test purpose.
  policies_values = list(policies_to_check.values())
  if not all(x == policies_values[0] for x in policies_values):
    raise ConflictPolicyException(flags_to_complain)

  # Set formatted level fields in the request
  if level_refs:
    req.gcpUserAccessBinding.accessLevels = [
        x.RelativeName() for x in level_refs
    ]
  if dry_run_level_refs:
    req.gcpUserAccessBinding.dryRunAccessLevels = [
        x.RelativeName() for x in dry_run_level_refs
    ]
  return req


def ProcessSessionLength(string):
  """Process the session-length argument into an acceptable form for GCSL session settings."""

  # If we receive the empty string then return a negative duration. This will
  # signal to the request processor that sessionSettings should be cleared.
  # This is primarily used for clearing bindings on calls to update, and is a
  # no-op for calls to create.

  duration = (
      times.ParseDuration(string) if string else iso_duration.Duration(hours=-1)
  )

  # TODO(b/346781832)
  if duration.total_seconds > iso_duration.Duration(days=1).total_seconds:
    raise calliope_exceptions.InvalidArgumentException(
        '--session-length',
        'The session length cannot be greater than one day.',
    )
  # Format for Google protobuf Duration
  return '{}s'.format(int(duration.total_seconds))


def ProcessSessionSettings(unused_ref, args, req):
  """Hook to process GCSL session settings.

    When --session-length=0 make sure the sessionLengthEnabled is set to false.

    Throw an error if --session-reauth-method or --use-oidc-max-age are set
    without --session-length.

  Args:
      unused_ref: Unused
      args: The command line arguments
      req: The request object

  Returns:
    The modified request object.

  Raises:
    calliope_exceptions.InvalidArgumentException: If arguments are incorrectly
    set.
  """
  del unused_ref
  if args.IsKnownAndSpecified('session_length'):
    if args.IsKnownAndSpecified(
        'restricted_client_application_client_ids'
    ) or args.IsKnownAndSpecified('restricted_client_application_names'):
      raise calliope_exceptions.InvalidArgumentException(
          '--session-length',
          'Cannot set session length on restricted client applications. Use '
          'scoped access settings.',
      )
    session_length = times.ParseDuration(
        req.gcpUserAccessBinding.sessionSettings.sessionLength
    ).total_seconds
    if session_length < 0:  # Case where --session_length=''
      req.gcpUserAccessBinding.sessionSettings = None
    elif session_length == 0:  # Case where we disable session
      req.gcpUserAccessBinding.sessionSettings.sessionLengthEnabled = False
    else:  # Normal case
      req.gcpUserAccessBinding.sessionSettings.sessionLengthEnabled = True
  else:
    if args.IsKnownAndSpecified('session_reauth_method'):
      raise calliope_exceptions.InvalidArgumentException(
          '--session_reauth_method',
          'Cannot set --session_reauth_method without --session-length',
      )
    # Clear all default session settings from the request if --session-length is
    # unspecified
    req.gcpUserAccessBinding.sessionSettings = None

  return req


def _CamelCase2SnakeCase(name):
  s1 = re.compile('([a-z0-9])([A-Z])').sub(r'\1_\2', name)
  return re.sub('_[A-Z]+', lambda m: m.group(0).lower(), s1)


def ProcessFilter(unused_ref, args, req):
  """Hook to process filter. Covert camel case to snake case."""
  del unused_ref
  if args.IsKnownAndSpecified('filter'):
    # Only pass filter to handler if it contains principal
    if 'principal' in args.filter:
      filter_str = _CamelCase2SnakeCase(args.filter)
      req.filter = filter_str
  return req


class ConflictPolicyException(core_exceptions.Error):
  """For conflict policies from inputs."""

  def __init__(self, parameter_names):
    super(ConflictPolicyException, self).__init__(
        'Invalid value for [{0}]: Ensure that the {0} resources are '
        'all from the same policy.'.format(
            ', '.join(['{0}'.format(p) for p in parameter_names])
        )
    )


def _TryGetAccessLevelResources(
    param, access_levels, field_name, error_message
):
  """Try to get the access level cloud resources that correspond to the `access levels`.

  Args:
    param: The parameters to pass to the resource registry
    access_levels: The access levels to turn into cloud resources
    field_name: The name of the field to use in the error message
    error_message: The error message to use if the access levels cannot be
      parsed

  Returns:
    The access level cloud resources that correspond to the `access levels`.
  """
  access_level_resources = []
  access_level_inputs = [
      access_level for access_level in access_levels if access_level
  ]

  for access_level_input in access_level_inputs:
    try:
      access_level_resources.append(
          resources.REGISTRY.Parse(
              access_level_input,
              params=param,
              collection='accesscontextmanager.accessPolicies.accessLevels',
          )
      )
    except:
      raise calliope_exceptions.InvalidArgumentException(
          '--{}'.format(field_name),
          error_message,
      )

  return access_level_resources


def _TryGetPolicyCloudResource(policy, field_name, error_message):
  """Try to get the policy cloud resource that corresponds to the `policy`.

  Args:
    policy: The policy to turn into a cloud resource
    field_name: The name of the field to use in the error message
    error_message: The error message to use if the policy cannot be parsed

  Returns:
    The policy cloud resource that corresponds to the `policy`.
  """
  try:
    return resources.REGISTRY.Parse(
        policy,
        collection='accesscontextmanager.accessPolicies',
    )
  except:
    raise calliope_exceptions.InvalidArgumentException(
        '--{}'.format(field_name), error_message
    )


def _ProcessScopesInScopedAccessSettings(req):
  """Validates the scope in the scoped access settings."""

  def _ValidateScopeInScopedAccessSettingsUniqueness(scoped_access_settings):
    scopes = [str(x.scope) for x in scoped_access_settings]
    if len(scopes) != len(set(scopes)):
      raise calliope_exceptions.InvalidArgumentException(
          '--binding-file',
          'ScopedAccessSettings in the binding-file must be unique.',
      )

  def _IsClientScopeSet(client_scope):
    if not client_scope:
      return False
    if client_scope.restrictedClientApplication:
      restricted_client_application_dict = encoding.MessageToDict(
          client_scope.restrictedClientApplication
      )
      if not restricted_client_application_dict:
        return False
      # Check for None or empty string
      for key in restricted_client_application_dict.keys():
        if not restricted_client_application_dict[key]:
          return False
      return True
    elif (
        hasattr(client_scope, 'restrictedProject')
        and client_scope.restrictedProject
    ):
      restricted_project_dict = encoding.MessageToDict(
          client_scope.restrictedProject
      )
      if not restricted_project_dict:
        return False
      for key in restricted_project_dict.keys():
        if not restricted_project_dict[key]:
          return False
      return True
    return False

  def _ValidateScopeInScopedAccessSettingIsNotEmpty(scoped_access_setting):
    if not scoped_access_setting.scope or not _IsClientScopeSet(
        scoped_access_setting.scope.clientScope
    ):
      raise calliope_exceptions.InvalidArgumentException(
          '--binding-file',
          'ScopedAccessSettings in the binding-file must have a scope.',
      )

  def _Start(req):
    scoped_access_settings = req.gcpUserAccessBinding.scopedAccessSettings
    _ValidateScopeInScopedAccessSettingsUniqueness(scoped_access_settings)
    for scoped_access_setting in scoped_access_settings:
      _ValidateScopeInScopedAccessSettingIsNotEmpty(scoped_access_setting)

  _Start(req)


def _ProcessAccessSettingsInScopedAccessSettings(req):
  """Validates the access settings in the scoped access settings."""

  def _IsAccessSettingsSet(access_settings):
    if not access_settings:
      return False
    access_settings_dict = encoding.MessageToDict(access_settings)
    if not access_settings_dict:
      return False
    # Check for None or empty arrays
    for key in access_settings_dict.keys():
      if not access_settings_dict[key]:
        return False
    return True

  def _ValidateAccessSettingsInScopedAccessSettingAtLeastOneIsNotEmpty(
      access_settings, dry_run_settings
  ):
    if not _IsAccessSettingsSet(access_settings) and not _IsAccessSettingsSet(
        dry_run_settings
    ):
      raise calliope_exceptions.InvalidArgumentException(
          '--binding-file',
          'ScopedAccessSettings in the binding-file must have at least one of'
          ' activeSettings or dryRunSettings set.',
      )

  def _Start(req):
    scoped_access_settings = req.gcpUserAccessBinding.scopedAccessSettings
    for scoped_access_setting in scoped_access_settings:
      _ValidateAccessSettingsInScopedAccessSettingAtLeastOneIsNotEmpty(
          scoped_access_setting.activeSettings,
          scoped_access_setting.dryRunSettings,
      )

  _Start(req)


def _ProcessAccessLevelsInScopedAccessSettings(args, req):
  """Process the access levels in the scoped access settings."""

  def _ValidateBelongsToSamePolicy(
      access_level_resources,
      dry_run_access_level_resources,
      policy_resource,
      parameter_names,
  ):
    """Validate that the access levels and policy belong to the same policy."""
    combined_access_level = (
        access_level_resources + dry_run_access_level_resources
    )
    if combined_access_level:
      # Check that all access levels are from the same policy
      access_level_resources_parents = [
          x.Parent() for x in combined_access_level
      ]
      if not all(
          x == access_level_resources_parents[0]
          for x in access_level_resources_parents
      ):
        raise ConflictPolicyException(parameter_names)

      # Check that the policy is the same as the access levels
      if (
          policy_resource
          and access_level_resources_parents
          and (
              policy_resource.RelativeName()
              != access_level_resources_parents[0].RelativeName()
          )
      ):
        raise ConflictPolicyException(['--policy'] + parameter_names)

  def _ReplaceAccessLevelsInAccessSettingsWithRelativeNames(
      access_settings, access_level_resources
  ):
    """Replace the access levels in the scoped access settings with relative names.

    For example,

    {
      'activeSettings': {
        'accessLevels': [
          'accessPolicies/123/accessLevels/access_level_1'
        ]
      }
    }

    is replaced with:

    {
      'activeSettings': {
        'accessLevels': [
          access_level_resources.RelativeName()
        ]
      }
    }

    Args:
      access_settings: The access settings to replace the access levels in.
      access_level_resources: The access level resources to replace the access
        levels with.
    """
    # Set the relative names of the access levels in the request
    if access_level_resources:
      access_settings.accessLevels = [
          x.RelativeName() for x in access_level_resources
      ]

  def _GetAccessLevelResources(policy_resource, access_levels):
    """Get the access level resources from the scoped access settings.

    Args:
      policy_resource: The policy resource
      access_levels: The access levels to turn into cloud resources. For
        example, ['accessPolicies/123/accessLevels/access_level_1']

    Returns:
      The access level cloud resources that correspond to the `access levels`.
      For example,
      ['https://accesscontextmanager.googleapis.com/v1/accessPolicies/123/accessLevels/access_level_1']
    """
    param = (
        {}
        if not policy_resource
        else {'accessPoliciesId': policy_resource.Name()}
    )
    # Obtain the access level resources
    access_level_resources = []
    if access_levels:
      access_level_resources = _TryGetAccessLevelResources(
          param,
          access_levels,
          'binding-file',
          'Access levels in ScopedAccessSettings must contain the full'
          ' identifier. For example:'
          ' `accessPolicies/123/accessLevels/access_level_1',
      )
    return access_level_resources

  def _Start(args, req):
    policy_resource = None
    if args.IsKnownAndSpecified('policy'):
      # Obtain the policy resource
      policy_resource = _TryGetPolicyCloudResource(
          args.GetValue('policy'),
          'policy',
          'The input must be the full identifier for the access policy, '
          'such as `123` or `accessPolicies/123.',
      )

    scoped_access_settings = req.gcpUserAccessBinding.scopedAccessSettings
    access_level_resources_sample = []
    dry_run_access_level_resources_sample = []
    for scoped_access_setting in scoped_access_settings:
      # Obtain the access level resources
      access_level_resources = []
      if (
          scoped_access_setting.activeSettings
          and scoped_access_setting.activeSettings.accessLevels
      ):
        access_level_resources = _GetAccessLevelResources(
            policy_resource, scoped_access_setting.activeSettings.accessLevels
        )
        access_level_resources_sample.append(access_level_resources[0])

      # Obtain the dry run access level resources
      dry_run_access_level_resources = []
      if (
          scoped_access_setting.dryRunSettings
          and scoped_access_setting.dryRunSettings.accessLevels
      ):
        dry_run_access_level_resources = _GetAccessLevelResources(
            policy_resource,
            scoped_access_setting.dryRunSettings.accessLevels,
        )
        dry_run_access_level_resources_sample.append(
            dry_run_access_level_resources[0]
        )
      _ValidateBelongsToSamePolicy(
          access_level_resources,
          dry_run_access_level_resources,
          policy_resource,
          ['--binding-file'],
      )
      _ReplaceAccessLevelsInAccessSettingsWithRelativeNames(
          scoped_access_setting.activeSettings, access_level_resources
      )
      _ReplaceAccessLevelsInAccessSettingsWithRelativeNames(
          scoped_access_setting.dryRunSettings, dry_run_access_level_resources
      )

    # Validate that all access levels in all scoped access settings belong to
    # the same policy
    _ValidateBelongsToSamePolicy(
        access_level_resources_sample,
        dry_run_access_level_resources_sample,
        policy_resource,
        ['--binding-file'],
    )

    # Obtain the global access level resource for the first access level defined
    # in the request
    global_access_level_resources = []
    if req.gcpUserAccessBinding.accessLevels:
      try:
        global_access_level_resources = _GetAccessLevelResources(
            policy_resource, req.gcpUserAccessBinding.accessLevels
        )
      except calliope_exceptions.InvalidArgumentException:
        # Ignore error because global access levels will be processed later
        pass
    if not global_access_level_resources:
      try:
        global_access_level_resources = _GetAccessLevelResources(
            policy_resource, req.gcpUserAccessBinding.dryRunAccessLevels
        )
      except calliope_exceptions.InvalidArgumentException:
        # Ignore error because global access levels will be processed later
        pass

    # Validated that scoped and global access levels belong to the same policy
    _ValidateBelongsToSamePolicy(
        access_level_resources_sample,
        global_access_level_resources,
        policy_resource,
        ['--binding-file', '--level', '--dry-run-level'],
    )

  _Start(args, req)


def _ProcessSessionSettingsInScopedAccessSettings(req):
  """Process the session settings in the scoped access settings."""

  def _ValidateSessionSettings(session_settings):
    if session_settings is None:
      return
    if session_settings.sessionLength is None:
      raise calliope_exceptions.InvalidArgumentException(
          '--binding-file',
          'SessionSettings within ScopedAccessSettings must include a session'
          'length.',
      )
    session_length = times.ParseDuration(
        session_settings.sessionLength
    ).total_seconds
    if session_length > iso_duration.Duration(days=1).total_seconds:
      raise calliope_exceptions.InvalidArgumentException(
          '--binding-file',
          'SessionLength within ScopedAccessSettings must not be greater than'
          ' one day',
      )
    if session_length < 0:
      raise calliope_exceptions.InvalidArgumentException(
          '--binding-file',
          'SessionLength within ScopedAccessSettings must not be less than '
          'zero',
      )

  def _InferEmptySessionSettingsFields(session_settings):
    # When sessionReauthMethod is absent, infer LOGIN
    if session_settings.sessionReauthMethod is None:
      v1_messages = util.GetMessages('v1')
      if isinstance(session_settings, v1_messages.SessionSettings):
        session_settings.sessionReauthMethod = (
            v1_messages.SessionSettings.SessionReauthMethodValueValuesEnum.LOGIN
        )
      else:
        session_settings.sessionReauthMethod = util.GetMessages(
            'v1alpha'
        ).SessionSettings.SessionReauthMethodValueValuesEnum.LOGIN
    # When sessionLengthEnabled is absent, infer True if SessionLength is
    # greater than zero, otherwise infer false.
    if session_settings.sessionLengthEnabled is None:
      session_length = times.ParseDuration(
          session_settings.sessionLength
      ).total_seconds
      if session_length > 0:
        session_settings.sessionLengthEnabled = True
      else:
        session_settings.sessionLengthEnabled = False
    # When useOidcMaxAge is absent, infer False
    if session_settings.useOidcMaxAge is None:
      session_settings.useOidcMaxAge = False

  def _Start(req):
    scoped_access_settings = req.gcpUserAccessBinding.scopedAccessSettings
    for s in scoped_access_settings:
      if not s.activeSettings:
        continue
      session_settings = s.activeSettings.sessionSettings
      if not session_settings:
        continue
      _ValidateSessionSettings(session_settings)
      _InferEmptySessionSettingsFields(session_settings)

  _Start(req)


def _ValidatePrincipalForRestrictedProject(args, req):
  """Validate principal for restricted project."""
  if req.gcpUserAccessBinding and req.gcpUserAccessBinding.scopedAccessSettings:
    for sas in req.gcpUserAccessBinding.scopedAccessSettings:
      if (
          sas.scope
          and sas.scope.clientScope
          and getattr(sas.scope.clientScope, 'restrictedProject', None)
      ):
        break
    else:
      # No restricted project scope found.
      return

  if properties.VALUES.access_context_manager.enable_gcsl.GetBool():
    # hasattr(args, 'group_key') checks if we are in create command which has
    # principal args.
    if hasattr(args, 'group_key') and not args.IsKnownAndSpecified(
        'federated_principal'
    ):
      raise calliope_exceptions.InvalidArgumentException(
          '--binding-file',
          'When using a restricted project scope, --federated-principal must be'
          ' specified.',
      )


def ProcessScopedAccessSettings(unused_ref, args, req):
  """Hook to process and validate scoped access settings from the request."""

  def _ValidateRestrictedClientApplicationNamesAndClientIdsAreNotSpecified(
      args,
  ):
    legacy_prca_fields_specified = args.IsKnownAndSpecified(
        'restricted_client_application_names'
    ) or args.IsKnownAndSpecified('restricted_client_application_client_ids')
    if legacy_prca_fields_specified:
      raise calliope_exceptions.InvalidArgumentException(
          '--binding-file',
          'The binding-file cannot be specified at the same time as'
          ' `--restricted-client-application-names` or'
          ' `--restricted-client-application-client-ids`.',
      )

  def _Start(unused_ref, args, req):
    del unused_ref
    if not args.IsKnownAndSpecified('binding_file'):
      return req

    _ValidateRestrictedClientApplicationNamesAndClientIdsAreNotSpecified(args)
    _ProcessScopesInScopedAccessSettings(req)
    _ProcessAccessSettingsInScopedAccessSettings(req)
    _ProcessAccessLevelsInScopedAccessSettings(args, req)
    _ProcessSessionSettingsInScopedAccessSettings(req)
    _ValidatePrincipalForRestrictedProject(args, req)

    return req

  return _Start(unused_ref, args, req)


class InvalidFormatError(common.ParseFileError):

  def __init__(self, path, reason):
    super(InvalidFormatError, self).__init__(
        path,
        (
            'Invalid format: {}\n\n'
            ' A binding-file is a YAML-formatted file'
            ' containing a single gcpUserAccessBinding.'
            ' For example:\n\n'
            '  scopedAccessSettings:\n'
            '  - scope:\n'
            '      clientScope:\n'
            '        restrictedClientApplication:\n'
            '          name: Cloud Console\n'
            '    activeSettings:\n'
            '      accessLevels:\n'
            '      - accessPolicies/123/accessLevels/access_level_1\n'
            '    dryRunSettings:\n'
            '      accessLevels:\n'
            '      - accessPolicies/123/accessLevels/dry_run_access_level_1\n'
            '  - scope:\n'
            '      clientScope:\n'
            '        restrictedClientApplication:\n'
            '          clientId: my_client_id.google.com\n'
            '    activeSettings:\n'
            '      accessLevels:\n'
            '      - accessPolicies/123/accessLevels/access_level_2\n'
            '    dryRunSetting:\n'
            '      accessLevels:\n'
            '      - accessPolicies/123/accessLevels/dry_run_access_level_2\n'
        ).format(
            reason,
        ),
    )


def ParseGcpUserAccessBindingFromBindingFile(api_version):
  """Parse a GcpUserAccessBinding from a YAML file.

  Args:
    api_version: str, the API version to use for parsing the messages

  Returns:
    A function that parses a GcpUserAccessBinding from a file.
  """

  def _ValidateSingleGcpUserAccessBinding(bindings):
    if len(bindings) > 1:
      raise calliope_exceptions.InvalidArgumentException(
          '--input-file',
          'The input file contains more than one GcpUserAccessBinding. '
          'Please specify only one GcpUserAccessBinding in the input file.',
      )

  def _ParseVersionedGcpUserAccessBindingFromBindingFile(path):
    bindings = common.ParseAccessContextManagerMessagesFromYaml(
        path, util.GetMessages(version=api_version).GcpUserAccessBinding, False
    )
    _ValidateSingleGcpUserAccessBinding(bindings)
    GcpUserAccessBindingStructureValidator(path, bindings[0]).Validate()
    return bindings[0]

  return _ParseVersionedGcpUserAccessBindingFromBindingFile


class GcpUserAccessBindingStructureValidator:
  """Validates a GcpUserAccessBinding structure against unrecognized fields."""

  def __init__(self, path, gcp_user_access_binding):
    self.path = path
    self.gcp_user_access_binding = gcp_user_access_binding

  def Validate(self):
    """Validates the GcpUserAccessBinding structure."""
    self._ValidateAllFieldsRecognizedForGcpUserAccessBinding(
        self.gcp_user_access_binding
    )
    self._ValidateScopedAccessSettings(
        self.gcp_user_access_binding.scopedAccessSettings
    )

  def _ValidateScopedAccessSettings(self, scoped_access_settings_list):
    """Validates the ScopedAccessSettings structure."""
    if scoped_access_settings_list:
      for i in range(len(scoped_access_settings_list)):
        scoped_access_settings = scoped_access_settings_list[i]
        self._ValidateAllFieldsRecognized(scoped_access_settings)
        self._ValidateAccessScope(scoped_access_settings.scope)
        self._ValidateAccessSettings(scoped_access_settings.activeSettings)
        self._ValidateAccessSettings(scoped_access_settings.dryRunSettings)

  def _ValidateAccessScope(self, access_scope):
    """Validates the AccessScope structure."""
    if access_scope:
      self._ValidateAllFieldsRecognized(access_scope)
      self._ValidateClientScope(access_scope.clientScope)

  def _ValidateClientScope(self, client_scope):
    """Validates the AccessScopeType structure."""
    if client_scope:
      self._ValidateAllFieldsRecognized(client_scope)
      self._ValidateRestrictedClientApplication(
          client_scope.restrictedClientApplication
      )
      if (
          properties.VALUES.access_context_manager.enable_gcsl.GetBool()
          and hasattr(client_scope, 'restrictedProject')
      ):
        self._ValidateProject(client_scope.restrictedProject)

  def _ValidateRestrictedClientApplication(self, restricted_client_application):
    """Validates the RestrictedClientApplications."""
    if restricted_client_application:
      self._ValidateAllFieldsRecognized(restricted_client_application)

  def _ValidateProject(self, restricted_project):
    """Validates the Project."""
    if restricted_project:
      self._ValidateAllFieldsRecognized(restricted_project)

  def _ValidateSessionSettings(self, session_settings):
    """Validate the SessionSettings."""
    if session_settings:
      self._ValidateAllFieldsRecognized(session_settings)

  def _ValidateAccessSettings(self, access_settings):
    """Validates the AccessSettings structure."""
    if access_settings:
      self._ValidateAllFieldsRecognized(access_settings)
      self._ValidateSessionSettings(access_settings.sessionSettings)

  def _ValidateAllFieldsRecognizedForGcpUserAccessBinding(
      self, gcp_user_access_binding
  ):
    """Validates that all fields in the GcpUserAccessBinding are recognized.

    Note:Because ScopedAccessSettings is the only field supported in the
    GcpUserAccessBinding, a custom validation is required.

    Args:
      gcp_user_access_binding: The GcpUserAccessBinding to validate

    Raises:
      InvalidFormatError: if the GcpUserAccessBinding contains unrecognized
      fields
    """
    valid_fields = ['scopedAccessSettings']
    unrecognized_fields = set()
    empty_list = []
    if gcp_user_access_binding.accessLevels != empty_list:
      unrecognized_fields.add('accessLevels')
    if gcp_user_access_binding.dryRunAccessLevels != empty_list:
      unrecognized_fields.add('dryRunAccessLevels')
    if gcp_user_access_binding.groupKey is not None:
      unrecognized_fields.add('groupKey')
    if gcp_user_access_binding.name:
      unrecognized_fields.add('name')
    if (
        hasattr(gcp_user_access_binding, 'principal')
        and gcp_user_access_binding.principal is not None
    ):
      unrecognized_fields.add('principal')
    if gcp_user_access_binding.sessionSettings is not None:
      unrecognized_fields.add('sessionSettings')
    if gcp_user_access_binding.restrictedClientApplications:
      unrecognized_fields.add('restrictedClientApplications')
    if gcp_user_access_binding.all_unrecognized_fields():
      unrecognized_fields.update(
          gcp_user_access_binding.all_unrecognized_fields()
      )
    if unrecognized_fields:
      raise InvalidFormatError(
          self.path,
          '"{}" contains unrecognized fields: [{}]. Valid fields are: [{}].'
          .format(
              type(self.gcp_user_access_binding).__name__,
              ', '.join(unrecognized_fields),
              ', '.join(valid_fields),
          ),
      )

  def _ValidateAllFieldsRecognized(self, message):
    """Validates that all fields in the message are recognized.

    Args:
      message: object to validate

    Raises:
      InvalidFormatError: if the message contains unrecognized fields
    """
    unrecognized_fields_set = set(message.all_unrecognized_fields())
    message_type = type(message)
    valid_fields_list = [f.name for f in message_type.all_fields()]
    if message_type.__name__ == 'ClientScope':
      if not properties.VALUES.access_context_manager.enable_gcsl.GetBool():
        if 'restrictedProject' in valid_fields_list:
          valid_fields_list.remove('restrictedProject')
        if hasattr(message, 'restrictedProject') and message.restrictedProject:
          unrecognized_fields_set.add('restrictedProject')

    if unrecognized_fields_set:
      raise InvalidFormatError(
          self.path,
          '"{}" contains unrecognized fields: [{}]. Valid fields are: [{}]'
          .format(
              message_type.__name__,
              ', '.join(sorted(unrecognized_fields_set)),
              ', '.join(sorted(valid_fields_list)),
          ),
      )
