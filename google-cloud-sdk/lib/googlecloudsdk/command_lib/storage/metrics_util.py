# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Used to collect anonymous transfer-related metrics."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.storage.tasks import task_util
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files


SEQUENTIAL = 'Sequential'
PARALLEL = 'Parallel'
UNSET = None


def _record_storage_event(metric, value=0):
  """Common code for processing an event.

  Args:
    metric (str): The metric being recorded.
    value (mixed): The value being recorded.
  """
  command_name = properties.VALUES.metrics.command_name.Get()
  metrics.CustomKeyValue(command_name, 'Storage-' + metric, value)


def report(source_scheme=UNSET, destination_scheme=UNSET, num_files=UNSET,
           size=UNSET, avg_speed=UNSET, disk_io_time=UNSET):
  """Reports metrics for a transfer.

  Args:
    source_scheme (str|UNSET): The source scheme, i.e. 'gs' or 's3'.
    destination_scheme (str|UNSET): The destination scheme i.e. 'gs' or 's3'.
    num_files (int|UNSET): The number of files transferred.
    size (int|UNSET): The size of the files transferred, in bytes.
    avg_speed (int|UNSET): The average throughput of a transfer in bytes/sec.
    disk_io_time (int|UNSET): The time spent on disk of a transfer in ms.
  """
  use_parallelism = task_util.should_use_parallelism()
  _record_storage_event('ParallelismStrategy',
                        PARALLEL if use_parallelism else SEQUENTIAL)
  _record_storage_event('SourceScheme', source_scheme)
  _record_storage_event('DestinationScheme', destination_scheme)
  _record_storage_event('NumberOfFiles', num_files)
  _record_storage_event('SizeOfFilesBytes', size)
  _record_storage_event('AverageSpeedBytesPerSec', avg_speed)
  _record_storage_event('DiskIoTimeMs', disk_io_time)


def _get_partitions():
  """Retrieves a list of disk partitions.

  Returns:
    An array of partition names as strings.
  """
  partitions = []

  with files.FileReader('/proc/partitions') as f:
    lines = f.readlines()[2:]
    for line in lines:
      _, _, _, name = line.split()
      if name[-1].isdigit():
        partitions.append(name)
  return partitions


def get_disk_counters():
  """Retrieves disk I/O statistics for all disks.

  Adapted from the psutil module's psutil._pslinux.disk_io_counters:
    http://code.google.com/p/psutil/source/browse/trunk/psutil/_pslinux.py

  Originally distributed under under a BSD license.
  Original Copyright (c) 2009, Jay Loden, Dave Daeschler, Giampaolo Rodola.

  Returns:
    A dictionary containing disk names mapped to the disk counters from
    /disk/diskstats.
  """
  # iostat documentation states that sectors are equivalent with blocks and
  # have a size of 512 bytes since 2.4 kernels. This value is needed to
  # calculate the amount of disk I/O in bytes.
  sector_size = 512

  partitions = _get_partitions()

  retdict = {}
  with files.FileReader('/proc/diskstats') as f:
    lines = f.readlines()
    for line in lines:
      values = line.split()[:11]
      _, _, name, reads, _, rbytes, rtime, writes, _, wbytes, wtime = values
      if name in partitions:
        rbytes = int(rbytes) * sector_size
        wbytes = int(wbytes) * sector_size
        reads = int(reads)
        writes = int(writes)
        rtime = int(rtime)
        wtime = int(wtime)
        retdict[name] = (reads, writes, rbytes, wbytes, rtime, wtime)
  return retdict
