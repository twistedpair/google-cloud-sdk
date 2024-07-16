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
"""Utilities for fetching system information."""

from __future__ import annotations
import abc
from collections.abc import Sequence
import ctypes
import dataclasses
import io
import os
import re
from typing import Callable
from typing import Tuple
from googlecloudsdk.command_lib.storage import metrics_util
from googlecloudsdk.command_lib.storage.diagnose import diagnostic
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms
from googlecloudsdk.core.util import scaled_integer

_CPU_COUNT_METRIC_NAME = 'CPU Count'
_CPU_COUNT_METRIC_DESCRIPTION = 'Number of logical CPUs in the system'
_CPU_LOAD_AVG_METRIC_NAME = 'CPU Load Avg'
_CPU_LOAD_AVG_METRIC_DESCRIPTION = 'Average CPU load during last 1-minute'
_FREE_MEMORY_METRIC_NAME = 'Free Memory'
_FREE_MEMORY_METRIC_DESCRIPTION = 'Free memory in the system'
_TOTAL_MEMORY_METRIC_NAME = 'Total Memory'
_TOTAL_MEMORY_METRIC_DESCRIPTION = 'Total memory in the system'
_DIAGNOSTIC_NAME = 'System Info'


@dataclasses.dataclass
class DiskIOStats:
  """I/O statistics for a disk.

  Attributes:
    name: The name of the disk.
    average_transfer_size: The average size of each transfer in bytes.
    transfer_count: The total number of transfers since boot.
    total_transfer_size: The total size of the transfers in bytes since boot.
  """

  name: str
  average_transfer_size: float | None
  transfer_count: float | None
  total_transfer_size: float | None


class SystemInfoProvider(abc.ABC):
  """Base system information provider.

  This class contains OS agnostic implemenations. Child classes may implement
  methods which are OS dependent.
  """

  def get_cpu_count(self) -> int:
    """Returns the number of logical CPUs in the system.

    Logical CPU is the number of threads that the OS can schedule work on.
    Includes physical cores and hyper-threaded cores.
    """
    return os.cpu_count()

  @abc.abstractmethod
  def get_cpu_load_avg(self) -> float:
    """Returns the average CPU load during last 1-minute."""
    pass

  @abc.abstractmethod
  def get_memory_stats(self) -> Tuple[int, int]:
    """Fetches the physical memory stats for the system in bytes.

    Returns:
      A tuple containing total memory and free memory in the system
      respectively.
    """
    pass

  @abc.abstractmethod
  def get_disk_io_stats(self) -> Sequence[DiskIOStats]:
    """Retrieves disk I/O statistics for all the disks in the system."""
    raise NotImplementedError()


