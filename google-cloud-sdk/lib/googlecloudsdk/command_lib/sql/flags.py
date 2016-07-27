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

USERNAME_FLAG = base.Argument('username',
                              completion_resource='sql.users',
                              help='Cloud SQL username.')

HOST_FLAG = base.Argument('host', help='Cloud SQL user\'s host.')

PASSWORD_FLAG = base.Argument('--password', help='Cloud SQL user\'s password.')
