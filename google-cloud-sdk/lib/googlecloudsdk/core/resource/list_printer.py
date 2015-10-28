# Copyright 2015 Google Inc. All Rights Reserved.

"""list format resource printer."""

from googlecloudsdk.core.resource import resource_printer_base


class ListPrinter(resource_printer_base.ResourcePrinter):
  """Prints the list representations of a JSON-serializable list.

  An ordered list of items.

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

  def __init__(self, *args, **kwargs):
    super(ListPrinter, self).__init__(*args, **kwargs)
    # Print the title if specified.
    if 'title' in self.attributes:
      self._out.write(self.attributes['title'] + '\n')

  def _AddRecord(self, record, delimit=False):
    """Immediately prints the given record as a list item.

    Args:
      record: A JSON-serializable object.
      delimit: Prints resource delimiters if True.
    """
    if isinstance(record, dict):
      record = ['{0}: {1}'.format(k, v) for k, v in sorted(record.iteritems())]
    elif not isinstance(record, list):
      record = [record]
    self._out.write(' - ' + '\n   '.join(record) + '\n')

  def Finish(self):
    """Prints the legend if any."""
    self.AddLegend()
