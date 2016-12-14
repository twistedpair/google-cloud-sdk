# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Resource display info for the Calliope display module."""


class DisplayInfo(object):
  """Display info accumulator for priming Displayer.

  "legacy" logic will be dropped when the incremental Command class refactor
  is complete.

  Attributes:
    _format: The default format string. args.format takes precedence.
    _transforms: The filter/format transforms symbol dict.
    _aliases: The resource name alias dict.
    _legacy: Use legacy Command methods for display info if True. This will
      be deleted when all commands are refactored to use parser.display_info.
  """

  def __init__(self):
    self._legacy = True
    self._format = None
    self._transforms = {}
    self._aliases = {}

  # pylint: disable=redefined-builtin, name matches args.format and --format
  def AddFormat(self, format):
    """Adds a format to the display info, newer info takes precedence.

    Args:
      format: The default format string. args.format takes precedence.
    """
    self._legacy = False
    if format:
      self._format = format

  def AddTransforms(self, transforms):
    """Adds transforms to the display info, newer values takes precedence.

    Args:
      transforms: A filter/format transforms symbol dict.
    """
    self._legacy = False
    if transforms:
      self._transforms.update(transforms)

  def AddAliases(self, aliases):
    """Adds aliases to the display info, newer values takes precedence.

    Args:
      aliases: The resource name alias dict.
    """
    self._legacy = False
    if aliases:
      self._aliases.update(aliases)

  def AddLowerDisplayInfo(self, display_info):
    """Add lower precedence display_info to the object.

    This method is called by calliope to propagate CLI low precedence parent
    info to its high precedence children.

    Args:
      display_info: The low precedence DisplayInfo object to add.
    """
    if not self._format:
      self._format = display_info.format
    if display_info.transforms:
      transforms = dict(display_info.transforms)
      transforms.update(self.transforms)
      self._transforms = transforms
    if display_info.aliases:
      aliases = dict(display_info.aliases)
      aliases.update(self._aliases)
      self._aliases = aliases

  @property
  def format(self):
    return self._format

  @property
  def aliases(self):
    return self._aliases

  @property
  def transforms(self):
    return self._transforms

  @property
  def legacy(self):
    return self._legacy

  @legacy.setter
  def legacy(self, value):
    self._legacy = value
