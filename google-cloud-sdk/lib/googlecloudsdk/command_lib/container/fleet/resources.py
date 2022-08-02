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

from googlecloudsdk.api_lib.container.fleet import util
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.container.fleet.features import base
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io

SUPPORTED_LOCATIONS = ('global')


def PromptForLocation(available_locations=SUPPORTED_LOCATIONS):
  """Prompt for location from list of available locations.

  This method is referenced by fleet commands as a fallthrough
  for getting the location when required.

  Args:
    available_locations: list of the available locations to choose from

  Returns:
    The location specified by the user (str), or None if unable to prompt.

  Raises:
    OperationCancelledError if the prompt is cancelled by user
  """

  if console_io.CanPrompt():
    all_locations = list(available_locations)
    idx = console_io.PromptChoice(
        all_locations,
        message='Please specify a location:\n',
        cancel_option=True)
    location = all_locations[idx]
    return location


def PromptForMembership():
  """Prompt for memberships from list of memberships.

  This method is referenced by fleet commands as a fallthrough
  for getting the memberships when required.

  Returns:
    The membership specified by the user (str), or None if unable to prompt.

  Raises:
    OperationCancelledError if the prompt is cancelled by user
  """

  if console_io.CanPrompt():
    all_memberships = base.ListMembershipsFull()
    partial = [util.MembershipPartialName(m) for m in all_memberships]
    idx = console_io.PromptChoice(
        partial, message='Please specify a membership:\n', cancel_option=True)
    membership = all_memberships[idx]
    return membership


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


def PositionalMembershipResourceName(args):
  """Gets a membership resource name from a resource argument MEMBERSHIP_NAME.

  Args:
    args: arguments provided to a command, including a membership resource arg

  Returns:
    The membership resource name (e.g. projects/x/locations/y/memberships/z)
  """
  return args.CONCEPTS.membership_name.Parse().RelativeName()


def MembershipResourceName(args):
  """Gets a membership resource name from a --membership resource argument.

  Args:
    args: arguments provided to a command, including a membership resource arg

  Returns:
    The membership resource name (e.g. projects/x/locations/y/memberships/z)
  """
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
