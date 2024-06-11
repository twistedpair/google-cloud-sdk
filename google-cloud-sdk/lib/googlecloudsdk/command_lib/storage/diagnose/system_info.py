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

import abc
import ctypes
import io
import os
import re
from typing import Tuple
from googlecloudsdk.command_lib.storage.diagnose import diagnostic
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core.util import files


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
