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
from collections.abc import Iterator, Mapping, MutableSequence, Sequence
import contextlib
import ctypes
from ctypes import wintypes
import dataclasses
import io
import os
import re
from typing import Callable, Tuple, TypeVar

import frozendict
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
_SYSTEM_DIAGNOSTIC_NAME = 'System Info'
_DISK_IO_DIAGNOSTIC_NAME = 'Disk IO Stats Delta'
_DISK_TRANSFER_COUNT_METRIC_NAME = 'Disk Transfer Count'
_DISK_TRANSFER_SIZE_METRIC_NAME = 'Disk Transfer Size'
_DISK_AVERAGE_TRANSFER_SIZE_METRIC_NAME = 'Disk Average Transfer Size'
_T = TypeVar('_T')


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
    raise NotImplementedError()

  @abc.abstractmethod
  def get_memory_stats(self) -> Tuple[int, int]:
    """Fetches the physical memory stats for the system in bytes.

    Returns:
      A tuple containing total memory and free memory in the system
      respectively.
    """
    raise NotImplementedError()

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
    super().__init__()


class PDHCounterUnion(ctypes.Union):
  """Structure for the union of the windows perfmon counter values.

  https://learn.microsoft.com/en-us/windows/win32/api/pdh/ns-pdh-pdh_counter_union
  """

  _fields_ = [
      ('longValue', wintypes.LONG),
      ('doubleValue', ctypes.c_double),
      ('largeValue', ctypes.c_longlong),
      ('AnsiStringValue', wintypes.LPCSTR),
      ('WideStringValue', wintypes.LPCWSTR),
  ]


class PDHFormattedCounterValue(ctypes.Structure):
  """Structure for the windows perfmon formatted counter value.

  https://learn.microsoft.com/en-us/windows/win32/api/pdh/ns-pdh-pdh_fmt_countervalue
  """

  _fields_ = [
      ('CStatus', wintypes.DWORD),
      ('union', PDHCounterUnion),
  ]


