# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""V2 WorkerPool instance split specific printer."""

from typing import List

from googlecloudsdk.command_lib.run.v2 import instance_split
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.resource import custom_printer_base as cp
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import worker_pool as worker_pool_objects

INSTANCE_SPLIT_PRINTER_FORMAT = 'instancesplit'


def TransformWorkerPoolInstanceSplit(
    record: worker_pool_objects.WorkerPool,
) -> cp.Section:
  """Transforms a worker pool into the output structure of instance split marker classes."""
  instance_split_pairs = instance_split.GetInstanceSplitPairs(record)
  split_section = _TransformInstanceSplitPairs(instance_split_pairs)
  return cp.Section(
      [cp.Labeled([('Instance Split', split_section)])], max_column_width=60
  )


def _TransformInstanceSplitPair(
    pair: instance_split.InstanceSplitPair,
):
  """Transforms a single InstanceSplitPair into a marker class structure."""
  console = console_attr.GetConsoleAttr()
  return (pair.display_percent, console.Emphasize(pair.display_revision_id))


def _TransformInstanceSplitPairs(
    pairs: List[instance_split.InstanceSplitPair],
) -> cp.Section:
  """Transforms a list of InstanceSplitPairs into a marker class structure."""
  return cp.Section([cp.Table(_TransformInstanceSplitPair(p) for p in pairs)])


class InstanceSplitPrinter(cp.CustomPrinterBase):
  """Prints the Run v2 WorkerPool instance split in a custom human-readable format."""

  def Print(self, resources, intermediate=False):
    """Overrides ResourcePrinter.Print to set single=True."""
    # The update-instance-split command returns a List[InstanceSplitPair] as its
    # result. In order to print the custom human-readable format, this printer
    # needs to process all records in the result at once (to compute column
    # widths). By default, ResourcePrinter interprets a List[*] as a list of
    # separate records and passes the contents of the list to this printer
    # one-by-one. Setting single=True forces ResourcePrinter to treat the
    # result as one record and pass the entire list to this printer in one call.
    super(InstanceSplitPrinter, self).Print(
        resources, single=True, intermediate=intermediate
    )

  def Transform(self, record: List[instance_split.InstanceSplitPair]):
    """Transform instance split pairs into the output structure of instance split marker classes."""
    split_section = _TransformInstanceSplitPairs(record)
    return cp.Section(
        [cp.Labeled([('Instance Split', split_section)])], max_column_width=60
    )
