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
"""Default formatter for Cloud Run Integrations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import io

from googlecloudsdk.command_lib.run.integrations.formatters import base
from googlecloudsdk.core.resource import custom_printer_base as cp
from googlecloudsdk.core.resource import yaml_printer as yp


class DefaultFormatter(base.BaseFormatter):
  """Format logics when no integration specific formatter is matched."""

  def TransformConfig(self, record: base.Record) -> cp._Marker:
    """Print the config of the integration.

    Args:
      record: integration_printer.Record class that just holds data.

    Returns:
      The printed output.
    """
    return cp.Lines([self._PrintAsYaml({'config': record.resource.config})])

  def TransformComponentStatus(self, record: base.Record) -> cp._Marker:
    """Print the component status of the integration.

    Args:
      record: dict, the integration.

    Returns:
      The printed output.
    """
    component_status = record.status.get('resourceComponentStatuses', {})
    components = []
    for r in component_status:
      comp_type = self.PrintType(r.get('type'))
      comp_name = r.get('name')
      console_link = r.get('consoleLink', 'n/a')
      state_name = r.get('state', 'n/a').upper()
      state_symbol = self.StatusSymbolAndColor(state_name)
      components.append(
          cp.Lines([
              '{} ({})'.format(comp_type, comp_name),
              cp.Labeled([
                  ('Console link', console_link),
                  ('Resource Status', state_symbol + ' ' + state_name),
              ]),
          ])
      )
    return cp.Labeled(components)

  def _PrintAsYaml(self, content: any) -> str:
    buffer = io.StringIO()
    printer = yp.YamlPrinter(buffer)
    printer.Print(content)
    return buffer.getvalue()