class UnixSystemInfoProvider(SystemInfoProvider):
  """System information provider for *nix based systems."""

  def get_cpu_load_avg(self) -> float:
    """Returns the average CPU load during last 1-minute."""
    return os.getloadavg()[0]

  def get_memory_stats(self) -> Tuple[int, int]:
    """Fetches the physical memory stats for the system in bytes.

    Returns:
      A tuple containing total memory and free memory in the system
      respectively.
    """
    mem_total = None
    mem_free = None
    mem_buffers = None
    mem_cached = None

    mem_total_regex = re.compile(r'^MemTotal:\s*(\d*)\s*kB')
    mem_free_regex = re.compile(r'^MemFree:\s*(\d*)\s*kB')
    mem_buffers_regex = re.compile(r'^Buffers:\s*(\d*)\s*kB')
    mem_cached_regex = re.compile(r'^Cached:\s*(\d*)\s*kB')

    with files.FileReader('/proc/meminfo') as f:
      for line in f:
        if m := mem_total_regex.match(line):
          mem_total = int(m.group(1)) * 1000
        elif m := mem_free_regex.match(line):
          mem_free = int(m.group(1)) * 1000
        elif m := mem_buffers_regex.match(line):
          mem_buffers = int(m.group(1)) * 1000
        elif m := mem_cached_regex.match(line):
          mem_cached = int(m.group(1)) * 1000

    # Free memory is really MemFree + Buffers(temporary storage for raw disk
    # blocks) + Cached(in-memory cache for files read from the disk).
    # https://www.kernel.org/doc/Documentation/filesystems/proc.txt
    return (mem_total, mem_free + mem_buffers + mem_cached)

  def get_disk_io_stats(self) -> Sequence[DiskIOStats]:
    """Retrieves disk I/O statistics for all the disks in the system."""
    raw_metrics = metrics_util.get_disk_counters()
    disk_io_stats = []
    if not raw_metrics:
      return []
    for disk_name, counters in raw_metrics.items():
      reads, writes, rbytes, wbytes, _, _ = counters
      transfer_count = reads + writes
      total_transfer_size = rbytes + wbytes

      if transfer_count == 0:
        average_transfer_size = None
      else:
        average_transfer_size = total_transfer_size / transfer_count

      disk_io_stats.append(
          DiskIOStats(
              name=disk_name,
              average_transfer_size=average_transfer_size,
              transfer_count=transfer_count,
              total_transfer_size=total_transfer_size,
          )
      )
    return disk_io_stats


class MemoryStatusEX(ctypes.Structure):
  """Windows MemoryStatusEX structure.

  https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/ns-sysinfoapi-memorystatusex
  """

  _fields_ = [
      ('dwLength', ctypes.c_ulong),
      ('dwMemoryLoad', ctypes.c_ulong),
      ('ullTotalPhys', ctypes.c_ulonglong),
      ('ullAvailPhys', ctypes.c_ulonglong),
      ('ullTotalPageFile', ctypes.c_ulonglong),
      ('ullAvailPageFile', ctypes.c_ulonglong),
      ('ullTotalVirtual', ctypes.c_ulonglong),
      ('ullAvailVirtual', ctypes.c_ulonglong),
      ('sullAvailExtendedVirtual', ctypes.c_ulonglong),
  ]

  def __init__(self):
    # Have to initialize this to the size of MemoryStatusEX.
    self.dwLength = ctypes.sizeof(self)  # pylint: disable=invalid-name
    super(MemoryStatusEX, self).__init__()


class WindowsSystemInfoProvider(SystemInfoProvider):
  """System info provider for windows based sytems."""

  def __init__(self):
    self.kernel32 = ctypes.windll.kernel32

  def get_cpu_load_avg(self) -> float:
    """Returns the average CPU load during last 1-minute."""
    pass

  def get_memory_stats(self) -> Tuple[int, int]:
    """Fetches the physical memory stats for the system.

    Returns:
      A tuple containing total memory and free memory in the system
      respectively.
    """

    meminfo = MemoryStatusEX()
    self.kernel32.GlobalMemoryStatusEx(ctypes.byref(meminfo))
    return (meminfo.ullTotalPhys, meminfo.ullAvailPhys)

  def get_disk_io_stats(self) -> Sequence[DiskIOStats]:
    raise NotImplementedError()


