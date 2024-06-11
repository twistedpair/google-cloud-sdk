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
"""Flag utils for networkservices commands."""
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.network_services import util
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs


def AddFilteredListFlags(parser):
  """Adds ListCommand args, but filters a few currently unused flags."""
  base.ListCommand.Args(parser)
  base.URI_FLAG.RemoveFromParser(parser)
  base.FILTER_FLAG.RemoveFromParser(parser)
  base.SORT_BY_FLAG.RemoveFromParser(parser)


def AddGatewayAndMeshFlags(parser):
  """Adds gateway and mesh flags to the given parser."""
  group = parser.add_group(
      'Parent of the Route View', mutex=True, required=True
  )
  concept_parsers.ConceptParser(
      specs=[
          presentation_specs.ResourcePresentationSpec(
              '--location',
              util.LocationResourceSpec(),
              'Location of the parent',
          ),
          presentation_specs.ResourcePresentationSpec(
              '--gateway',
              util.GatewayResourceSpec(),
              'Parent Gateway',
              # This hides the location flag for the gateway resource.
              flag_name_overrides={'location': ''},
              group=group,
          ),
          presentation_specs.ResourcePresentationSpec(
              '--mesh',
              util.MeshResourceSpec(),
              'Parent Mesh',
              # This hides the location flag for the mesh resource.
              flag_name_overrides={'location': ''},
              group=group,
          ),
      ],
      command_level_fallthroughs={
          '--gateway.location': ['--location'],
          '--mesh.location': ['--location'],
      },
  ).AddToParser(parser)


def AddRouteViewFlags(parser):
  """Adds routeview flags to the given parser."""
  concept_parsers.ConceptParser(
      specs=[
          presentation_specs.MultitypeResourcePresentationSpec(
              '--route-view',
              util.MeshOrGatewayRouteViewResourceSpec(),
              'RouteView to describe',
              required=True,
          ),
      ],
  ).AddToParser(parser)
