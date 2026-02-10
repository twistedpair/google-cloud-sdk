# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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

"""Utilities for IAP checks in Cloud Run commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import types

from apitools.base.py import encoding
from apitools.base.py import exceptions as api_exceptions
from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.command_lib.iap import util as iap_command_util
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import properties


def IsOrglessProject(project_id: str) -> bool:
  """Checks if a given project is part of an organization.

  Args:
    project_id: The ID of the project to check.

  Returns:
    True if the project is not associated with any organization, False
    otherwise.
    Also returns True if there are errors fetching the ancestry.
  """
  try:
    ancestry = projects_api.GetAncestry(project_id)
    if not ancestry or not ancestry.ancestor:
      return True
    for ancestor in ancestry.ancestor:
      if ancestor.resourceId.type.startswith('organization'):
        return False
    return True
  except api_exceptions.HttpForbiddenError:
    logging.debug(
        'Permission denied to get project ancestry for [%r]',
        project_id,
        exc_info=True,
    )
    return True
  except api_exceptions.HttpError:
    logging.debug(
        'HTTP error when getting project ancestry for [%r]',
        project_id,
        exc_info=True,
    )
    return True
  except core_exceptions.Error:
    logging.debug(
        'Unknown error when getting project ancestry for [%r]',
        project_id,
        exc_info=True,
    )
    return True


def IsIapAlreadyEnabled(self) -> bool:
  """Checks if IAP is already enabled for the current project.

  Args:
    self: The command object.

  Returns:
    True if IAP is enabled (client ID and secret are present), False otherwise.
  """
  try:
    iap_args = types.SimpleNamespace()
    iap_args.project = properties.VALUES.core.project.Get(required=True)
    iap_args.resource_type = None
    iap_args.service = None
    iap_args.region = None
    iap_args.organization = None
    iap_args.folder = None
    iap_args.version = None
    # TODO: b/419573373 - Update IAP check when visibility label is removed.
    iap_setting_ref = iap_command_util.ParseIapSettingsResource(
        self.ReleaseTrack(),
        iap_args,
        support_cloud_run=True,
    )
    try:
      iap_settings = iap_setting_ref.GetIapSetting()
    except api_exceptions.HttpForbiddenError:
      logging.debug(
          "Permission 'iap.projects.getSettings' denied. Cannot confirm IAP"
          ' status.',
          exc_info=True,
      )
      return False
    except api_exceptions.HttpNotFoundError:
      logging.debug(
          'No project-level IAP settings found for [%r].',
          iap_args.project,
          exc_info=True,
      )
      return False
    except api_exceptions.HttpError:
      logging.debug(
          'Failed to get IAP settings due to HTTP error.',
          exc_info=True,
      )
      return False
    iap_settings_dict = encoding.MessageToDict(iap_settings)
    oauth_settings = iap_settings_dict.get('accessSettings', {}).get(
        'oauthSettings', {}
    )
    client_id = oauth_settings.get('clientId')
    client_secret_sha256 = oauth_settings.get('clientSecretSha256')
    return bool(client_id) and bool(client_secret_sha256)
  except core_exceptions.Error:
    logging.debug('Unknown error when getting IAP settings', exc_info=True)
    return False
