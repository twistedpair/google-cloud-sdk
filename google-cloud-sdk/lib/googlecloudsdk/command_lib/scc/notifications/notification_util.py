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

"""Shared util methods common to Notification commands."""
import re
from googlecloudsdk.command_lib.scc import errors
from googlecloudsdk.command_lib.scc import util


def GetNotificationConfigName(args):
  """Returns relative resource name for a notification config."""
  resource_pattern = re.compile(
      "(organizations|projects|folders)/.+/notificationConfigs/[a-zA-Z0-9-_]{1,128}$"
  )
  id_pattern = re.compile("[a-zA-Z0-9-_]{1,128}$")
  notification_config_id = args.NOTIFICATIONCONFIGID
  if not resource_pattern.match(
      notification_config_id
  ) and not id_pattern.match(notification_config_id):
    raise errors.InvalidNotificationConfigError(
        "NotificationConfig must match either (organizations|projects|folders)/"
        ".+/notificationConfigs/[a-zA-Z0-9-_]{1,128})$ or "
        "[a-zA-Z0-9-_]{1,128}$."
    )

  if resource_pattern.match(notification_config_id):
    # Handle config id as full resource name
    return notification_config_id

  return (
      util.GetParentFromNamedArguments(args)
      + "/notificationConfigs/"
      + notification_config_id
  )


def GetParentFromResourceName(resource_name):
  resource_pattern = re.compile("(organizations|projects|folders)/.*")
  if not resource_pattern.match(resource_name):
    raise errors.InvalidSCCInputError(
        "When providing a full resource path, it must also include the pattern "
        "the organization, project, or folder prefix."
    )
  list_organization_components = resource_name.split("/")
  return list_organization_components[0] + "/" + list_organization_components[1]


def ValidateMutexOnConfigIdAndParent(args, parent):
  """Validates that only a full resource name or split arguments are provided."""
  notification_config_id = args.NOTIFICATIONCONFIGID
  if "/" in notification_config_id:
    if parent is not None:
      raise errors.InvalidNotificationConfigError(
          "Only provide a full resource name "
          "(organizations/123/notificationConfigs/test-config) "
          "or an --(organization|folder|project) flag, not both."
      )
  elif parent is None:
    raise errors.InvalidNotificationConfigError(
        "A corresponding parent by a --(organization|folder|project) flag must "
        "be provided if it is not included in notification ID."
    )
