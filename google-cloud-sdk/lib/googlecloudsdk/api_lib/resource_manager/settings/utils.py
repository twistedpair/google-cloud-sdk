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
"""Utilities for manipulating organization policies."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.resource_manager.settings import service as settings_service

ORGANIZATION = 'organization'
FOLDER = 'folder'
PROJECT = 'project'


def ComputeResourceType(args):
  """Returns the resource type from the user-specified arguments.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
  """
  if args.organization:
    resource_type = ORGANIZATION
  elif args.folder:
    resource_type = FOLDER
  else:
    resource_type = PROJECT

  return resource_type


def GetPatchRequestFromResourceType(resource_type, name, local_value, etag):
  """Returns the Setting from the user-specified arguments.

  Args:
    resource_type: A String object that contains the resource type
    name: The resource name of the setting and has the following syntax:
      [organizations|folders|projects]/{resource_id}/settings/{setting_name}.
    local_value: The configured value of the setting at the given parent
      resource
    etag: A fingerprint used for optimistic concurrency.
  """

  setting = settings_service.ResourceSettingsMessages(
  ).Setting(
      name=name, value=local_value, etag=etag)

  if resource_type == ORGANIZATION:
    request = settings_service.ResourceSettingsMessages(
    ).CloudresourcemanagerOrganizationsSettingsPatchRequest(
        name=name, setting=setting)
  elif resource_type == FOLDER:
    request = settings_service.ResourceSettingsMessages(
    ).CloudresourcemanagerFoldersSettingsPatchRequest(
        name=name, setting=setting)
  else:
    request = settings_service.ResourceSettingsMessages(
    ).CloudresourcemanagerProjectsSettingsPatchRequest(
        name=name, setting=setting)

  return request


def GetDescribeRequestFromArgs(args, setting_name, is_effective):
  """Returns the get_request from the user-specified arguments.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
    setting_name: setting name such as `settings/iam-projectCreatorRoles`
    is_effective: indicate if it is requesting for an effective setting
  """

  messages = settings_service.ResourceSettingsMessages()

  if args.organization:
    if is_effective:
      get_request = (
          messages.CloudresourcemanagerOrganizationsEffectiveSettingsGetRequest(
              name=setting_name
          )
      )
    else:
      get_request = (
          messages.CloudresourcemanagerOrganizationsSettingsGetRequest(
              name=setting_name
          )
      )
  elif args.folder:
    if is_effective:
      get_request = (
          messages.CloudresourcemanagerFoldersEffectiveSettingsGetRequest(
              name=setting_name
          )
      )
    else:
      get_request = messages.CloudresourcemanagerFoldersSettingsGetRequest(
          name=setting_name
      )
  else:
    if is_effective:
      get_request = (
          messages.CloudresourcemanagerProjectsEffectiveSettingsGetRequest(
              name=setting_name
          )
      )
    else:
      get_request = messages.CloudresourcemanagerProjectsSettingsGetRequest(
          name=setting_name
      )

  return get_request


def GetListRequestFromArgs(args, parent_resource):
  """Returns the get_request from the user-specified arguments.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
    parent_resource: resource location such as `organizations/123`
  """

  messages = settings_service.ResourceSettingsMessages()

  if args.organization:
    get_request = messages.CloudresourcemanagerOrganizationsSettingsListRequest(
        parent=parent_resource)
  elif args.folder:
    get_request = messages.CloudresourcemanagerFoldersSettingsListRequest(
        parent=parent_resource)
  else:
    get_request = messages.CloudresourcemanagerProjectsSettingsListRequest(
        parent=parent_resource)

  return get_request


def GetDeleteValueRequestFromArgs(args, setting_name):
  """Returns the get_request from the user-specified arguments.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
    setting_name: setting name such as `settings/iam-projectCreatorRoles`
  """

  messages = settings_service.ResourceSettingsMessages()

  if args.organization:
    get_request = (
        messages.CloudresourcemanagerOrganizationsSettingsClearRequest(
            name=setting_name
        )
    )
  elif args.folder:
    get_request = messages.CloudresourcemanagerFoldersSettingsClearRequest(
        name=setting_name
    )
  else:
    get_request = messages.CloudresourcemanagerProjectsSettingsClearRequest(
        name=setting_name
    )

  return get_request


def GetServiceFromArgs(args):
  """Returns the service from the user-specified arguments.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
  """

  resource_type = ComputeResourceType(args)

  return GetServiceFromResourceType(resource_type)


def GetServiceFromResourceType(resource_type):
  """Returns the service from the resource type input.

  Args:
    resource_type: A String object that contains the resource type
  """

  if resource_type == ORGANIZATION:
    service = settings_service.OrganizationsSettingsService()
  elif resource_type == FOLDER:
    service = settings_service.FoldersSettingsService()
  else:
    service = settings_service.ProjectsSettingsService()

  return service


def GetEffectiveServiceFromArgs(args):
  """Returns the service from the user-specified arguments.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
  """

  resource_type = ComputeResourceType(args)

  return GetEffectiveServiceFromResourceType(resource_type)


def GetEffectiveServiceFromResourceType(resource_type):
  """Returns the service from the resource type input.

  Args:
    resource_type: A String object that contains the resource type
  """

  if resource_type == ORGANIZATION:
    service = settings_service.OrganizationsEffectiveSettingsService()
  elif resource_type == FOLDER:
    service = settings_service.FoldersEffectiveSettingsService()
  else:
    service = settings_service.ProjectsEffectiveSettingsService()

  return service
