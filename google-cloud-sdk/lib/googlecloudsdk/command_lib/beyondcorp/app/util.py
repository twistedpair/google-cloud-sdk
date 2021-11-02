# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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

"""CLI Utilities for beyondcorp app commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions

MEMBER_PARSE_ERROR = ('Error parsing member [{}]: member must be prefixed of '
                      'the form serviceAccount:<value>.')
MEMBER_PREFIX = 'serviceAccount'


class MemberParseError(exceptions.Error):
  """Error if a member is not in correct format."""


def MemberProcessor(member):
  """Validates and parses a service account from member string.

  Expects string.

  Args:
    member: string in format of 'serviceAccount:<value>'.

  Raises:
    MemberParseError: if string is not in valid format 'serviceAccount:<value>',
    raises exception MemberParseError.

  Returns:
    string: Returns <value> part from 'serviceAccount:<value>'.
  """
  member_array = member.split(':')

  if len(member_array) == 2 and member_array[0] == MEMBER_PREFIX:
    return member_array[1]
  else:
    raise MemberParseError(
        MEMBER_PARSE_ERROR.format(member))
