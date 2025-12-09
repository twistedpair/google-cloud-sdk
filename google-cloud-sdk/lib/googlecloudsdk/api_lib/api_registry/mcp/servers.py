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

"""Class for MCP Servers API client."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.api_registry import utils


class McpServersClient(object):
  """Client for MCP Servers API."""

  def __init__(self, version, client=None, messages=None):
    self.client = client or utils.GetClientInstance(version=version)
    self.messages = messages or utils.GetMessagesModule(
        version, client=self.client
    )
    self._service = self.client.projects_locations_mcpServers

  def ListAlpha(self, request, args):
    """List MCP Servers in the API Registry.

    Args:
      request: (CloudapiregistryProjectsLocationsMcpServersListRequest) input
        message
      args: (arg_parsers.ArgumentParser) command line arguments

    Returns:
      A list of MCP Servers.
    """

    filter_str = 'enabled=true'
    if args.all:
      filter_str = 'enabled=false'

    list_req = (
        self.messages.
        CloudapiregistryProjectsLocationsMcpServersListRequest(
            parent=request, filter=filter_str))

    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='mcpServers',
        batch_size_attribute='pageSize')

  def ListBeta(self, request, args):
    """List MCP Servers in the API Registry.

    Args:
      request:
        (CloudapiregistryProjectsLocationsMcpServersListRequest)
        input message
      args:
        (arg_parsers.ArgumentParser)
        command line arguments

    Returns:
      A list of MCP Servers.
    """

    filter_str = 'enabled=true'
    if args.all:
      filter_str = 'enabled=false'

    list_req = (
        self.messages.
        CloudapiregistryProjectsLocationsMcpServersListRequest(
            parent=request, filter=filter_str))

    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='mcpServers',
        batch_size_attribute='pageSize')
