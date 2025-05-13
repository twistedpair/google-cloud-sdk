# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Instance-split-specific printer and functions for generating instance split formats."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.api_lib.run import instance_split_pair
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.resource import custom_printer_base as cp


INSTANCE_SPLIT_PRINTER_FORMAT = 'instancesplit'
_LATEST_READY_REV_UNSPECIFIED = '-'


def _TransformInstanceSplitPair(pair):
  """Transforms a single InstanceSplitPair into a marker class structure."""
  console = console_attr.GetConsoleAttr()
  return (
      pair.displayPercent,
      console.Emphasize(pair.displayRevisionId),
  )


def _TransformInstanceSplitPairs(instance_split_pairs):
  """Transforms a List[InstanceSplitPair] into a marker class structure."""
  instance_split_section = cp.Section(
      [cp.Table(_TransformInstanceSplitPair(p) for p in instance_split_pairs)]
  )
  return cp.Section(
      [cp.Labeled([('Instance Split', instance_split_section)])],
      max_column_width=60,
  )


def TransformInstanceSplitFields(worker_pool_record):
  """Transforms a worker's instance split fields into a marker class structure to print.

  Generates the custom printing format for a worker's instance split using the
  marker classes defined in custom_printer_base.

  Args:
    worker_pool_record: A WorkerPool object.

  Returns:
    A custom printer marker object describing the instance split fields
    print format.
  """
  no_status = worker_pool_record.status is None
  instance_split_pairs = instance_split_pair.GetInstanceSplitPairs(
      worker_pool_record.spec_split,
      worker_pool_record.status_split,
      (
          _LATEST_READY_REV_UNSPECIFIED
          if no_status
          else worker_pool_record.status.latestReadyRevisionName
      ),
  )
  return _TransformInstanceSplitPairs(instance_split_pairs)


class InstanceSplitPrinter(cp.CustomPrinterBase):
  """Prints a worker pool's instance split in a custom human-readable format."""

  def Print(self, resources, single=False, intermediate=False):
    """Overrides ResourcePrinter.Print to set single=True."""
    # The update-instance-split command returns a List[InstanceSplitPair] as its
    # result. In order to print the custom human-readable format, this printer
    # needs to process all records in the result at once (to compute column
    # widths). By default, ResourcePrinter interprets a List[*] as a list of
    # separate records and passes the contents of the list to this printer
    # one-by-one. Setting single=True forces ResourcePrinter to treat the
    # result as one record and pass the entire list to this printer in one call.
    super(InstanceSplitPrinter, self).Print(resources, True, intermediate)

  def Transform(self, record):
    """Transforms a List[InstanceSplitPair] into a marker class format."""
    return _TransformInstanceSplitPairs(record)
