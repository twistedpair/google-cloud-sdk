# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Utils for Edge Cache commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Union

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import resources
from googlecloudsdk.generated_clients.apis.networkservices.v1 import networkservices_v1_messages as v1_msgs
from googlecloudsdk.generated_clients.apis.networkservices.v1alpha1 import networkservices_v1alpha1_messages as v1alpha1_msgs


def SetLocationAsGlobal():
  """Set default location to global."""
  return 'global'


def SetFailoverOriginRelativeName(unused_ref, args, request):
  """Parse the provided failover origin to a relative name.

  Relative name includes defaults (or overridden values) for project & location.
  Location defaults to 'global'.

  Args:
    unused_ref: A string representing the operation reference. Unused and may be
      None.
    args: The argparse namespace.
    request: The request to modify.

  Returns:
    The updated request.
  """

  # request.parent has the form 'projects/<project>/locations/<location>'
  project = request.parent.split('/')[1]

  request.edgeCacheOrigin.failoverOrigin = resources.REGISTRY.Parse(
      args.failover_origin,
      params={
          'projectsId': args.project or project,
          'locationsId': args.location or SetLocationAsGlobal(),
          'edgeCacheOriginsId': request.edgeCacheOriginId
      },
      collection='networkservices.projects.locations.edgeCacheOrigins'
  ).RelativeName()
  return request


def GetFlexShielding(
    api_version: str, region: str
) -> Union[v1_msgs.FlexShieldingOptions, v1alpha1_msgs.FlexShieldingOptions]:
  """Get a FlexShieldingOptions message from a specified FlexShieldingRegion.

  Args:
    api_version: The API version to use, e.g. 'v1' or 'v1alpha1'.
    region: The FlexShieldingRegion to use, e.g. 'me_central1', or empty string.

  Returns:
    A FlexShieldingOptions message, or None if the region is empty.
  """
  if not region:
    return None

  messages = apis.GetMessagesModule('networkservices', api_version)
  regions_enum = (
      messages.FlexShieldingOptions.FlexShieldingRegionsValueListEntryValuesEnum
  )

  return messages.FlexShieldingOptions(
      flexShieldingRegions=[
          regions_enum.lookup_by_name(region.upper()),
      ]
  )


def GetFlexShieldingGA(region: str) -> v1_msgs.FlexShieldingOptions:
  """Get a GA FlexShieldingOptions message from a specified FlexShieldingRegion.

  Args:
    region: The FlexShieldingRegion to use, e.g. 'me_central1', or empty string.

  Returns:
    A FlexShieldingOptions message, or None if the region is empty.
  """
  return GetFlexShielding('v1', region)


def GetFlexShieldingAlpha(region: str) -> v1alpha1_msgs.FlexShieldingOptions:
  """Get an alpha FlexShieldingOptions from a specified FlexShieldingRegion.

  Args:
    region: The FlexShieldingRegion to use, e.g. 'me_central1', or empty string.

  Returns:
    A FlexShieldingOptions message, or None if the region is empty.
  """
  return GetFlexShielding('v1alpha1', region)
