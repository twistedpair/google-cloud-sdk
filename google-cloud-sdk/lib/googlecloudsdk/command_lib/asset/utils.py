# -*- coding: utf-8 -*- #
# Copyright 2018 Google LLC. All Rights Reserved.
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
"""The utils for asset surface."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.calliope import exceptions as gcloud_exceptions
from googlecloudsdk.command_lib.projects import util as project_util
from googlecloudsdk.core import properties


def SetDefaultScopeIfEmpty(unused_ref, args, request):
  """Update the request scope to fall back to core project if not specified.

  Used by Asset Search gcloud `modify_request_hooks`. When --scope flag is not
  specified, it will modify the request.scope to fallback to the core properties
  project.

  Args:
    unused_ref: unused.
    args: The argument namespace.
    request: The request to modify.

  Returns:
    The modified request.
  """
  if args.IsSpecified('scope'):
    VerifyScopeForSearch(request.scope)
  else:
    project_id = properties.VALUES.core.project.GetOrFail()
    request.scope = 'projects/{0}'.format(
        project_util.GetProjectNumber(project_id))
  return request


def VerifyScopeForSearch(scope):
  """Verify the scope is a project number, folder number or org number."""
  if not re.match('^(projects|folders|organizations)/[1-9][0-9]{0,18}$', scope):
    raise gcloud_exceptions.InvalidArgumentException(
        '--scope',
        'A valid scope should be: projects/<number>, organizations/<number> or '
        'folders/<number>.')


def VerifyParentForExport(organization,
                          project,
                          folder,
                          attribute='root cloud asset'):
  """Verify the parent name."""
  if organization is None and project is None and folder is None:
    raise gcloud_exceptions.RequiredArgumentException(
        '--organization or --project or --folder',
        'Should specify the organization, or project, or the folder for '
        '{0}.'.format(attribute))
  if organization and project:
    raise gcloud_exceptions.ConflictingArgumentsException(
        'organization', 'project')
  if organization and folder:
    raise gcloud_exceptions.ConflictingArgumentsException(
        'organization', 'folder')
  if project and folder:
    raise gcloud_exceptions.ConflictingArgumentsException('project', 'folder')


def GetParentNameForExport(organization,
                           project,
                           folder,
                           attribute='root cloud asset'):
  """Gets the parent name from organization Id, project Id, or folder Id."""
  VerifyParentForExport(organization, project, folder, attribute)
  if organization:
    return 'organizations/{0}'.format(organization)
  if folder:
    return 'folders/{0}'.format(folder)
  return 'projects/{0}'.format(project)


def GetFeedParent(organization, project, folder):
  """Get the parent name from organization Number, project Id, or folder Number."""
  if organization:
    return 'organizations/{0}'.format(organization)
  if folder:
    return 'folders/{0}'.format(folder)
  return 'projects/{0}'.format(project_util.GetProjectNumber(project))


def VerifyParentForGetHistory(organization,
                              project,
                              attribute='root cloud asset'):
  """Verify the parent name."""
  if organization is None and project is None:
    raise gcloud_exceptions.RequiredArgumentException(
        '--organization or --project',
        'Should specify the organization, or project for {0}.'.format(
            attribute))
  if organization and project:
    raise gcloud_exceptions.ConflictingArgumentsException(
        'organization', 'project')


def GetParentNameForGetHistory(organization,
                               project,
                               attribute='root cloud asset'):
  """Gets the parent name from organization Id, project Id."""
  VerifyParentForGetHistory(organization, project, attribute)
  if organization:
    return 'organizations/{0}'.format(organization)
  return 'projects/{0}'.format(project)


def VerifyParentForAnalyzeIamPolicy(organization,
                                    folder,
                                    attribute='root cloud asset'):
  """Verify the parent name."""
  if organization is None and folder is None:
    raise gcloud_exceptions.RequiredArgumentException(
        '--organization or --folder',
        'Should specify the organization, or the folder for '
        '{0}.'.format(attribute))
  if organization and folder:
    raise gcloud_exceptions.ConflictingArgumentsException(
        'organization', 'folder')


def GetParentNameForAnalyzeIamPolicy(organization,
                                     folder,
                                     attribute='root cloud asset'):
  """Gets the parent name from organization Id or folder Id."""
  VerifyParentForAnalyzeIamPolicy(organization, folder, attribute)
  if organization:
    return 'organizations/{0}'.format(organization)
  return 'folders/{0}'.format(folder)
