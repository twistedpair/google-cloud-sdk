# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Fallback formatter for Cloud Run Integrations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import io

from googlecloudsdk.command_lib.run.integrations.formatters import base_formatter
from googlecloudsdk.core.resource import custom_printer_base as cp
from googlecloudsdk.core.resource import yaml_printer as yp


class FallbackFormatter(base_formatter.BaseFormatter):
  """Format logics when no integration specific formatter is matched."""

  def TransformConfig(self, record):
    """Print the config of the integration.

    Args:
      record: dict, the integration.

    Returns:
      The printed output.
    """
    return self._PrintAsYaml(record['config'])

  def TransformComponentStatus(self, record):
    """Print the component status of the integration.

    Args:
      record: dict, the integration.

    Returns:
      The printed output.
    """
    component_status = record.get('status', {}).get('resourceComponentStatuses',
                                                    {})
    components = []
    for r in component_status:
      components.append((self.PrintType(r.get('type')), '{} {}'.format(
          self.StatusSymbolAndColor(r.get('state')), r.get('name'))))
    return cp.Labeled(components)

  def _PrintAsYaml(self, record):
    buffer = io.StringIO()
    printer = yp.YamlPrinter(buffer)
    printer.Print(record)
    return buffer.getvalue()

