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

"""The mcp command group for the Cloud API Registry API."""

from googlecloudsdk.calliope import base


# NOTE: Release track decorators can be used here as well, and would propagate
# to this group's children.
class Mcp(base.Group):
  """Manage API Registry MCP Command Group.

  This command group is used to enable and disable MCP enablement for a given
  service in the current project.
  The current library contains utilitiy functions that are used by the
  enablement and disablement commands.
  """
