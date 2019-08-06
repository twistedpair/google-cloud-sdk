# -*- coding: utf-8 -*- #
# Copyright 2017 Google LLC. All Rights Reserved.
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
"""Flags for commands that deal with the Org Policies API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.command_lib.resource_manager import completers
from googlecloudsdk.core import properties


def AddIdArgToParser(parser):
  base.Argument(
      'id', metavar='ORG_POLICY_ID',
      help='The Org Policy constraint name.').AddToParser(parser)


class OrgPolicyArgumentInterceptor(parser_arguments.ArgumentInterceptor):

  def AddFlagActionFromAncestors(self, action):
    """Prevents --project flag from being added, but otherwise behaves similarly to the base class."""
    name = action.option_strings[0]
    if name != '--project':
      super(OrgPolicyArgumentInterceptor,
            self).AddFlagActionFromAncestors(action)


def AddCustomResourceFlagsToParser(parser):
  """Add flags for the resource ID and enable custom --project flag to be added by modifying the parser.

  Adds --organization, --folder, and --project flags to the parser. The flags
  are added as a required group with a mutex condition, which ensures that the
  user passes in exactly one of the flags.

  This also overrides the behavior of the parser to filter out the global
  --project flag and allow a custom --project flag to be defined. The parser
  does not allow for the same flag to be set multiple times, and since --project
  is a global flag and is automatically passed in, we cannot define our own
  version of it without this workaround. This originally meant that the
  --project flag did not appear alongside the --folder and --organization flags
  in the documentation. We additionally could not mark them as part of a
  required, mutually exclusive set of flags, and had to roll our own custom
  verifier instead of having gcloud validate the user-specified set of flags for
  us.

  We cannot manually drop the global --project flag in the Args function of a
  Command since the global flags are added after that function is run. This
  seems to be the next best workaround.

  Args:
    parser: ArgumentInterceptor, An argparse parser.
  """
  resource_group = parser.add_group(
      mutex=True,
      required=True,
      help='Resource that is associated with the organization policy.')
  resource_group.add_argument(
      '--organization',
      metavar='ORGANIZATION_ID',
      completer=completers.OrganizationCompleter,
      help='Organization ID.')
  resource_group.add_argument(
      '--folder', metavar='FOLDER_ID', help='Folder ID.')
  # This definition is similar to that of the global --project flag, but has
  # different help text for maintaining consistency with the other flags
  resource_group.add_argument(
      '--project',
      metavar='PROJECT_ID',
      dest='project',
      suggestion_aliases=['--application'],
      completer=completers.ProjectCompleter,
      action=actions.StoreProperty(properties.VALUES.core.project),
      help='Project ID.')

  # Overwrite the class of the parser to be that of a derived class, effectively
  # downcasting the parser object. The new class only overrides a function, so
  # this should be relatively safe.
  parser.__class__ = OrgPolicyArgumentInterceptor
