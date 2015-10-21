# -*- coding: utf-8 -*-
# Copyright 2014 Google Inc. All Rights Reserved.

"""JSON format resource printer."""


import json

from googlecloudsdk.core.resource import resource_printer_base


class JsonPrinter(resource_printer_base.ResourcePrinter):
  """Prints all records as a JSON list.

  link:www.json.org[JSON], JavaScript Object Notation.

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