class WindowsPerfmonCounterProvider:
  """Provider for interacting with windows perfmon counters.

  This class wraps the windows perfmon low level API.
  https://learn.microsoft.com/en-us/windows/win32/perfctrs/using-the-perflib-functions-to-consume-counter-data

  Attributes:
    counters: The string counter identifiers whose values are to be fetched.
  """

  # Constant for fetching the double value from the perfmon counter.
  _PDH_FORMAT_DOUBLE = 512

  # Mapping of the error codes returned by the perfmon API to human readable
  # error messages.
  # https://learn.microsoft.com/en-us/windows/win32/perfctrs/pdh-error-codes
  _PDH_ERRORCODES_TO_MESSAGES = frozendict.frozendict({
      0x00000000: 'PDH_CSTATUS_VALID_DATA',
      0x800007D0: 'PDH_CSTATUS_NO_MACHINE',
      0x800007D2: 'PDH_MORE_DATA',
      0x800007D5: 'PDH_NO_DATA',
      0xC0000BB8: 'PDH_CSTATUS_NO_OBJECT',
      0xC0000BB9: 'PDH_CSTATUS_NO_COUNTER',
      0xC0000BBB: 'PDH_MEMORY_ALLOCATION_FAILURE',
      0xC0000BBC: 'PDH_INVALID_HANDLE',
      0xC0000BBD: 'PDH_INVALID_ARGUMENT',
      0xC0000BC0: 'PDH_CSTATUS_BAD_COUNTERNAME',
      0xC0000BC2: 'PDH_INSUFFICIENT_BUFFER',
      0xC0000BC6: 'PDH_INVALID_DATA',
      0xC0000BD3: 'PDH_NOT_IMPLEMENTED',
      0xC0000BD4: 'PDH_STRING_NOT_FOUND',
  })

  def __init__(self, counters: Sequence[str]):
    """Initializes the provider.

    Some of the perfmom counters are intantaneous and some are cumulative. This
    provider will fetch the counters during instantiation so that the data for
    cummulative counters is availble on successive calls to the
    get_perfmon_counter_values method. The data for cumulative counters is
    updated from the start of the initialization to the time of the call to
    get_perfmon_counter_values. The instance of this class encapsulates the
    counter state which is updated during the initialization and the subsequent
    calls to get_perfmon_counter_values. The counter state is reset when the
    close method is called.

    Example usage:
      provider = WindowsPerfmonCounterProvider(counters)
      counter_values = provider.get_perfmon_counter_values()
      ...
      # Fetch the counter values again.
      counter_values = provider.get_perfmon_counter_values()
      ...
      # Close the perfmon query.
      provider.close()

      Can be used with closing context manager as well.
      with contextlib.closing(WindowsPerfmonCounterProvider(counters)) as
      provider:
        counter_values = provider.get_perfmon_counter_values()

    Args:
      counters: The language neutral perfmon counter identifiers.

    Raises:
      DiagnosticIgnorableError: If failed to initialize the perfmon query.
    """
    self.counters = counters
    self._pdh = ctypes.windll.pdh
    self._query_handle = None
    self._counter_handles = []
    self._initialize_perfmon_query()

    # Populate the initial counter values.
    self._populate_perfmon_counter_values()

  def _get_pdh_error(self, code) -> str:
    """Convert a PDH error code to a human readable string."""
    code &= 0xFFFF_FFFF  # signed to unsigned conversion.
    return self._PDH_ERRORCODES_TO_MESSAGES.get(code, code)

  def _translate_and_raise_error(self, error_code: int) -> None:
    """Translates the error code to a human readable string and raises it."""
    raise diagnostic.DiagnosticIgnorableError(
        f'Failed to fetch perfmon data. {self._get_pdh_error(error_code)}'
    )

  def _initialize_perfmon_query(self) -> None:
    """Initializes the perfmon query."""
    # Handle to the perfmon query.
    self._query_handle = wintypes.HANDLE()
    # Handle to each counter.
    self._counter_handles = []

    # TODO(b/358001644): Confirm the validity of query_handle in case of
    # PdhOpenQueryW errors.
    error = self._pdh.PdhOpenQueryW(None, 0, ctypes.byref(self._query_handle))
    if error:
      self._translate_and_raise_error(error)

    for counter in self.counters:
      counter_handle = wintypes.HANDLE()
      error = self._pdh.PdhAddEnglishCounterW(
          self._query_handle, counter, 0, ctypes.byref(counter_handle)
      )
      if error:
        self._translate_and_raise_error(error)
      self._counter_handles.append(counter_handle)

  def _populate_perfmon_counter_values(self) -> None:
    """Fetches the values for the perfmon counters."""
    error = self._pdh.PdhCollectQueryData(self._query_handle)
    if error:
      self._translate_and_raise_error(error)

  def get_perfmon_counter_values(self) -> Iterator[float | None]:
    """Fetches the values for the perfmon counters.

    For the cumulative counters, the values are updated from the start of the
    initialization to the time of the call to this method.

    Yields:
      The value for the perfmon counter as Float or None if counter value is not
      available.

    Raises:
      DiagnosticIgnorableError: If failed to fetch the perfmon counter values.
    """
    self._populate_perfmon_counter_values()

    for counter_handle in self._counter_handles:
      value = PDHFormattedCounterValue()
      error = self._pdh.PdhGetFormattedCounterValue(
          counter_handle, self._PDH_FORMAT_DOUBLE, None, ctypes.byref(value)
      )
      if error:
        self._translate_and_raise_error(error)

      yield getattr(value.union, 'doubleValue', None)

  def close(self) -> None:
    """Closes the perfmon query."""
    if not self._query_handle:
      return
    error = self._pdh.PdhCloseQuery(self._query_handle)
    self._query_handle = None
    if error:
      log.error(
          'Failed to close the perfmon query. %s', self._get_pdh_error(error)
      )


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
    raise NotImplementedError('Not implemented for Windows.')


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

    disks_line, header_line, stats_line, *_ = out.getvalue().split('\n')

    # The iostat command returns disk stats in columnar format:
    # https://ss64.com/mac/iostat.html.
    # The first line denotes the disks followed by the metric header.
    # The next line displays the stats.
    # Example:
    # disk0               disk1
    #   KB/t  xfrs   MB   KB/t  xfrs   MB
    #   0.00   0.00   0.00    0.00    0.00    0.00
    disks = disks_line.split()
    headers = header_line.split()
    stats = stats_line.split()

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
    metric_name: str,
    metric_function: Callable[[], _T],
) -> _T | str:
  try:
    return metric_function()
  # There may be some OSes where the metric is not available.
  except Exception as e:  # pylint: disable=broad-exception-caught
    log.exception('Failed to fetch metric: %s. %s', metric_name, e)
  return diagnostic.PLACEHOLDER_METRIC_VALUE


