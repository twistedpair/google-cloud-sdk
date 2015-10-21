# Copyright 2014 Google Inc. All Rights Reserved.

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
    _attributes: Optional printer attribute dict indexed by attribute name.
    _by_columns: True if AddRecord() expects a list of columns.
    column_attributes: Projection ColumnAttributes().
    _heading: The list of column heading label strings.
    _name: Format name.
    _out: Output stream.
    _process_record: The function called to process each record passed to
      AddRecord() before calling _AddRecord(). It is called like this:
        record = process_record(record)
  """

  def __init__(self, out=None, name=None, attributes=None,
               column_attributes=None, by_columns=False, process_record=None):
    """Constructor.

    Args:
      out: The output stream, log.out if None.
      name: The format name.
      attributes: Optional printer attribute dict indexed by attribute name.
      column_attributes: Projection ColumnAttributes().
      by_columns: True if AddRecord() expects a list of columns.
      process_record: The function called to process each record passed to
        AddRecord() before calling _AddRecord(). It is called like this:
          record = process_record(record)
    """
    self._attributes = attributes or {}
    self._by_columns = by_columns
    self.column_attributes = column_attributes
    self._heading = None
    self._name = name
    self._out = out or log.out
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

  def AddRecord(self, record, delimit=True):
    """Adds a record for printing.

    Streaming formats (e.g., YAML) can print results at each AddRecord() call.
    Non-streaming formats (e.g., JSON, table(...)) may cache data at each
    AddRecord() call and not print until Finish() is called.

    Args:
      record: A JSON-serializable object.
      delimit: Prints resource delimiters if True.
    """
    self._AddRecord(self._process_record(record), delimit)

  def ByColumns(self):
    """Returns True if AddRecord() expects a list of columns.

    Returns:
      True if AddRecord() expects a list of columns.
    """
    return self._by_columns

  def Finish(self):
    """Prints the results for non-streaming formats."""

  def PrintSingleRecord(self, record):
    """Print one record by itself.

    Args:
      record: Prints resource delimiters if True.
    """
    self.AddRecord(record, delimit=False)
    self.Finish()
