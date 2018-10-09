# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Mappings from TextTypes to TextAttributes used by the TextTypeParser."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.console.style import ansi
from googlecloudsdk.core.console.style import text


class StyleMapping(object):
  """Mapping of TextTypes to TextAttributes."""

  def __init__(self, mappings):
    """Creates a StyleMapping object to be used by a StyledLogger.

    Args:
      mappings: (dict[TextTypes, TextAttributes]), the mapping
        to be used for this StyleMapping object.
    """
    self.mappings = mappings

  def __getitem__(self, key):
    if key in self.mappings:
      return self.mappings[key]
    return None


STYLE_MAPPINGS_BASIC = StyleMapping({
    text.TextTypes.RESOURCE_NAME: text.TextAttributes('[{}]'),
    text.TextTypes.USER_INPUT: text.TextAttributes('{}'),
})


STYLE_MAPPINGS_ANSI = StyleMapping({
    text.TextTypes.RESOURCE_NAME: text.TextAttributes(
        '[{}]', color=ansi.Colors.BLUE, attrs=[]),
    text.TextTypes.USER_INPUT: text.TextAttributes(
        '{}', color=None, attrs=[ansi.Attrs.BOLD]),
    text.TextTypes.COMMAND: text.TextAttributes(
        '{}', color=None, attrs=[ansi.Attrs.ITALICS]),
})


def GetStyleMappings(console_attributes=None):
  console_attributes = console_attributes or console_attr.GetConsoleAttr()
  if console_attributes.SupportsAnsi():
    return STYLE_MAPPINGS_ANSI
  else:
    return STYLE_MAPPINGS_BASIC
