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
"""Utils for storage resource formatters."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

# Binary exponentiation strings for gsutil formatting.
_EXP_STRINGS = [
    (0, 'B', 'bit'),
    (10, 'KiB', 'Kibit', 'K'),
    (20, 'MiB', 'Mibit', 'M'),
    (30, 'GiB', 'Gibit', 'G'),
    (40, 'TiB', 'Tibit', 'T'),
    (50, 'PiB', 'Pibit', 'P'),
    (60, 'EiB', 'Eibit', 'E'),
]

_BYTE_EXPONENTS_AND_UNIT_STRINGS = [
    (0, 'B'),
    (10, 'KiB'),
    (20, 'MiB'),
    (30, 'GiB'),
    (40, 'TiB'),
    (50, 'PiB'),
    (60, 'EiB'),
]


def gsutil_format_byte_values(byte_count):
  """Generates a gsutil-style human-readable string for a number of bytes.

  Args:
    byte_count (int): A number of bytes to format.

  Returns:
    A string form of the number using size abbreviations (KiB, MiB, etc).
  """
  final_exponent, final_unit_string = _BYTE_EXPONENTS_AND_UNIT_STRINGS[0]
  for exponent, unit_string in _BYTE_EXPONENTS_AND_UNIT_STRINGS:
    if byte_count < 2**exponent:
      break
    final_exponent = exponent
    final_unit_string = unit_string

  rounded_number = round(byte_count / 2**final_exponent, 2)
  return '{:g} {}'.format(rounded_number, final_unit_string)
