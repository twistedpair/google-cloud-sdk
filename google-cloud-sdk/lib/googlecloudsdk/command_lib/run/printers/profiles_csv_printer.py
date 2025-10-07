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
"""Profiles-specific printer and functions for generating CSV formats."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import csv
import sys

from googlecloudsdk.core.resource import custom_printer_base as cp


PROFILES_PRINTER_FORMAT = "csvprofile"


def amount_to_decimal(cost):
  """Converts cost to a decimal representation."""
  units = cost.units
  if not units:
    units = 0
  decimal_value = +(units + cost.nanos / 1e9)
  return f"{decimal_value:.3f}"


def get_decimal_cost(costs):
  """Returns the cost per million normalized output tokens as a decimal.

  Args:
    costs: The costs to convert.
  """
  output_token_cost = "N/A"
  if costs and costs[0].costPerMillionOutputTokens:
    output_token_cost = amount_to_decimal(
        costs[0].costPerMillionOutputTokens
    )
  input_token_cost = "N/A"
  if costs and costs[0].costPerMillionInputTokens:
    input_token_cost = amount_to_decimal(costs[0].costPerMillionInputTokens)
  return (input_token_cost, output_token_cost)


def _transform_profiles(profiles):
  """Transforms profiles to a CSV format, including cost conversions."""
  csv_data = []
  header = [
      "Instance Type",
      "Accelerator Type",
      "Model Name",
      "Model Server Name",
      "Model Server Version",
      "Output Tokens/s",
      "NTPOT (ms)",
      "TTFT (ms)",
      "QPS",
      "Cost/M Input Tokens",
      "Cost/M Output Tokens",
  ]
  csv_data.append(header)
  for profile in profiles:
    if profile.performanceStats:
      for stats in profile.performanceStats:
        input_token_cost, output_token_cost = get_decimal_cost(
            stats.cost
        )
        row = [
            profile.instanceType,
            profile.acceleratorType,
            profile.modelServerInfo.model,
            profile.modelServerInfo.modelServer,
            profile.modelServerInfo.modelServerVersion,
            stats.outputTokensPerSecond,
            stats.ntpotMilliseconds,
            stats.ttftMilliseconds,
            stats.queriesPerSecond,
            input_token_cost,
            output_token_cost,
        ]
        csv_data.append(row)
  return csv_data


class ProfileCSVPrinter(cp.CustomPrinterBase):
  """Prints a service's profile in a custom human-readable format."""

  def Transform(self, profiles):
    """Transforms a List[TrafficTargetPair] into a CSV format."""
    return _transform_profiles(profiles)

  def Print(self, resources, single=True, intermediate=False):
    """Overrides ResourcePrinter.Print to set single=True."""
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerows(self.Transform(resources))
