# -*- coding: utf-8 -*- #
# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Defines tool-wide constants."""
from __future__ import absolute_import
from __future__ import division

# Defaults for instance creation.
from __future__ import unicode_literals
DEFAULT_MACHINE_TYPE = 'db-n1-standard-1'

# Determining what executables, flags, and defaults to use for sql connect.
DB_EXE = {'MYSQL': 'mysql', 'POSTGRES': 'psql'}

EXE_FLAGS = {
    'mysql': {
        'user': '-u',
        'password': '-p',
        'hostname': '-h'
    },
    'psql': {
        'user': '-U',
        'password': '-W',
        'hostname': '-h',
        'database': '-d'
    }
}

DEFAULT_SQL_USER = {'mysql': 'root', 'psql': 'postgres'}

# Size conversions.
BYTES_TO_GB = 1 << 30
