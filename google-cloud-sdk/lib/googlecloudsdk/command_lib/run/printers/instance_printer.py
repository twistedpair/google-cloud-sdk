# third_party/py/googlecloudsdk/command_lib/run/printers/instance_printer.py
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
"""Instance-specific printer."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.api_lib.run import instance
from googlecloudsdk.command_lib.run.printers import container_and_volume_printer_util as container_util
from googlecloudsdk.command_lib.run.printers import k8s_object_printer_util as k8s_util
from googlecloudsdk.core.resource import custom_printer_base as cp


def status_color_format():
  """Return the color format string for the status of this instance."""
  color_formatters = []
  for _, symbol in instance.Instance.INSTANCE_SYMBOLS.items():
    if symbol.color:
      color_formatters.append(f'{symbol.color}="[{symbol.best}{symbol.alt}]"')
  color_formatters_str = ','.join(color_formatters)
  return f'ready_symbol.color({color_formatters_str}):label=""'


INSTANCE_PRINTER_FORMAT = 'instance'


# TODO: b/456195460 - Add more fields to the instance printer.
class InstancePrinter(cp.CustomPrinterBase):
  """Prints the run Instance in a custom human-readable format.

  Format specific to Cloud Run instances. Only available on Cloud Run commands
  that print instances.
  """

  @staticmethod
  def _formatOutput(record):
    output = []
    header = k8s_util.BuildHeader(record)
    labels = k8s_util.GetLabels(record.labels)
    ready_message = k8s_util.FormatReadyMessage(record)
    if header:
      output.append(header)
    output.append(' ')
    if labels:
      output.append(labels)
      output.append(' ')
    if ready_message:
      output.append(ready_message)
    output.append(container_util.GetContainers(record))

    return output

  def Transform(self, record):
    """Transform a instance into the output structure of marker classes."""
    return cp.Lines(InstancePrinter._formatOutput(record))
