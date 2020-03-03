# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Base class for resource-specific printers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import abc

from googlecloudsdk.core.resource import resource_printer_base

import six


class _Marker(object):
  pass


class Table(list, _Marker):
  """Marker class for a table."""
  skip_empty = False
  separator = ''


class Labeled(Table):
  """Marker class for a list of "Label: value" 2-tuples."""
  skip_empty = True
  separator = ':'


# This class exists for API compatibility.
class Mapped(Table):
  """Marker class for a list of key-value 2-tuples."""


class Lines(list, _Marker):
  """Marker class for a list of lines in a section."""


def _FollowedByEmpty(row, index):
  """Returns true if all columns after the given index are empty."""
  return not any(row[index + 1:])


def _IsLastColumnInRow(row, column_index, last_index, skip_empty):
  """Returns true if column_index is considered the last column in the row."""
  # A column is considered the last column in the row if it is:
  #   1) The last column in the row.
  #   2) Only followed by empty columns and skip_empty is true.
  #   3) Followed by a _Marker.
  #        - This is because _Marker's must be in the last column in their row
  #          and get printed on a new line).
  return (column_index == last_index or
          (skip_empty and _FollowedByEmpty(row, column_index)) or
          isinstance(row[column_index + 1], _Marker))


class ColumnWidths(object):
  """Computes and stores column widths for a table and any nested tables.

  A nested table is a table defined in the last column of a row in another
  table. ColumnWidths calculates the column widths for nested tables separately
  from the parent table. When merging ColumnWidths, the class merges nested
  tables at the same level of nesting.

  Attributes:
    widths: A list containing the computed minimum width of each column in the
      table.
    subtable: A ColumnWidths instance describing the column widths for all
      nested tables or None if there are no nested tables.
  """

  def __init__(self,
               row=None,
               separator='',
               skip_empty=False,
               max_column_width=None):
    """Computes the width of each column in row and in any nested tables.

    Args:
      row: An optional list containing the columns in a table row. Any marker
        classes nested within the row must be in the last column of the row.
      separator: An optional separator string to place between columns.
      skip_empty: A boolean indicating whether columns followed only by empty
        columns should be skipped.
      max_column_width: An optional maximum column width.

    Returns:
      A ColumnWidths object containing the computed column widths.
    """
    self._widths = []
    self._subtable = None
    self._max_column_width = max_column_width
    if row:
      for i in range(len(row)):
        self._ProcessColumn(i, row, len(separator), skip_empty)

  @property
  def widths(self):
    """A list containing the minimum width of each column."""
    return self._widths

  @property
  def subtable(self):
    """A ColumnWidths object for nested tables or None if no nested tables."""
    return self._subtable

  def __repr__(self):
    """Returns a string representation of a ColumnWidths object."""
    return '<widths: {}, subtable: {}>'.format(self.widths, self.subtable)

  def _SetWidth(self, column_index, content_length):
    """Adjusts widths to account for the length of new column content.

    Args:
      column_index: The column index to potentially update. Must be between 0
        and len(widths).
      content_length: The column content's length to consider when updating
        widths.
    """
    # Updates the width at position column_index to be the max of the existing
    # value and the new content's length, or this instance's max_column_width if
    # the value would be greater than max_column_width.
    if column_index == len(self._widths):
      self._widths.append(0)

    new_width = max(self._widths[column_index], content_length)
    if self._max_column_width is not None:
      new_width = min(self._max_column_width, new_width)
    self._widths[column_index] = new_width

  def _ProcessColumn(self, index, row, separator_width, skip_empty):
    """Processes a single column value when computing column widths."""
    record = row[index]
    last_index = len(row) - 1
    if isinstance(record, _Marker):
      if index == last_index:
        # TODO(b/148901171) Compute column widths of nested tables.
        return
      else:
        raise TypeError('Markers can only be used in the last column.')

    if _IsLastColumnInRow(row, index, last_index, skip_empty):
      self._SetWidth(index, 0)
    else:
      self._SetWidth(index, len(record) + separator_width)


@six.add_metaclass(abc.ABCMeta)
class CustomPrinterBase(resource_printer_base.ResourcePrinter):
  """Base to extend to custom-format a resource.

  Instead of using a format string, uses the "Transform" method to build a
  structure of marker classes that represent out to print out the resource
  in a structured way, and then prints it out in that way.

  A string prints out as a string; the marker classes above print out as an
  indented aligned table.
  """

  MAX_MAP_WIDTH = 20

  def __init__(self, *args, **kwargs):
    kwargs['process_record'] = self.Transform
    super(CustomPrinterBase, self).__init__(*args, **kwargs)

  def _AddRecord(self, record, delimit=True):
    column_div = self._CalculateColumn(record)
    self._PrintHelper(record, 0, column_div)
    if delimit:
      self._out.write('------\n')

  def _CalculateColumn(self, record):
    """Return the position of the tabstop between labels or keys and values."""
    if not record:
      return 0
    if isinstance(record, Table):
      add_width = len(record.separator)
      if record.skip_empty:
        if not any(v for _, v in record):
          return 0
      ret = max(len(k) for k, v in record if v) + add_width
      ret = max(ret, 2 + max(self._CalculateColumn(v) for _, v in record))
      return min(ret, self.MAX_MAP_WIDTH)
    elif isinstance(record, Lines):
      return max(self._CalculateColumn(l) for l in record)
    else:
      return 0

  def _PrintHelper(self, subrecord, indent_level, column_div):
    """Helper function for recursively indentedly printing."""
    linefmt = '{indent: <%d}{line}\n' % indent_level
    mapfmt = '{indent: <%d}{k: <%d} {v}' % (indent_level, column_div)
    if not subrecord:
      return
    elif isinstance(subrecord, Table):
      sep = subrecord.separator
      for k, v in subrecord:
        if not v and subrecord.skip_empty:
          continue
        if isinstance(v, _Marker):
          self._out.write(
              mapfmt.format(indent='', k=k+sep, v='').rstrip() + '\n')
          self._PrintHelper(v, indent_level+2, column_div-2)
        else:
          self._out.write(
              mapfmt.format(indent='', k=k+sep, v=v).rstrip() + '\n')
    elif isinstance(subrecord, Lines):
      for r in subrecord:
        self._PrintHelper(r, indent_level, column_div)
    elif isinstance(subrecord, _Marker):
      raise ValueError('Unrecognized marker class')
    else:
      self._out.write(linefmt.format(indent='', line=subrecord))

  @abc.abstractmethod
  def Transform(self, record):
    """Override to describe the format of the record.

    Takes in the raw record, returns a structure of "marker classes" (above in
    this file) that will describe how to print it.

    Args:
      record: The record to transform
    Return:
      A structure of "marker classes" that describes how to print the record.
    """
    pass
