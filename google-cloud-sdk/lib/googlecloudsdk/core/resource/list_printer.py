# Copyright 2015 Google Inc. All Rights Reserved.
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

"""list format resource printer."""

from googlecloudsdk.core.resource import resource_printer_base


class ListPrinter(resource_printer_base.ResourcePrinter):
  """Prints the list representations of a JSON-serializable list.

  An ordered list of items.

  Printer attributes:
    compact: Display all items in a record on one line.
  """

  def __init__(self, *args, **kwargs):
    super(ListPrinter, self).__init__(*args, by_columns=True, **kwargs)
    self._process_record_orig = self._process_record
    self._process_record = self._ProcessRecord
    self._separator = u' ' if 'compact' in self.attributes else u'\n   '
    # Print the title if specified.
    if 'title' in self.attributes:
      self._out.write(self.attributes['title'] + '\n')

  def _ProcessRecord(self, record):
    """Applies the original process_record on dict and list records.

    Args:
      record: A JSON-serializable object.

    Returns:
      The processed record.
    """
    if isinstance(record, (dict, list)):
      record = self._process_record_orig(record)
    if isinstance(record, dict):
      record = [u'{0}: {1}'.format(k, v) for k, v in sorted(record.iteritems())
                if v is not None]
    elif not isinstance(record, list):
      record = [unicode(record or '')]
    return [i for i in record if i is not None]

  def _AddRecord(self, record, delimit=False):
    """Immediately prints the given record as a list item.

    Args:
      record: A JSON-serializable object.
      delimit: Prints resource delimiters if True.
    """
    self._out.write(u' - ' + self._separator.join(record) + u'\n')

  # TODO(b/27967563): remove 3Q2016
  def Finish(self):
    """Prints the legend if any."""
    self.AddLegend()
