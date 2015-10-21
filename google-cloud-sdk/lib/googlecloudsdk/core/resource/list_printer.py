# Copyright 2015 Google Inc. All Rights Reserved.

"""list format resource printer."""

from googlecloudsdk.core.resource import resource_printer_base


class ListPrinter(resource_printer_base.ResourcePrinter):
  """Prints the list representations of a JSON-serializable list.

  An ordered list of items.

  Printer attributes:
    title=_TITLE_: Prints a left-justified _TITLE_ before the list data.
  """

  def __init__(self, *args, **kwargs):
    super(ListPrinter, self).__init__(*args, **kwargs)
    # Print the title if specified.
    if 'title' in self._attributes:
      self._out.write(self._attributes['title'] + '\n')

  def _AddRecord(self, record, delimit=False):
    """Immediately prints the given record as a list item.

    Args:
      record: A JSON-serializable object.
      delimit: Prints resource delimiters if True.
    """
    self._out.write(' - ' + str(record) + '\n')
