# -*- coding: utf-8 -*- #
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

"""Cloud SDK markdown document renderer base class."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc

from googlecloudsdk.core import log

import six
from six.moves import range  # pylint: disable=redefined-builtin


# Font Attributes.
BOLD, ITALIC, CODE = list(range(3))


@six.add_metaclass(abc.ABCMeta)
class Renderer(object):  # pytype: disable=ignored-abstractmethod
  r"""Markdown renderer base class.

  The member functions provide an abstract document model that matches markdown
  entities to output document renderings.

  Attributes:
    _font: The font attribute bitmask.
    _lang: ```lang\n...\n``` code block language. None if not in code block,
      '' if in code block with no explicit lang specified.
    _out: The output stream.
    _title: The document tile.
    _width: The output width in characters.
  """

  def __init__(self, out=None, title=None, width=80):
    self._font = 0
    self._lang = None
    self._out = out or log.out
    self._title = title
    self._width = width

  def Entities(self, buf):
    """Converts special characters to their entity tags.

    This is applied after font embellishments.

    Args:
      buf: The normal text that may contain special characters.

    Returns:
      The escaped string.
    """
    return buf

  def Escape(self, buf):
    """Escapes special characters in normal text.

    This is applied before font embellishments.

    Args:
      buf: The normal text that may contain special characters.

    Returns:
      The escaped string.
    """
    return buf

  def Finish(self):
    """Finishes all output document rendering."""
    return None

  def Font(self, unused_attr, unused_out=None):
    """Returns the font embellishment string for attr.

    Args:
      unused_attr: None to reset to the default font, otherwise one of BOLD,
        ITALIC, or CODE.
      unused_out: Writes tags line to this stream if not None.

    Returns:
      The font embellishment string.
    """
    return ''

  def SetLang(self, lang):
    """Sets the ```...``` code block language.

    Args:
      lang: The language name, None if not in a code block, '' is no explicit
        language specified.
    """
    self._lang = lang

  def Link(self, target, text):
    """Renders an anchor.

    Args:
      target: The link target URL.
      text: The text to be displayed instead of the link.

    Returns:
      The rendered link anchor and text.
    """
    if text:
      if target and '://' in target:
        # Show non-local targets.
        return '{0} ({1})'.format(text, target)
      return text
    if target:
      return target
    return '[]()'
