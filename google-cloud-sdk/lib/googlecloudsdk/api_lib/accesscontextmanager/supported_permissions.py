# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""API library for Supported Permissions."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.accesscontextmanager import util


class Client(object):
  """High-level API client for Supported Permissions."""

  def __init__(self, client=None, messages=None, version=None):
    self.client = client or util.GetClient(version=version)
    self.messages = messages or self.client.MESSAGES_MODULE

  def List(self, page_size=100, limit=None):
    """Make API call to list VPC Service Controls supported permissions.

    Args:
      page_size: The page size to list.
      limit: The maximum number of permissions to display.

    Returns:
      The list of VPC Service Controls supported permissions.
    """
    req = self.messages.AccesscontextmanagerPermissionsListRequest()
    return list_pager.YieldFromList(
        self.client.permissions,
        req,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='supportedPermissions',
    )
