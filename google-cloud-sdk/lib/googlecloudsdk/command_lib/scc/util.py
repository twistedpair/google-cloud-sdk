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
"""Shared utility functions for Cloud SCC commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re

from googlecloudsdk.command_lib.scc.errors import InvalidSCCInputError
from googlecloudsdk.core import properties


def GetParentFromPositionalArguments(args):
  """Converts user input to one of: organization, project, or folder."""
  id_pattern = re.compile("[0-9]+")
  parent = None
  if hasattr(args, "parent"):
    if not args.parent:
      parent = properties.VALUES.scc.parent.Get()
    else:
      parent = args.parent

  if parent is None:
    # Use organization property as backup for legacy behavior.
    parent = properties.VALUES.scc.organization.Get()

  if parent is None:
    parent = args.organization

  if parent is None:
    raise InvalidSCCInputError("Could not find Parent argument. Please "
                               "provide the parent argument.")

  if id_pattern.match(parent):
    # Prepend organizations/ if only number value is provided.
    parent = "organizations/" + parent

  if not (parent.startswith("organizations/") or
          parent.startswith("projects/") or parent.startswith("folders/")):
    error_message = ("Parent must match either [0-9]+, organizations/[0-9]+, "
                     "projects/.* "
                     "or folders/.*."
                     "")
    raise InvalidSCCInputError(error_message)

  return parent


def GetParentFromNamedArguments(args):
  """Gets and validates parent from named arguments."""
  if args.organization is not None:
    if "/" in args.organization:
      pattern = re.compile("^organizations/[0-9]{1,19}$")
      if not pattern.match(args.organization):
        raise InvalidSCCInputError(
            "When providing a full resource path, it must include the pattern "
            "'^organizations/[0-9]{1,19}$'.")
      else:
        return args.organization
    else:
      pattern = re.compile("^[0-9]{1,19}$")
      if not pattern.match(args.organization):
        raise InvalidSCCInputError(
            "Organization does not match the pattern '^[0-9]{1,19}$'.")
      else:
        return "organizations/" + args.organization

  if hasattr(args, "folder") and args.folder is not None:
    if "/" in args.folder:
      pattern = re.compile("^folders/.*$")
      if not pattern.match(args.folder):
        raise InvalidSCCInputError(
            "When providing a full resource path, it must include the pattern "
            "'^folders/.*$'.")
      else:
        return args.folder
    else:
      return "folders/" + args.folder

  if hasattr(args, "project") and args.project is not None:
    if "/" in args.project:
      pattern = re.compile("^projects/.*$")
      if not pattern.match(args.project):
        raise InvalidSCCInputError(
            "When providing a full resource path, it must include the pattern "
            "'^projects/.*$'.")
      else:
        return args.project
    else:
      return "projects/" + args.project
