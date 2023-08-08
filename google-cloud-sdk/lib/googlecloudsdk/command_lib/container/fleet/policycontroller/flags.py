# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Functions to add standardized flags in PoCo commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import argparse

from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.command_lib.container.fleet import resources
from googlecloudsdk.command_lib.container.fleet.policycontroller import exceptions


class Flags:
  """Handle common flags for Poco Commands.

  Use this class to keep command flags that touch similar configuration options
  on the Policy Controller feature in sync across commands.
  """

  def __init__(
      self,
      parser: parser_arguments.ArgumentInterceptor,
      command: str,
  ):
    self._parser = parser
    self._display_name = command

  @property
  def parser(self):  # pylint: disable=invalid-name
    return self._parser

  @property
  def display_name(self):
    return self._display_name

  def AddAuditInterval(self):
    """Adds handling for audit interval configuration changes."""
    self.parser.add_argument(
        '--audit-interval',
        type=int,
        help='How often Policy Controller will audit resources, in seconds.',
        default=60,
    )

  def AddConstraintViolationLimit(self):
    """Adds handling for constraint violation limit configuration changes."""
    self.parser.add_argument(
        '--constraint-violation-limit',
        type=int,
        help=(
            'The number of violations stored on the constraint resource. Must'
            ' be greater than 0.'
        ),
        default=20,
    )

  def AddExemptableNamespaces(self):
    """Adds handling for configuring exemptable namespaces."""
    group = self.parser.add_argument_group(
        'Exemptable Namespace flags.', mutex=True
    )
    group.add_argument(
        '--exemptable-namespaces',
        type=str,
        help=(
            'Namespaces that Policy Controller should ignore, separated by'
            ' commas if multiple are supplied.'
        ),
    )
    group.add_argument(
        '--clear-exemptable-namespaces',
        action='store_true',
        help=(
            'Removes any namespace exemptions, enabling Policy Controller on'
            ' all namespaces.'
        ),
    )

  def AddLogDeniesEnabled(self):
    """Adds handling for log denies enablement."""
    self.parser.add_argument(
        '--log-denies',
        action=EnableDisableAction,
        help=(
            'If set, log all denies and dry run failures. (To disable, use'
            ' --no-log-denies)'
        ),
    )

  def AddMemberships(self):
    """Adds handling for single, multiple or all memberships."""
    group = self.parser.add_argument_group('Membership flags.', mutex=True)
    resources.AddMembershipResourceArg(
        group,
        plural=True,
        membership_help=(
            'The membership names to {}, separated by commas if multiple '
            'are supplied. Ignored if --all-memberships is supplied; if '
            'neither is supplied, a prompt will appear with all available '
            'memberships.'.format(self.display_name)
        ),
    )

    group.add_argument(
        '--all-memberships',
        action='store_true',
        help=(
            'If supplied, {} all Policy Controllers memberships in the fleet.'
            .format(self.display_name)
        ),
        default=False,
    )

  def AddMonitoring(self):
    """Adds handling for monitoring configuration changes."""
    group = self.parser.add_argument_group('Monitoring flags.', mutex=True)
    group.add_argument(
        '--monitoring',
        type=str,
        help=(
            'Monitoring backend options Policy Controller should export metrics'
            ' to, separated by commas if multiple are supplied. Options:'
            ' prometheus, cloudmonitoring'
        ),
    )
    group.add_argument(
        '--no-monitoring',
        action='store_true',
        help=(
            'Include this flag to disable the monitoring configuration of'
            ' Policy Controller.'
        ),
    )

  def AddMutationEnabled(self):
    """Adds handling for mutation enablement."""
    self.parser.add_argument(
        '--mutation',
        action=EnableDisableAction,
        help=(
            'If set, enable support for mutation. (To disable, use'
            ' --no-mutation)'
        ),
    )

  def AddReferentialRulesEnabled(self):
    """Adds handling for referential rules enablement."""
    self.parser.add_argument(
        '--referential-rules',
        action=EnableDisableAction,
        help=(
            'If set, enable support for referential constraints. (To disable,'
            ' use --no-referential-rules)'
        ),
    )

  def AddTemplateLibraryInstall(self):
    """Adds handling for installing the template library."""
    self.parser.add_argument(
        '--template-library',
        action=EnableDisableAction,
        help=(
            'If set, installs a library of constraint templates for common'
            ' policy types. (To disable, use --no-template-library)'
        ),
    )

  def AddVersion(self):
    """Adds handling for version flag."""
    self.parser.add_argument(
        '--version',
        type=str,
        help=(
            'The version of Policy Controller to install; defaults to latest'
            ' version.'
        ),
    )


class EnableDisableAction(argparse.Action):
  """EnableDisableAction is an explicit enable/disable option pair.

  This action is based on BooleanOptionalAction, is largely copied from the
  Python 3.9 library. This is a workaround before the minimum supported version
  of python is updated to 3.9 in gcloud, or the field mask bug is implemented
  (b/233366392), whichever comes first.
  """

  def __init__(
      self,
      option_strings,
      dest,
      default=None,
      type=None,  # pylint: disable=redefined-builtin
      choices=None,
      required=False,
      help=None,  # pylint: disable=redefined-builtin
      metavar=None,
      const=None,
  ):
    self.__called = False
    _option_strings = []  # pylint: disable=invalid-name
    for option_string in option_strings:
      prefix = ''
      if option_string.startswith('--'):
        option_string = option_string[2:]
        prefix = '--'

      _option_strings.append('{}{}'.format(prefix, option_string))
      _option_strings.append('{}no-{}'.format(prefix, option_string))

    if help is not None and default is not None:
      help += ' (default: %(default)s)'

    super(EnableDisableAction, self).__init__(
        option_strings=_option_strings,
        dest=dest,
        nargs=0,
        default=default,
        type=type,
        choices=choices,
        required=required,
        help=help,
        metavar=metavar,
        const=const,
    )

  def __call__(self, parser, namespace, values, option_string=None):
    if self.__called:
      raise exceptions.MutexError(
          'Specify only one flag of: {}'.format(', '.join(self.option_strings))
      )
    self.__called = True

    if option_string in self.option_strings:
      setattr(namespace, self.dest, not option_string.startswith('--no-'))

  def format_usage(self):
    return ' | '.join(self.option_strings)
