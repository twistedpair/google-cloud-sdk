# -*- coding: utf-8 -*- #
# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Common functions for users."""

from __future__ import unicode_literals
DEFAULT_LIST_FORMAT = """\
    table(
      name,
      owner,
      description
    )"""


def AddUserArgument(parser, operation_type, custom_help=None):
  """Adds a user positional argument for users commands."""
  help_text = custom_help or ('If provided, the name of the user to {0}. Else, '
                              'the default user will be {0}d.').format(
                                  operation_type)
  parser.add_argument(
      'name',
      nargs='?',
      help="""\
      {0} The default username is mapped from the email address of the
      authenticated account.
      Please run:

        $ gcloud config set account ACCOUNT

      to change the authenticated account.""".format(help_text))
