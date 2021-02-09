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
"""KubeRun Component printer."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.resource import custom_printer_base as cp

RESOURCE_PRINTER_FORMAT = 'resource'


class ResourcePrinter(cp.CustomPrinterBase):
  """Prints the KubeRun Resource custom human-readable format."""

  def Transform(self, record):
    """Transform a service into the output structure of marker classes."""
    sections = [
        self._Header(record),
        self._Kind(record),
        self._SpecSection(record),
    ]
    return cp.Lines(_Spaced(sections))

  def _Header(self, record):
    con = console_attr.GetConsoleAttr()
    return con.Emphasize('Resource {}'.format(record['metadata']['name']))

  def _Kind(self, record):
    return cp.Section([cp.Labeled([('Kind', record['kind'])])])

  def _SpecSection(self, record):
    return cp.Section(
        [cp.Labeled([('Refs', cp.Lines(record['spec']['refs']))])])


def _Spaced(lines):
  """Adds a line of space between the passed in lines."""
  spaced_lines = []
  for line in lines:
    if spaced_lines:
      spaced_lines.append(' ')
    spaced_lines.append(line)
  return spaced_lines
