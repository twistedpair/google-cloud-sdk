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
"""Apphub Command Lib Utils."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.apphub import consts
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def GetProjectLocationResource(locations_id):
  return resources.REGISTRY.Parse(
      locations_id,
      params={
          consts.Resource.PROJECTS_ID: properties.VALUES.core.project.GetOrFail,
      },
      collection=consts.Collections.PROJECTS_LOCATIONS,
  )


def GetGlobalTopologyResourceRelativeName():
  return (
      GetProjectLocationResource(consts.Resource.GLOBAL_LOCATION).RelativeName()
      + consts.Topology.TOPOLOGY_SUFFIX
  )


def GetGlobalTelemetryResourceRelativeName():
  return (
      GetProjectLocationResource(consts.Resource.GLOBAL_LOCATION).RelativeName()
      + consts.Telemetry.TELEMETRY_SUFFIX
  )
