# Copyright 2014 Google Inc. All Rights Reserved.
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

"""JSON format resource printer."""

import json
import StringIO

from googlecloudsdk.core.resource import resource_printer_base


class JsonPrinter(resource_printer_base.ResourcePrinter):
  """Prints resource records as a JSON list.

  [JSON](http://www.json.org), JavaScript Object Notation.

  Printer attributes:
    no-undefined: Does not display resource data items with null values.

  Attributes:
    _buffer: Buffer stream for record item indentation.
    _delimiter: Delimiter string before the next record.
    _empty: True if no records were output.
    _indent: Resource item indentation.
  """

  # json.dump() does not have a streaming mode. In order to print a resource`
  # list it requires the complete list contents. To get around that limitation
  # and print each resource list item, _AddRecord() prints the initial "[", the
  # intervening ",", the final "]", captures the json.dump() output for each
  # resource list item and prints it indented by STRUCTURED_INDENTATION spaces.

  _BEGIN_DELIMITER = '[\n'

  def __init__(self, *args, **kwargs):
    super(JsonPrinter, self).__init__(*args, retain_none_values=True, **kwargs)
    self._buffer = StringIO.StringIO()
    self._empty = True
    self._delimiter = self._BEGIN_DELIMITER
    self._indent = ' ' * resource_printer_base.STRUCTURED_INDENTATION

  def __Dump(self, resource, out=None):
    json.dump(
        resource,
        fp=out or self._out,
        indent=resource_printer_base.STRUCTURED_INDENTATION,
        sort_keys=True,
        separators=(',', ': '))

  def _AddRecord(self, record, delimit=True):
    """Prints one element of a JSON-serializable Python object resource list.

    Allows intermingled delimit=True and delimit=False.

    Args:
      record: A JSON-serializable object.
      delimit: Dump one record if False, used by PrintSingleRecord().
    """
    self._empty = False
    if delimit:
      delimiter = self._delimiter + self._indent
      self._delimiter = ',\n'
      self.__Dump(record, self._buffer)
      output = self._buffer.getvalue()
      self._buffer.truncate(0)
      for line in output.split('\n'):
        self._out.write(delimiter + line)
        delimiter = '\n' + self._indent
    else:
      if self._delimiter != self._BEGIN_DELIMITER:
        self._out.write('\n]\n')
        self._delimiter = self._BEGIN_DELIMITER
      self.__Dump(record)
      self._out.write('\n')

  def Finish(self):
    """Prints the final delimiter and preps for the next resource list."""
    if self._empty:
      self._out.write('[]\n')
    elif self._delimiter != self._BEGIN_DELIMITER:
      self._out.write('\n]\n')
      self._delimiter = self._BEGIN_DELIMITER
