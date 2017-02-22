# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Common flags for some of the SQL commands."""

from googlecloudsdk.calliope import base

INSTANCE_FLAG = base.Argument(
    '--instance',
    '-i',
    required=True,
    completion_resource='sql.instances',
    help='Cloud SQL instance ID.')

USERNAME_FLAG = base.Argument(
    'username', completion_resource='sql.users', help='Cloud SQL username.')

HOST_FLAG = base.Argument('host', help='Cloud SQL user\'s host.')

PASSWORD_FLAG = base.Argument('--password', help='Cloud SQL user\'s password.')

# Database specific flags

DATABASE_NAME_FLAG = base.Argument(
    'database',
    completion_resource='sql.databases',
    help='Cloud SQL database name.')

CHARSET_FLAG = base.Argument(
    '--charset',
    help='Cloud SQL database charset setting, which specifies the '
    'set of symbols and encodings used to store the data in your database. Each'
    ' database version may support a different set of charsets.')

COLLATION_FLAG = base.Argument(
    '--collation',
    help='Cloud SQL database collation setting, which specifies '
    'the set of rules for comparing characters in a character set. Each'
    ' database version may support a different set of collations.')
