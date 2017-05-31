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

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import base

INSTANCE_FLAG = base.Argument(
    '--instance',
    '-i',
    required=True,
    completion_resource='sql.instances',
    help='Cloud SQL instance ID.')

DEPRECATED_INSTANCE_FLAG_REQUIRED = base.Argument(
    '--instance',
    '-i',
    action=actions.DeprecationAction(
        '--instance',
        removed=False,
        warn=('Starting on 2017-06-30, --instance will no longer be a valid '
              'flag: Run the same command but omit this flag.'),),
    required=True,
    completion_resource='sql.instances',
    help='Cloud SQL instance ID.')

DEPRECATED_INSTANCE_FLAG = base.Argument(
    '--instance',
    '-i',
    action=actions.DeprecationAction(
        '--instance',
        removed=False,
        warn=('Starting on 2017-06-30, --instance will no longer be a valid '
              'flag: Run the same command but omit this flag.'),),
    required=False,
    completion_resource='sql.instances',
    help='Cloud SQL instance ID.')

USERNAME_FLAG = base.Argument(
    'username', completion_resource='sql.users', help='Cloud SQL username.')

HOST_FLAG = base.Argument('host', help='Cloud SQL user\'s host.')

PASSWORD_FLAG = base.Argument(
    '--password',
    help='Cloud SQL user\'s password.')
PROMPT_FOR_PASSWORD_FLAG = base.Argument(
    '--prompt-for-password',
    action='store_true',
    help=('Prompt for the Cloud SQL user\'s password with character echo '
          'disabled. The password is all typed characters up to but not '
          'including the RETURN or ENTER key.'))

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

OPERATION_ARGUMENT = base.Argument(
    'operation',
    nargs='+',
    help='An identifier that uniquely identifies the operation.')

INSTANCES_FORMAT = """
  table(
    instance:label=NAME,
    region,
    settings.tier,
    ipAddresses[0].ipAddress.yesno(no="-"):label=ADDRESS,
    state:label=STATUS
  )
"""

INSTANCES_FORMAT_BETA = """
  table(
    name,
    region,
    settings.tier,
    ipAddresses[0].ipAddress.yesno(no="-"):label=ADDRESS,
    state:label=STATUS
  )
"""

OPERATION_FORMAT = """
  table(
    operation,
    operationType:label=TYPE,
    startTime.iso():label=START,
    endTime.iso():label=END,
    error[0].code.yesno(no="-"):label=ERROR,
    state:label=STATUS
  )
"""

OPERATION_FORMAT_BETA = """
  table(
    name,
    operationType:label=TYPE,
    startTime.iso():label=START,
    endTime.iso():label=END,
    error[0].code.yesno(no="-"):label=ERROR,
    status:label=STATUS
  )
"""

SSL_CERTS_FORMAT = """
  table(
    commonName:label=NAME,
    sha1Fingerprint,
    expirationTime.yesno(no="-"):label=EXPIRATION
  )
"""

TIERS_FORMAT = """
  table(
    tier,
    region.list():label=AVAILABLE_REGIONS,
    RAM.size(),
    DiskQuota.size():label=DISK
  )
"""

USERS_FORMAT_BETA = """
  table(
    name.yesno(no='(anonymous)'),
    host
  )
"""
