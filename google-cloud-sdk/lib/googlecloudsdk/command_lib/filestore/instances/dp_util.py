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
"""Module for deletion protection related utility functions."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import parser_errors

_DELETION_PROTECTION_GROUP_HELP = """\
Deletion protection control options. When deletion protection is enabled,
the instance cannot be deleted."""

_DELETION_PROTECTION_HELP = 'Enables deletion protection for the instance.'

_DELETION_PROTECTION_REASON_HELP = """\
The reason for enabling deletion protection for the instance."""


def AddDeletionProtectionCreateArgs(parser):
  """Adds deletion protection related create flags to the parser."""

  group = parser.add_group(
      help=_DELETION_PROTECTION_GROUP_HELP,
      required=False)

  group.add_argument(
      '--deletion-protection',
      action='store_true',
      default=None,
      required=True,
      help=_DELETION_PROTECTION_HELP)

  group.add_argument(
      '--deletion-protection-reason',
      required=False,
      help=_DELETION_PROTECTION_REASON_HELP)


def AddDeletionProtectionUpdateArgs(parser):
  """Adds deletion protection related update flags to the parser."""
  group = parser.add_group(
      help=_DELETION_PROTECTION_GROUP_HELP)

  group.add_argument(
      '--deletion-protection',
      action=arg_parsers.StoreTrueFalseAction,
      help=_DELETION_PROTECTION_HELP)

  group.add_argument(
      '--deletion-protection-reason',
      help=_DELETION_PROTECTION_REASON_HELP)


def GetDeletionProtectionUpdateMask(args):
  """Returns the update mask for deletion protection.

  Args:
    args: The args from the command.
  """

  mask = []
  if (args.IsSpecified('deletion_protection')):
    mask.append('deletionProtectionEnabled')

  if args.IsSpecified('deletion_protection_reason'):
    mask.append('deletionProtectionReason')

  return mask


def ValidateDeletionProtectionUpdateArgs(args):
  """Validates the deletion protection args.

  Args:
    args: The args from the command.
  """
  deletion_protection_enabled = args.deletion_protection
  deletion_protection_reason = args.deletion_protection_reason

  if (deletion_protection_enabled is not None
      and not deletion_protection_enabled
      and deletion_protection_reason is not None):
    raise parser_errors.ArgumentException(
        '--deletion-protection-reason cannot be used with '
        '--no-deletion-protection')
