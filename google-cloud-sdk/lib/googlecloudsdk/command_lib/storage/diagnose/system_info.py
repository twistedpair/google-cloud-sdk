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
import os
import re
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
  def get_memory_stats(self) -> (int, int):
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

  def get_memory_stats(self) -> (int, int):
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
