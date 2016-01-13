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

"""CSV resource printer."""

import csv

from googlecloudsdk.core.resource import resource_printer_base


class CsvPrinter(resource_printer_base.ResourcePrinter):
  """A printer for printing CSV data.

  [Comma Separated Values](http://www.ietf.org/rfc/rfc4180.txt) with no keys.
  This format requires a projection to define the values to be printed.

  Printer attributes:
    no-heading: Disables the initial key name heading record.
  """

  def __init__(self, *args, **kwargs):
    super(CsvPrinter, self).__init__(*args, by_columns=True, **kwargs)
    self._heading_printed = False
    self._add_csv_row = csv.writer(self._out, dialect='excel',
                                   delimiter=',', lineterminator='\n').writerow

  def _AddRecord(self, record, delimit=False):
    """Prints the current record as CSV.

    Printer attributes:
      noheading: bool, Disable the initial key name heading record.

    Args:
      record: A list of JSON-serializable object columns.
      delimit: bool, Print resource delimiters -- ignored.

    Raises:
      ToolException: A data value has a type error.
    """
    # The CSV heading has three states:
    #   1: No heading, used by ValuePrinter and CSV when 2. and 3. are empty.
    #   2: Heading via AddHeading().
    #   3: Default heading from format labels, if specified.
    if not self._heading_printed:
      self._heading_printed = True
      if 'no-heading' not in self.attributes:
        if self._heading:
          labels = self._heading
        else:
          labels = self.column_attributes.Labels()
          if labels:
            labels = [x.lower() for x in labels]
        if labels:
          self._add_csv_row(labels)
    line = []
    for col in record:
      if isinstance(col, dict):
        val = ';'.join([str(k) + '=' + str(v)
                        for k, v in sorted(col.iteritems())])
      elif isinstance(col, list):
        val = ';'.join([str(x) for x in col])
      else:
        val = str(col)
      line.append(val)
    self._add_csv_row(line)


class ValuePrinter(CsvPrinter):
  """A printer for printing value data.

  CSV with no heading and <TAB> delimiter instead of <COMMA>, and a legend. Used
  to retrieve individual resource values. This format requires a projection to
  define the value(s) to be printed.

  Printer attributes:
    empty-legend=_SENTENCES_: Prints _SENTENCES_ to the *status* logger if there
      are no items. The default *empty-legend* is "Listed 0 items.".
      *no-empty-legend* disables the default.
    legend=_SENTENCES_: Prints _SENTENCES_ to the *out* logger after the last
      item if there is at least one item.
    log=_TYPE_: Prints the legend to the _TYPE_ logger instead of the default.
      _TYPE_ may be: *out* (the default), *status* (standard error), *debug*,
      *info*, *warn*, or *error*.
    no-quote: Prints NEWLINE terminated TAB delimited values with no quoting.
  """

  def _WriteRow(self, row):
    self._out.write('\t'.join(row) + '\n')

  def __init__(self, *args, **kwargs):
    super(ValuePrinter, self).__init__(*args, **kwargs)
    self._heading_printed = True
    if self.attributes.get('no-quote', 0):
      self._add_csv_row = self._WriteRow
    else:
      self._add_csv_row = csv.writer(
          self._out, dialect='excel', delimiter='\t',
          lineterminator='\n').writerow

  def Finish(self):
    """Prints the legend if any."""
    self.AddLegend()
