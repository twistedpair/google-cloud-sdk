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
"""Custom printer for gsutil-style JSON."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json

from googlecloudsdk.core.resource import resource_printer
from googlecloudsdk.core.resource import resource_printer_base

_PRINTER_FORMAT = 'gsutiljson'


class GsutilJsonPrinter(resource_printer_base.ResourcePrinter):
  """Prints resource records as single line JSON string, just like gsutil.

  To use this resource printer, first call this class's Register() method in a
  target command's Args() method to add it to the available formatters. Then,
  use `gsutiljson[empty="Message"]` rather than the usual `json` formatter to
  mimic gsutil JSON output.

  Printer attributes:
    empty: Returns this value if the resource is empty. Defaults to printing ''.

  Attributes:
    _empty: True if no records were output.
    _delimiter: Delimiter string before the next record.
  """

  _BEGIN_DELIMITER = '['
  _END_DELIMITER = ']'

  def __init__(self, *args, **kwargs):
    super(GsutilJsonPrinter, self).__init__(
        *args, retain_none_values=True, **kwargs
    )
    self._empty = True
    self._delimiter = self._BEGIN_DELIMITER

  @staticmethod
  def Register():
    """Register this as a custom resource printer."""
    resource_printer.RegisterFormatter(
        _PRINTER_FORMAT, GsutilJsonPrinter, hidden=True
    )

  def _AddRecord(self, record, delimit=True):
    """Prints one element of a JSON-serializable Python object resource list.

    Allows intermingled delimit=True and delimit=False.

    Args:
      record: A JSON-serializable object.
      delimit: Dump one record if False, used by PrintSingleRecord().
    """
    self._empty = False
    output = json.dumps(record, sort_keys=True)
    if delimit:
      self._out.write(self._delimiter + output)
      self._delimiter = ','
    else:
      if self._delimiter != self._BEGIN_DELIMITER:
        self._out.write(self._END_DELIMITER)
        self._delimiter = self._BEGIN_DELIMITER
      self._out.write(output)

  def Finish(self):
    if self._empty:
      if 'empty' in self.attributes:
        self._out.write(self.attributes.get('empty'))
    elif self._delimiter != self._BEGIN_DELIMITER:
      self._out.write(self._END_DELIMITER)
      self._delimiter = self._BEGIN_DELIMITER
    self._out.write('\n')
    super(GsutilJsonPrinter, self).Finish()
