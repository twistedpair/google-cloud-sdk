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
"""Specify common flags for management gcloud."""

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.resource_manager import completers
from googlecloudsdk.command_lib.scc.manage import constants


def CreateParentFlag(required=False) -> base.Argument:
  """Returns a flag for capturing an org, project, or folder name.

  The flag can be provided in one of 2 forms:
    1. --parent=organizations/<id>, --parent=projects/<id or name>,
    --parent=folders/<id>
    2. One of:
      * --organizations=<id> or organizations/<id>
      * --projects=<id or name> or projects/<id or name>
      * --folders=<id> or folders/<id>

  Args:
    required: whether or not this flag is required
  """

  root = base.ArgumentGroup(mutex=True, required=required)

  root.AddArgument(
      base.Argument(
          '--parent',
          required=False,
          help=("""The parent associated with the custom module. Can be one of
              organizations/<id>, projects/<id or name>, folders/<id>"""),
      )
  )

  root.AddArgument(
      base.Argument(
          '--organization',
          required=False,
          metavar='ORGANIZATION_ID',
          completer=completers.OrganizationCompleter,
          help='The organization associated with the custom module.',
      )
  )

  root.AddArgument(
      base.Argument(
          '--project',
          required=False,
          metavar='PROJECT_ID_OR_NUMBER',
          completer=completers.ProjectCompleter,
          help='The project associated with the custom module.',
      )
  )

  root.AddArgument(
      base.Argument(
          '--folder',
          required=False,
          metavar='FOLDER_ID',
          help='The folder associated with the custom module.',
      )
  )

  return root


def CreateModuleIdOrNameArg(
    module_type: constants.CustomModuleType,
) -> base.Argument:
  """A positional argument representing a custom module ID or name."""
  return base.Argument(
      'module_id_or_name',
      help="""The custom module ID or name. The expected format is {parent}/[locations/global]/MODULE_TYPE/{module_id} or just {module_id}. Where module_id is a numeric identifier 1-20 characters
      in length. Parent is of the form organizations/{id}, projects/{id or name},
      folders/{id}.""".replace(
          'MODULE_TYPE', module_type
      ),
  )