class OsxSystemInfoProvider(SystemInfoProvider):
  """System info provider for OSX based systems."""

  def get_cpu_load_avg(self) -> float:
    """Returns the average CPU load during last 1-minute."""
    return os.getloadavg()[0]

  def _get_total_memory(self) -> int:
    """Fetches the total memory in the system in bytes."""
    out = io.StringIO()
    err = io.StringIO()

    return_code = execution_utils.Exec(
        execution_utils.ArgsForExecutableTool('sysctl', '-n', 'hw.memsize'),
        out_func=out.write,
        err_func=err.write,
        no_exit=True,
    )

    if return_code != 0:
      raise diagnostic.DiagnosticIgnorableError(
          'Failed to fetch memory stats. {}'.format(err.getvalue())
      )

    return int(out.getvalue())

  def _get_free_memory(self) -> int:
    """Fetches the free memory in the system in bytes."""
    page_size = 4096
    out = io.StringIO()
    err = io.StringIO()

    return_code = execution_utils.Exec(
        execution_utils.ArgsForExecutableTool('vm_stat'),
        out_func=out.write,
        err_func=err.write,
        no_exit=True,
    )
    if return_code != 0:
      raise diagnostic.DiagnosticIgnorableError(
          'Failed to fetch memory stats. {}'.format(err.getvalue())
      )

    # Fetch only the number of free pages
    # https://www.unix.com/man-page/osx/1/vm_stat/.
    memory_pages_free_regex = re.compile(r'^Pages free:\s*(\d*).')

    for lines in out.getvalue().split('\n'):
      if m := memory_pages_free_regex.match(lines):
        return int(m.group(1)) * page_size
    return None

  def get_memory_stats(self) -> Tuple[int, int]:
    """Fetches the physical memory stats for the system in bytes.

    Returns:
      A tuple containing total memory and free memory in the system
      respectively.
    """
    return (self._get_total_memory(), self._get_free_memory())

  def _is_valid_iostat_output(
      self,
      disks: Sequence[str],
      header: Sequence[str],
      stats: Sequence[str],
      metric_count_per_disk: int,
  ) -> bool:
    """Validates the output of the iostat command.

    The iostat command output can be missing from the system due to missing
    installation or the command may not report the disk metrics if there is no
    disk activity.

    Args:
      disks: List of disks in the system.
      header: Header of the iostat output.
      stats: Stats of the iostat output.
      metric_count_per_disk: Number of metrics per disk.

    Returns:
      Whether the output is valid.
    """
    if len(header) != len(disks) * metric_count_per_disk:
      return False
    if len(stats) != len(header):
      return False
    return True

  def _get_disk_io_stats_from_iostat_output(
      self, disk_name: str, headers: Sequence[str], stats: Sequence[str]
  ) -> DiskIOStats:
    """Returns the disk I/O stats for a disk from the iostat output."""
    kilobytes_per_transfer_regex = re.compile(r'^KB/t')
    transfers_regex = re.compile(r'^xfrs')
    megabytes_transferred_regex = re.compile(r'^MB')

    transfer_count = None
    total_transfer_size = None
    average_transfer_size = None

    for index, header in enumerate(headers):
      if kilobytes_per_transfer_regex.match(header):
        average_transfer_size = float(stats[index]) * 1000
      elif transfers_regex.match(header):
        transfer_count = float(stats[index])
      elif megabytes_transferred_regex.match(header):
        total_transfer_size = float(stats[index]) * 1000000

    return DiskIOStats(
        name=disk_name,
        average_transfer_size=average_transfer_size,
        transfer_count=transfer_count,
        total_transfer_size=total_transfer_size,
    )

  def get_disk_io_stats(self) -> Sequence[DiskIOStats]:
    """Retrieves disk I/O statistics for all the disks in the system.

    Returns:
      A list of DiskIOStats objects containing the disk I/O statistics.

    Raises:
      DiagnosticIgnorableError: If failed to fetch disk I/O stats.
    """
    out = io.StringIO()
    err = io.StringIO()

    return_code = execution_utils.Exec(
        execution_utils.ArgsForExecutableTool('iostat', '-d', '-I'),
        out_func=out.write,
        err_func=err.write,
        no_exit=True,
    )
    if return_code != 0:
      raise diagnostic.DiagnosticIgnorableError(
          f'Failed to fetch disk I/O stats. {err.getvalue()}'
      )

    disks_line, header_line, stats_line = out.getvalue().split('\n')

    # The iostat command returns disk stats in columnar format:
    # https://ss64.com/mac/iostat.html.
    # The first line denotes the disks followed by the metric header.
    # The next line displays the stats.
    # Example:
    # disk0               disk1
    #   KB/t  xfrs   MB   KB/t  xfrs   MB
    #   0.00   0.00   0.00    0.00    0.00    0.00
    disks = re.split(r'\s+', disks_line)
    headers = re.split(r'\s+', header_line)
    stats = re.split(r'\s+', stats_line)

    metric_count_per_disk = 3

    if not self._is_valid_iostat_output(
        disks, headers, stats, metric_count_per_disk
    ):
      raise diagnostic.DiagnosticIgnorableError(
          'Failed to fetch disk I/O stats. Invalid output of iostat command.'
      )

    disk_io_stats = []
    counter = 0
    for disk in disks:
      disk_io_stats.append(
          self._get_disk_io_stats_from_iostat_output(
              disk,
              headers[counter : counter + metric_count_per_disk],
              stats[counter : counter + metric_count_per_disk],
          )
      )
      counter += metric_count_per_disk

    return disk_io_stats


