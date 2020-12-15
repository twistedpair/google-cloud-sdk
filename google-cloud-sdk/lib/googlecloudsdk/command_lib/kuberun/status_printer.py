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
"""Custom printer for KubeRun Application Status."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.core.resource import custom_printer_base as cp
from googlecloudsdk.core.resource import resource_printer

_PRINTER_FORMAT = 'status'


def _ComponentTable(components):
  rows = [(x.name, x.deployment_state, x.commit_id[:6], x.deployment_time,
           x.url) for x in components]
  return cp.Table([('NAME', 'DEPLOYMENT', 'COMMIT', 'LAST-DEPLOYED', 'URL')] +
                  rows)


def _ModulesTable(modules):
  rows = []
  for m in modules:
    rows.extend([(x.name, m.name, x.deployment_state, x.commit_id[:6],
                  x.deployment_time, x.url) for x in m.components])
  return cp.Table([('NAME', 'MODULE', 'DEPLOYMENT', 'COMMIT', 'LAST-DEPLOYED',
                    'URL')] + rows)


class ApplicationStatusPrinter(cp.CustomPrinterBase):
  """Prints the KubeRun Application Status custom human-readable format."""

  @staticmethod
  def Register(parser):
    """Register this custom printer with the given parser."""
    resource_printer.RegisterFormatter(
        _PRINTER_FORMAT, ApplicationStatusPrinter, hidden=True)
    parser.display_info.AddFormat(_PRINTER_FORMAT)

  def Transform(self, record):
    """Transform a service into the output structure of marker classes."""
    results = [
        cp.Section([cp.Labeled([('Environment', record['environment'])])])
    ]
    status = record['status']
    if len(status.modules) == 1:
      results.append(
          cp.Section([cp.Labeled(
              [
                  ('Components', _ComponentTable(status.modules[0].components))
              ])], max_column_width=25))
    else:
      results.append(
          cp.Section(
              [cp.Labeled([('Components', _ModulesTable(status.modules))])],
              max_column_width=25))
    return cp.Lines(results)
