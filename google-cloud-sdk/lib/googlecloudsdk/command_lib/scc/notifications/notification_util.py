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
from googlecloudsdk.command_lib.scc.util import GetParentFromNamedArguments
from googlecloudsdk.core import exceptions as core_exceptions


class InvalidNotificationConfigError(core_exceptions.Error):
  """Exception raised for errors in the input."""


def GetNotificationConfigName(args):
  """Returns relative resource name for a notification config."""
  resource_pattern = re.compile(
      "(organizations|projects|folders)/.+/notificationConfigs/[a-zA-Z0-9-_]{1,128}$"
  )
  id_pattern = re.compile("[a-zA-Z0-9-_]{1,128}$")

  if not resource_pattern.match(
      args.NOTIFICATIONCONFIGID
  ) and not id_pattern.match(args.NOTIFICATIONCONFIGID):
    raise InvalidNotificationConfigError(
        "NotificationConfig must match either (organizations|projects|folders)/"
        ".+/notificationConfigs/[a-zA-Z0-9-_]{1,128})$ or "
        "[a-zA-Z0-9-_]{1,128}$."
    )

  if resource_pattern.match(args.NOTIFICATIONCONFIGID):
    # Handle config id as full resource name
    return args.NOTIFICATIONCONFIGID

  return (
      GetParentFromNamedArguments(args)
      + "/notificationConfigs/"
      + args.NOTIFICATIONCONFIGID
  )


def ValidateMutexOnConfigIdAndParent(args, parent):
  """Validates that only a full resource name or split arguments are provided."""
  if "/" in args.NOTIFICATIONCONFIGID:
    if parent is not None:
      raise InvalidNotificationConfigError(
          "Only provide a full resource name "
          "(organizations/123/notificationConfigs/test-config) "
          "or an --(organization|folder|project) flag, not both."
      )
  elif parent is None:
    raise InvalidNotificationConfigError(
        "A corresponding parent by a --(organization|folder|project) flag must "
        "be provided if it is not included in notification ID."
    )