def get_system_info_diagnostic_result(
    provider: SystemInfoProvider,
) -> diagnostic.DiagnosticResult:
  """Returns the system info as diagnostic result."""

  cpu_count = _get_metric_or_placeholder(
      _CPU_COUNT_METRIC_NAME, provider.get_cpu_count
  )
  cpu_load_avg = _get_metric_or_placeholder(
      _CPU_LOAD_AVG_METRIC_NAME, provider.get_cpu_load_avg
  )
  memory_stats = _get_metric_or_placeholder(
      'Memory Stats', provider.get_memory_stats
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
      name=_SYSTEM_DIAGNOSTIC_NAME,
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


def _format_disk_io_stats(
    disk_stat: DiskIOStats,
) -> Mapping[str, str]:
  """Formats the disk I/O stat metrics to a human readable format.

  Args:
    disk_stat: The disk I/O stats object.

  Returns:
    A mapping of metric name to the formatted metric value.
  """
  formatted_transfer_count = f'{disk_stat.transfer_count:.1f}'

  formatted_total_transfer_size = None
  if disk_stat.total_transfer_size:
    formatted_total_transfer_size = scaled_integer.FormatBinaryNumber(
        disk_stat.total_transfer_size, decimal_places=1
    )

  formatted_average_transfer_size = None
  if disk_stat.average_transfer_size:
    formatted_average_transfer_size = scaled_integer.FormatBinaryNumber(
        disk_stat.average_transfer_size, decimal_places=1
    )

  return {
      _DISK_TRANSFER_COUNT_METRIC_NAME: formatted_transfer_count,
      _DISK_TRANSFER_SIZE_METRIC_NAME: formatted_total_transfer_size,
      _DISK_AVERAGE_TRANSFER_SIZE_METRIC_NAME: formatted_average_transfer_size,
  }


@contextlib.contextmanager
def get_disk_io_stats_delta_diagnostic_result(
    provider: SystemInfoProvider,
    test_result: MutableSequence[diagnostic.DiagnosticResult],
):
  """A context manager to get the disk I/O stats delta as diagnostic result.

  The context manager will fetch the disk I/O stats at the beginning and end of
  the context and calculate the delta for each disk metric. Adds the delta
  stats as a diagnostic result to the test_result list.

  Args:
    provider: System info provider.
    test_result: List to append the diagnostic result.

  Yields:
    None
  """
  disk_io_metric_name = 'Disk IO Stats'
  initial_disk_stats = _get_metric_or_placeholder(
      disk_io_metric_name, provider.get_disk_io_stats
  )

  yield

  if initial_disk_stats is diagnostic.PLACEHOLDER_METRIC_VALUE:
    return

  final_disk_stats = _get_metric_or_placeholder(
      disk_io_metric_name, provider.get_disk_io_stats
  )

  if final_disk_stats is diagnostic.PLACEHOLDER_METRIC_VALUE:
    return

  diagnostic_operation_results = []
  for disk_stat in final_disk_stats:
    matching_initial_disk_stats = [
        stat for stat in initial_disk_stats if stat.name == disk_stat.name
    ]
    if len(matching_initial_disk_stats) != 1:
      return

    initial_disk_stat = matching_initial_disk_stats[0]

    # Calculating delta for the average metric does not make sense so use the
    # final value.
    average_transfer_size = disk_stat.average_transfer_size

    transfer_count_delta = (
        disk_stat.transfer_count - initial_disk_stat.transfer_count
    )
    total_transfer_size_delta = (
        disk_stat.total_transfer_size - initial_disk_stat.total_transfer_size
    )

    disk_stat_delta = DiskIOStats(
        name=disk_stat.name,
        average_transfer_size=average_transfer_size,
        transfer_count=transfer_count_delta,
        total_transfer_size=total_transfer_size_delta,
    )

    diagnostic_operation_results.append(
        diagnostic.DiagnosticOperationResult(
            name=disk_stat.name, result=_format_disk_io_stats(disk_stat_delta)
        )
    )

  test_result.append(
      diagnostic.DiagnosticResult(
          name=_DISK_IO_DIAGNOSTIC_NAME,
          operation_results=diagnostic_operation_results,
      )
  )
