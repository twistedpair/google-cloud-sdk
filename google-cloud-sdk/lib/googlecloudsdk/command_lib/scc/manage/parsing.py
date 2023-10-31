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
"""Common flag parsing for management gcloud."""

import re

from googlecloudsdk.api_lib.resource_manager import folders
from googlecloudsdk.command_lib.scc.manage import constants
from googlecloudsdk.command_lib.scc.manage import errors
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

_CUSTOM_MODULE_ID_REGEX = re.compile('[0-9]{1,20}')


def GetParentResourceNameFromArgs(args) -> str:
  """Returns the relative path to the parent from args.

  Args:
    args: command line args.

  Returns:
    The relative path. e.g. 'projects/foo', 'folders/1234'.
  """
  if args.parent:
    return _ParseParent(args.parent).RelativeName()

  return _GetParentResourceFromArgs(args).RelativeName()


def _GetParentResourceFromArgs(args):
  if args.organization:
    return resources.REGISTRY.Parse(
        args.organization, collection='cloudresourcemanager.organizations'
    )
  elif args.folder:
    return folders.FoldersRegistry().Parse(
        args.folder, collection='cloudresourcemanager.folders'
    )
  else:
    return resources.REGISTRY.Parse(
        args.project or properties.VALUES.core.project.Get(required=True),
        collection='cloudresourcemanager.projects',
    )


def GetModuleIdFromArgs(args) -> str:
  """Returns the module id from args."""
  if not args.module_id_or_name:
    raise errors.InvalidCustomModuleIdError(None)

  match = _CUSTOM_MODULE_ID_REGEX.fullmatch(args.module_id_or_name)

  if match:
    return match[0]
  else:
    raise errors.InvalidCustomModuleIdError(args.module_id_or_name)


def GetModuleNameFromArgs(args, module_type: constants.CustomModuleType) -> str:
  """Returns the specified module name from args if it exists.

  Otherwise, an exception is raised detailing the parsing error along with the
  expectation.

  Args:
    args: the args
    module_type: the module type (see
      googlecloudsdk.command_lib.scc.manage.constants)

  Raises:
    MissingCustomModuleNameOrIdError: no module name or id was specified.
    InvalidCustomModuleNameError: the specified module name was invalid.
    InvalidCustomModuleIdError: the specified module id was invalid.
  """

  if not args.module_id_or_name:
    raise errors.MissingCustomModuleNameOrIdError()

  # First try to see if we can parse a resource name
  collections = [
      f'securitycentermanagement.organizations.locations.{module_type}',
      f'securitycentermanagement.projects.locations.{module_type}',
      f'securitycentermanagement.folders.locations.{module_type}',
  ]

  is_possible_resource_name = (
      _IsPossibleResourceName(args.module_id_or_name)
      or len(args.GetSpecifiedArgNames()) == 1
  )

  for collection in collections:
    try:
      return resources.REGISTRY.Parse(
          args.module_id_or_name, collection=collection
      ).RelativeName()
    except resources.RequiredFieldOmittedException:
      pass

  if is_possible_resource_name:
    # The error messages provided by the default gcloud parsing are awful so we
    # detect a resource name misformatting here and print a better error
    raise errors.InvalidCustomModuleNameError(
        args.module_id_or_name, module_type
    )

  parent = GetParentResourceNameFromArgs(args)
  module_id = GetModuleIdFromArgs(args)

  return f'{parent}/locations/global/{module_type}/{module_id}'


def _ParseParent(parent: str) -> str:
  """Extracts parent name from a string of the form {organizations|projects|folders}/<id>."""

  if parent.startswith('organizations/'):
    return resources.REGISTRY.Parse(
        parent, collection='cloudresourcemanager.organizations'
    )
  elif parent.startswith('folders/'):
    return folders.FoldersRegistry().Parse(
        parent, collection='cloudresourcemanager.folders'
    )
  elif parent.startswith('projects/'):
    return resources.REGISTRY.Parse(
        parent,
        collection='cloudresourcemanager.projects',
    )
  else:
    raise errors.InvalidParentError(parent)


def _IsPossibleResourceName(name: str) -> bool:
  return (
      name.startswith('organizations')
      or name.startswith('projects')
      or name.startswith('folders')
  )
