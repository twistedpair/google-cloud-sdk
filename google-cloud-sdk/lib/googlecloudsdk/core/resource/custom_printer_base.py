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


class _TwoCol(list, _Marker):
  pass


class Labeled(_TwoCol):
  """Marker class for a list of "Label: value" 2-tuples."""
  skip_empty = True
  separator = ':'


class Mapped(_TwoCol):
  """Marker class for a list of key-value 2-tuples."""
  skip_empty = False
  separator = ''


class Lines(list, _Marker):
  """Marker class for a list of lines in a section."""
  pass


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
    if isinstance(record, _TwoCol):
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
    elif isinstance(subrecord, _TwoCol):
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
