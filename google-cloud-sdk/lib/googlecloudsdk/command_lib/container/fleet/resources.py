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
"""Resources for fleet commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.container.fleet import util as cmd_util
from googlecloudsdk.command_lib.container.fleet.features import base
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io


def PromptForMembership(flag='--membership',
                        message='Please specify a membership:\n'):
  """Prompt the user for a membership from a list of memberships in the fleet.

  This method is referenced by fleet and feature commands as a fallthrough
  for getting the memberships when required.

  Args:
    flag: The name of the membership flag, used in the error message
    message: The message given to the user describing the prompt.

  Returns:
    The membership specified by the user (str), or None if unable to prompt.

  Raises:
    OperationCancelledError if the prompt is cancelled by user
    RequiredArgumentException if the console is unable to prompt
  """

  if console_io.CanPrompt():
    all_memberships, _ = base.ListMembershipsFull()
    idx = console_io.PromptChoice(
        base.MembershipPartialNames(all_memberships),
        message=message,
        cancel_option=True)
    membership = all_memberships[idx]
    return membership
  else:
    raise calliope_exceptions.RequiredArgumentException(
        flag, ('Cannot prompt a console for membership. Membership is '
               'required. Please specify `{}` to select at '
               'least one membership.'.format(flag)))


def _LocationAttributeConfig(help_text=''):
  """Create location attributes in resource argument.

  Args:
    help_text: If set, overrides default help text for `--location`

  Returns:
    Location resource argument parameter config
  """
  fallthroughs = [
      deps.ArgFallthrough('--location'),
      deps.PropertyFallthrough(properties.VALUES.gkehub.location),
  ]
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text=help_text if help_text else ('Location for the {resource}.'),
      fallthroughs=fallthroughs)


def _MembershipAttributeConfig(attr_name, help_text=''):
  """Create membership attributes in resource argument.

  Args:
    attr_name: Name of the resource
    help_text: If set, overrides default help text for `--membership`

  Returns:
    Membership resource argument parameter config
  """
  return concepts.ResourceParameterAttributeConfig(
      name=attr_name,
      help_text=help_text if help_text else ('Name of the {resource}.'))


def AddMembershipResourceArg(parser,
                             api_version='v1',
                             positional=False,
                             plural=False,
                             membership_required=False,
                             membership_arg='',
                             membership_help='',
                             location_help=''):
  """Add resource arg for projects/{}/locations/{}/memberships/{}."""
  flag_name = '--membership'
  if membership_arg:
    flag_name = membership_arg
  elif positional:
    # Flags without '--' prefix are automatically positional
    flag_name = 'MEMBERSHIP_NAME'
  elif plural:
    flag_name = '--memberships'
  spec = concepts.ResourceSpec(
      'gkehub.projects.locations.memberships',
      api_version=api_version,
      resource_name='membership',
      plural_name='memberships',
      disable_auto_completers=True,
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=_LocationAttributeConfig(location_help),
      membershipsId=_MembershipAttributeConfig(
          'memberships' if plural else 'membership', membership_help))
  concept_parsers.ConceptParser.ForResource(
      flag_name,
      spec,
      'The group of arguments defining one or more memberships.'
      if plural else 'The group of arguments defining a membership.',
      plural=plural,
      required=membership_required).AddToParser(parser)


def GetExistingMembershipResourceName(args, positional=False):
  """Gets the resource name of a membership in the fleet using a membership resource argument.

  Assumes the argument is called `--membership`, or `MEMBERSHIP_NAME` if
  positional. Runs ListMemberships call to verify the membership exists.

  Args:
    args: arguments provided to a command, including a membership resource arg
    positional: whether the argument is positional

  Returns:
    The membership resource name (e.g. projects/x/locations/y/memberships/z)

  Raises: googlecloudsdk.core.exceptions.Error if unable to find the membership
  in the fleet
  """
  all_memberships, unavailable = base.ListMembershipsFull()
  if not all_memberships:
    raise exceptions.Error('No memberships available in the fleet.')
  if positional:
    arg_membership = args.membership_name
  else:
    arg_membership = args.membership
  found = []
  for existing_membership in all_memberships:
    if arg_membership in existing_membership:
      found.append(existing_membership)
  if not found:
    raise exceptions.Error(
        'Membership {} not found in the fleet.'.format(arg_membership) +
        (' Locations {} were unavailable.'.format(unavailable
                                                 ) if unavailable else ''))
  elif len(found) > 1:
    raise exceptions.Error(
        ('Multiple memberships named {} found in the fleet. Please use '
         '`--location` or full resource name '
         '(projects/*/locations/*/memberships/*) to specify.'
        ).format(arg_membership))
  elif unavailable:
    raise exceptions.Error(
        ('Locations [{}] unreachable. Please specify a location for membership'
         ' with `--location` or use the full resource name '
         '(projects/*/locations/*/memberships/*)').format(unavailable))
  return found[0]


def MembershipResourceName(args, positional=False):
  """Gets a membership resource name from a membership resource argument.

  Assumes the argument is called `--membership`, or `MEMBERSHIP_NAME` if
  positional.

  Args:
    args: arguments provided to a command, including a membership resource arg
    positional: whether the argument is positional

  Returns:
    The membership resource name (e.g. projects/x/locations/y/memberships/z)
  """
  if positional:
    return args.CONCEPTS.membership_name.Parse().RelativeName()
  return args.CONCEPTS.membership.Parse().RelativeName()


def PluralMembershipsResourceNames(args):
  """Gets a list of membership resource names from a --memberships resource arg.

  Args:
    args: arguments provided to a command, including a plural memberships
      resource arg

  Returns:
    A list of membership resource names (e.g.
    projects/x/locations/y/memberships/z)
  """
  return [m.RelativeName() for m in args.CONCEPTS.memberships.Parse()]


def UseRegionalMemberships(track=None):
  """Returns whether regional memberships should be included.

  This will be updated as regionalization is released, and eventually deleted
  when it is fully rolled out.

  Args:
    track: The release track of the command

  Returns:
    A bool, whether regional memberships are supported for the release track in
    the active environment
  """
  return (track is calliope_base.ReleaseTrack.ALPHA) and (
      cmd_util.APIEndpoint() == cmd_util.AUTOPUSH_API)


def InProdRegionalAllowlist(project, track=None):
  """Returns whether project is allowlisted for regional memberships in Prod.

  This will be updated as regionalization is released, and eventually deleted
  when it is fully rolled out.

  Args:
     project: The parent project ID of the membership
    track: The release track of the command

  Returns:
    A bool, whether project is allowlisted for regional memberships in Prod
  """
  prod_regional_allowlist = [
      'gkeconnect-prober',
      'gkeconnect-e2e',
      'gkehub-cep-test',
      'connectgateway-gke-testing',
      'xuebinz-gke',
      'kolber-anthos-testing',
      'anthonytong-hub2',
      'wenjuntoy2',
      'hub-regionalisation-test',  # For Cloud Console UI testing.
      'a4vm-ui-tests-3',  # For Cloud Console UI testing.
      'm4a-ui-playground-1',  # For Cloud Console UI testing.
      'pikalov-tb',
  ]
  return track is calliope_base.ReleaseTrack.ALPHA and (
      project in prod_regional_allowlist)


def GetMembershipProjects(memberships):
  """Returns all unique project identifiers of the given membership names.

  ListMemberships should use the same identifier (all number or all ID) in
  membership names. Users can convert their own project identifiers for manually
  entering arguments.

  Args:
    memberships: A list of full membership resource names

  Returns:
    A list of project identifiers in the parents of the memberships

  Raises: googlecloudsdk.core.exceptions.Error if unable to parse any membership
  name
  """
  projects = set()
  for m in memberships:
    match = re.match(r'projects\/(.*)\/locations\/(.*)\/memberships\/(.*)', m)
    if not match:
      raise exceptions.Error('Unable to parse membership {} (expected '
                             'projects/*/locations/*/memberships/*)'.format(m))
    projects.add(match.group(1))
  return list(projects)
