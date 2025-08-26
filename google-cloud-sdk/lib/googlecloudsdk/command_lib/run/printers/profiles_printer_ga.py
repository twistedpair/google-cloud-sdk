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
"""Traffic-specific printer and functions for generating traffic formats."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.core.resource import custom_printer_base as cp


PROFILES_PRINTER_FORMAT = 'profile'


def amount_to_decimal(cost):
  """Converts cost to a decimal representation."""
  units = cost.units
  if not units:
    units = 0
  decimal_value = +(units + cost.nanos / 1e9)
  return f'{decimal_value:.3f}'


def get_decimal_cost(costs):
  """Returns the cost per million normalized output tokens as a decimal.

  Args:
    costs: The costs to convert.
  """
  output_token_cost = 'N/A'
  if costs and costs[0].costPerMillionOutputTokens:
    output_token_cost = amount_to_decimal(
        costs[0].costPerMillionOutputTokens
    )
  input_token_cost = 'N/A'
  if costs and costs[0].costPerMillionInputTokens:
    input_token_cost = amount_to_decimal(costs[0].costPerMillionInputTokens)
  return (input_token_cost, output_token_cost)


def _transform_profiles(profiles):
  """Transforms a List[AcceleratorOption] into a table with decimal representation of cost."""

  header = [
      'Instance Type',
      'Accelerator',
      'Cost/M Input Tokens',
      'Cost/M Output Tokens',
      'Output Tokens/s',
      'NTPOT(ms)',
      'TTFT(ms)',
      'Model Server',
      'Model Server Version',
      'Model',
  ]

  rows = [header]
  for p in profiles:
    input_token_cost, output_token_cost = get_decimal_cost(
        p.performanceStats[0].cost if p.performanceStats else None
    )
    row = [
        p.instanceType,
        p.acceleratorType,
        input_token_cost,
        output_token_cost,
        p.performanceStats[0].outputTokensPerSecond
        if p.performanceStats[0]
        else None,
        p.performanceStats[0].ntpotMilliseconds if p.performanceStats else None,
        p.performanceStats[0].ttftMilliseconds if p.performanceStats else None,
        p.modelServerInfo.modelServer,
        p.modelServerInfo.modelServerVersion,
        p.modelServerInfo.model,
    ]
    rows.append(row)

  profiles_table = cp.Table(rows)

  return cp.Section([profiles_table], max_column_width=60)


class ProfilePrinter(cp.CustomPrinterBase):
  """Prints a service's profile in a custom human-readable format."""

  def Print(self, resources, single=True, intermediate=False):
    """Overrides ResourcePrinter.Print to set single=True."""
    super(ProfilePrinter, self).Print(resources, True, intermediate)

  def Transform(self, profiles):
    """Transforms a List[TrafficTargetPair] into a marker class format."""
    return _transform_profiles(profiles)