def get_system_info_provider() -> SystemInfoProvider:
  """Factory for fetching system info provider based on the OS."""
  if platforms.OperatingSystem.Current() == platforms.OperatingSystem.WINDOWS:
    return WindowsSystemInfoProvider()
  if platforms.OperatingSystem.Current() == platforms.OperatingSystem.MACOSX:
    return OsxSystemInfoProvider()
  return UnixSystemInfoProvider()


def _get_metric_or_placeholder(
    metric_name: str, metric_function: Callable[[], int | Tuple[int, int]]
):
  try:
    return metric_function()
  # There may be some OSes where the metric is not available.
  except Exception as e:  # pylint: disable=broad-exception-caught
    log.exception('Failed to fetch metric: %s. %s', metric_name, e)
  return diagnostic.PLACEHOLDER_METRIC_VALUE


def get_system_info_diagnostic_result() -> diagnostic.DiagnosticResult:
  """Returns the system info as diagnostic result."""
  system_info_provider = get_system_info_provider()

  cpu_count = _get_metric_or_placeholder(
      _CPU_COUNT_METRIC_NAME, system_info_provider.get_cpu_count
  )
  cpu_load_avg = _get_metric_or_placeholder(
      _CPU_LOAD_AVG_METRIC_NAME, system_info_provider.get_cpu_load_avg
  )
  memory_stats = _get_metric_or_placeholder(
      'Memory Stats', system_info_provider.get_memory_stats
  )

  if memory_stats is not diagnostic.PLACEHOLDER_METRIC_VALUE:
    total_memory, free_memory = memory_stats
    total_memory = scaled_integer.FormatBinaryNumber(
        total_memory, decimal_places=1
    )
    free_memory = scaled_integer.FormatBinaryNumber(
        free_memory, decimal_places=1
    )
  else:
    total_memory = free_memory = diagnostic.PLACEHOLDER_METRIC_VALUE

  return diagnostic.DiagnosticResult(
      name=_DIAGNOSTIC_NAME,
      operation_results=[
          diagnostic.DiagnosticOperationResult(
              name=_CPU_COUNT_METRIC_NAME,
              result=cpu_count,
              payload_description=_CPU_COUNT_METRIC_DESCRIPTION,
          ),
          diagnostic.DiagnosticOperationResult(
              name=_CPU_LOAD_AVG_METRIC_NAME,
              result=cpu_load_avg,
              payload_description=_CPU_LOAD_AVG_METRIC_DESCRIPTION,
          ),
          diagnostic.DiagnosticOperationResult(
              name=_TOTAL_MEMORY_METRIC_NAME,
              result=total_memory,
              payload_description=_TOTAL_MEMORY_METRIC_DESCRIPTION,
          ),
          diagnostic.DiagnosticOperationResult(
              name=_FREE_MEMORY_METRIC_NAME,
              result=free_memory,
              payload_description=_FREE_MEMORY_METRIC_DESCRIPTION,
          ),
      ],
  )
