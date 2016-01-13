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

from googlecloudsdk.core.resource import resource_printer_base


class JsonPrinter(resource_printer_base.ResourcePrinter):
  """Prints all records as a JSON list.

  [JSON](http://www.json.org), JavaScript Object Notation.

  Attributes:
    _records: The list of all resource records.
  """

  def __init__(self, *args, **kwargs):
    super(JsonPrinter, self).__init__(*args, **kwargs)
    self._records = []

  def __Dump(self, resource):
    json.dump(
        resource,
        fp=self._out,
        indent=resource_printer_base.STRUCTURED_INDENTATION,
        sort_keys=True,
        separators=(',', ': '))
    self._out.write('\n')

  def _AddRecord(self, record, delimit=True):
    """Adds a JSON-serializable Python object to the resource list.

    The logic allows intermingled delimit=True and delimit=False.

    Args:
      record: A JSON-serializable object.
      delimit: Dump one record if False, used by PrintSingleRecord().
    """
    if delimit:
      if self._records is None:
        self._records = []
      self._records.append(record)
    else:
      if self._records:
        self.__Dump(self._records)
      self._records = None
      self.__Dump(record)

  def Finish(self):
    """Prints the record list to the output stream."""
    if self._records is not None:
      self.__Dump(self._records)
      self._records = None
