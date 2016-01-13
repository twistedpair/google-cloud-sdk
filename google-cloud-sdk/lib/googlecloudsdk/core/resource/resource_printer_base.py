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

"""Resource printer base class.

Each printer has three main attributes, all accessible as strings in the
--format='NAME[ATTRIBUTES](PROJECTION)' option:

  NAME: str, The printer name.

  [ATTRIBUTES]: str, An optional [no-]name[=value] list of attributes. Unknown
    attributes are silently ignored. Attributes are added to a printer local
    dict indexed by name.

  (PROJECTION): str, List of resource names to be included in the output
    resource. Unknown names are silently ignored. Resource names are
    '.'-separated key identifiers with an implicit top level resource name.

Example:

  gcloud compute instances list \
      --format='table[box](name, networkInterfaces[0].networkIP)'
"""

from googlecloudsdk.core import log
from googlecloudsdk.core.resource import resource_projector


# Structured output indentation.
STRUCTURED_INDENTATION = 2


class ResourcePrinter(object):
  """Base class for printing JSON-serializable Python objects.

  Attributes:
    attributes: Optional printer attribute dict indexed by attribute name.
    _by_columns: True if AddRecord() expects a list of columns.
    column_attributes: Projection ColumnAttributes().
    _empty: True if there are no records.
    _heading: The list of column heading label strings.
    _name: Format name.
    _out: Output stream.
    _process_record: The function called to process each record passed to
      AddRecord() before calling _AddRecord(). It is called like this:
        record = process_record(record)

  Printer attributes:
    empty-legend=_SENTENCES_: Prints _SENTENCES_ to the *status* logger if there
      are no items. The default *empty-legend* is "Listed 0 items.".
      *no-empty-legend* disables the default.
    legend=_SENTENCES_: Prints _SENTENCES_ to the *out* logger after the last
      item if there is at least one item.
    log=_TYPE_: Prints the legend to the _TYPE_ logger instead of the default.
      _TYPE_ may be: *out* (the default), *status* (standard error), *debug*,
      *info*, *warn*, or *error*.
  """

  def __init__(self, out=None, name=None, attributes=None,
               column_attributes=None, by_columns=False, process_record=None):
    """Constructor.

    Args:
      out: The output stream, log.out if None. If the 'private' attribute is set
        and the output stream is a log._ConsoleWriter then the underlying stream
        is used instead to disable output to the log file.
      name: The format name.
      attributes: Optional printer attribute dict indexed by attribute name.
      column_attributes: Projection ColumnAttributes().
      by_columns: True if AddRecord() expects a list of columns.
      process_record: The function called to process each record passed to
        AddRecord() before calling _AddRecord(). It is called like this:
          record = process_record(record)
    """
    self.attributes = attributes or {}
    self._by_columns = by_columns
    self.column_attributes = column_attributes
    self._empty = True
    self._heading = None
    self._name = name
    self._out = out or log.out
    if 'private' in self.attributes:
      try:
        # Disable log file writes by printing directly to the console stream.
        self._out = self._out.GetConsoleWriterStream()
      except AttributeError:
        pass
    self._process_record = (process_record or
                            resource_projector.Compile().Evaluate)

  def AddHeading(self, heading):
    """Overrides the default heading.

    If the printer does not support headings then this is a no-op.

    Args:
      heading: List of column heading strings that overrides the default
        heading.
    """
    self._heading = heading

  def _AddRecord(self, record, delimit=True):
    """Format specific AddRecord().

    Args:
      record: A JSON-serializable object.
      delimit: Prints resource delimiters if True.
    """
    pass

  def AddRecord(self, record, delimit=True):
    """Adds a record for printing.

    Streaming formats (e.g., YAML) can print results at each AddRecord() call.
    Non-streaming formats (e.g., JSON, table(...)) may cache data at each
    AddRecord() call and not print until Finish() is called.

    Args:
      record: A JSON-serializable object.
      delimit: Prints resource delimiters if True.
    """
    self._empty = False
    self._AddRecord(self._process_record(record), delimit)

  def AddLegend(self):
    """Prints the table legend if it was specified.

    The legend is one or more lines of text printed after the table data.
    """
    writers = {
        'out': lambda x: self._out.write(x + '\n'),
        'status': lambda x: log.status.write(x + '\n'),
        'debug': log.debug,
        'info': log.info,
        'warn': log.warn,
        'error': log.error,
        }

    log_type = self.attributes.get('log', None)
    if self._empty:
      if not log_type:
        log_type = 'status'
      legend = self.attributes.get('empty-legend')
      if legend is None and 'no-empty-legend' not in self.attributes:
        legend = 'Listed 0 items.'
    else:
      legend = self.attributes.get('legend')
      if legend and not log_type:
        legend = '\n' + legend
    if legend is not None:
      writer = writers.get(log_type or 'out')
      writer(legend)

  def ByColumns(self):
    """Returns True if AddRecord() expects a list of columns.

    Returns:
      True if AddRecord() expects a list of columns.
    """
    return self._by_columns

  def Finish(self):
    """Prints the results for non-streaming formats."""
    pass

  def PrintSingleRecord(self, record):
    """Print one record by itself.

    Args:
      record: A JSON-serializable object.
    """
    self.AddRecord(record, delimit=False)
    self.Finish()
