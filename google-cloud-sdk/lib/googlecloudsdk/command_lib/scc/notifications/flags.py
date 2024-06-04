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

"""Shared flags definitions for multiple commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from googlecloudsdk.calliope import base

DESCRIPTION_FLAG = base.Argument(
    '--description',
    help="""
      The text that will be used to describe a notification configuration.""",
)

# Note:
# SCC's custom --filter is passing the streaming config filter as part of
# the request body. However --filter is a global filter flag in gcloud. The
# --filter flag in gcloud (outside of this command) is used for client side
# filtering. This has led to a collision in logic as gcloud believes the
# update is trying to perform client side filtering. In the context of
# notifications, it is instead updating the streaming config filter.
#
# Any future new commands should reconsider not using --filter for this logic
# and perhaps use a different name to avoid any collisions with gcloud logic.
FILTER_FLAG = base.Argument(
    '--filter',
    help="""
      Filter to be used for notification config.
    """,
)

FILTER_FLAG_LONG_DESCRIPTION = base.Argument(
    '--filter',
    help="""
      The filter string which will applied to events of findings of a
      notification configuration.
    """,
)

PAGE_TOKEN_FLAG = base.Argument(
    '--page-token',
    help="""
      Response objects will return a non-null value for page-token to
      indicate that there is at least one additional page of data. User can
      either directly request that page by specifying the page-token
      explicitly or let gcloud fetch one-page-at-a-time.""",
)

PUBSUB_TOPIC_OPTIONAL_FLAG = base.Argument(
    '--pubsub-topic',
    help="""
      The Pub/Sub topic which will receive notifications. Its format is
      "projects/[project_id]/topics/[topic]".
    """,
)

PUBSUB_TOPIC_REQUIRED_FLAG = base.Argument(
    '--pubsub-topic',
    required=True,
    help="""
      The Pub/Sub topic which will receive notifications. Its format is
      "projects/[project_id]/topics/[topic]".
    """,
)

CREATE_NOTIFICATION_CONFIG_LOCATION_FLAG = base.Argument(
    '--location',
    help="""
      If data residency is enabled, specify the Security Command Center location
      in which to create the notification. The resulting `notificationConfig`
      resource is stored only in this location. Only findings that are issued
      in this location are sent to Pub/Sub.

      If data residency is not enabled, specifying the `--location` flag creates
      the notification by using Security Command Center API v2, and the only
      valid value for the flag is `global`.
      """,
    default='global',
)

DELETE_NOTIFICATION_CONFIG_LOCATION_FLAG = base.Argument(
    '--location',
    help="""
      Required if either data residency is enabled or the `notificationConfig`
      was created by using the API v2.

      If data residency is enabled, specify the Security Command Center location
      in which the notification is stored.

      If data residency is not enabled, include `/locations/```LOCATION'' in the
      full name or specify the `--location flag` only if the
      `notificationConfig` was created by using the Security Command Center API
      v2, in which case, the only valid location is `global`.
      """,
    default='global',
)

DESCRIBE_NOTIFICATION_CONFIG_LOCATION_FLAG = base.Argument(
    '--location',
    help="""
      Required if either data residency is enabled or the `notificationConfig`
      resources were created by using the API v2.

      If data residency is enabled, specify the Security Command Center location
      in which the notifications are stored.

      If data residency is not enabled, include `/locations/```LOCATION'' only
      if the `notificationConfig` resource was created by using the Security
      Command Center API v2, in which case, the only valid location is `global`.
      """,
    default='global',
)

LIST_NOTIFICATION_CONFIG_LOCATION_FLAG = base.Argument(
    '--location',
    help="""
      Required if either data residency is enabled or the `notificationConfig`
      resources were created by using the API v2.

      If data residency is enabled, specify the Security Command Center location
      in which the notifications are stored.

      If data residency is not enabled, including `/locations/```LOCATION'' in
      the name or the `--location` flag in the command lists only the
      `notificationConfig` resources that were created by using the Security
      Command Center API v2 and the only valid location is `global`.
      """,
    default='global',
)

UPDATE_NOTIFICATION_CONFIG_LOCATION_FLAG = base.Argument(
    '--location',
    help="""
      Required if either data residency is enabled or the `notificationConfig`
      was created by using the API v2.

      If data residency is enabled, specify the Security Command Center location
      in which the notification is stored.

      If data residency is not enabled, include `/locations/```LOCATION'' in the
      full name or specify the `--location` flag only if the
      `notificationConfig` resource was created by using the Security Command
      Center API v2, in which case, the only valid location is `global`.
      """,
    default='global',
)


def AddNotificationConfigPositionalArgument(parser):
  """Add Notification Config as a positional argument."""
  parser.add_argument(
      'NOTIFICATIONCONFIGID',
      metavar='NOTIFICATION_CONFIG_ID',
      help="""\
      The ID of the notification config. Formatted as
      "organizations/123/notificationConfigs/456" or just "456".
      """,
  )
  return parser


def AddParentGroup(parser):
  """Set folder/org/project as mutually exclusive group."""
  resource_group = parser.add_group(required=False, mutex=True)
  resource_group.add_argument(
      '--organization',
      help="""\
        Organization where the notification config resides. Formatted as
        ``organizations/123'' or just ``123''.
        """,
    )
  resource_group.add_argument(
      '--folder',
      help="""\
        Folder where the notification config resides. Formatted as
        ``folders/456'' or just ``456''.
        """,
  )
  resource_group.add_argument(
      '--project',
      help="""\
        Project (ID or number) where the notification config resides.
        Formatted as ``projects/789'' or just ``789''.
        """,
  )
  return parser
