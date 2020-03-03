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
"""Traffic-specific printer and functions for generating traffic formats."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.api_lib.run import traffic_pair
from googlecloudsdk.core.resource import custom_printer_base as cp


def _TransformTrafficPairs(traffic_pairs):
  """Transforms a List[TrafficTargetPair] into a marker class structure."""
  return cp.Labeled([
      ('Traffic',
       cp.Mapped(
           (p.displayPercent, p.displayRevisionId) for p in traffic_pairs))
  ])


def TransformTraffic(service):
  """Transforms a service's traffic into a marker class structure to print.

  Generates the custom printing format for a service's traffic using the marker
  classes defined in custom_printer_base.

  Args:
    service: A Service object.

  Returns:
    A custom printer marker object describing the traffic print format.
  """
  traffic_pairs = traffic_pair.GetTrafficTargetPairs(
      service.spec_traffic, service.status_traffic, service.is_managed,
      service.status.latestReadyRevisionName)
  return _TransformTrafficPairs(traffic_pairs)


# TODO(b/148901171) Add a traffic-specific custom printer.
