# Copyright 2014 Google Inc. All Rights Reserved.

"""CSV resource printer."""

import csv

from googlecloudsdk.core.resource import resource_printer_base


class CsvPrinter(resource_printer_base.ResourcePrinter):
  """A printer for printing CSV data.

  link:www.ietf.org/rfc/rfc4180.txt[Comma Separated Values] with no keys.
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
      if 'no-heading' not in self._attributes:
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

  CSV with no heading and <TAB> delimiter instead of <COMMA>. Used to retrieve
  individual resource values. This format requires a projection to define the
  value(s) to be printed.
  """

  def __init__(self, *args, **kwargs):
    super(ValuePrinter, self).__init__(*args, **kwargs)
    self._heading_printed = True
    self._add_csv_row = csv.writer(self._out, dialect='excel',
                                   delimiter='\t', lineterminator='\n').writerow
