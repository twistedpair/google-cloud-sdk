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

"""The gcloud shell key bindings."""

from __future__ import unicode_literals

import re
import sys

from googlecloudsdk.command_lib.shell import browser
from prompt_toolkit import enums
from prompt_toolkit import keys
from prompt_toolkit.key_binding import manager


class _KeyBinding(object):
  """Key binding base info to keep registered bindings and toolbar in sync.

  Attributes:
    key: The keys.Key.* object.
    label: The short word label for the bottom toolbar.
    status: The bool => string toggle status map.
    toggle: The bool toggle state.
  """

  def __init__(self, key, label=None, status=None, toggle=True):
    self.key = key
    self.label = label
    self.status = status
    self.toggle = toggle

  def GetName(self):
    """Returns the binding display name."""
    return re.sub('.*<(.*)>.*', r'\1', str(self.key)).replace('C-', 'ctrl-')

  def GetLabel(self):
    """Returns the key binding display label containing the name and value."""
    label = [self.GetName(), ':']
    if self.label:
      label.append(self.label)
      if self.status:
        label.append(':')
    if self.status:
      label.append(self.status[self.toggle])
    return ''.join(label)

  def SetMode(self, cli):
    """Sets the toggle mode in the cli."""
    del cli

  def Handle(self, event):
    """Handles a bound key event."""
    self.toggle = not self.toggle
    self.SetMode(event.cli)


class _BrowseKeyBinding(_KeyBinding):
  """The browse key binding."""

  def __init__(self, key):
    super(_BrowseKeyBinding, self).__init__(key=key, label='browse')

  def Handle(self, event):
    doc = event.cli.current_buffer.document
    browser.OpenReferencePage(event.cli, doc.text, doc.cursor_position)


class _EditKeyBinding(_KeyBinding):
  """The edit mode key binding."""

  def __init__(self, key, toggle=True):
    super(_EditKeyBinding, self).__init__(
        key=key, toggle=toggle, status={False: 'vi', True: 'emacs'})

  def SetMode(self, cli):
    if self.toggle:
      cli.editing_mode = enums.EditingMode.EMACS
    else:
      cli.editing_mode = enums.EditingMode.VI


class _HelpKeyBinding(_KeyBinding):
  """The help key binding."""

  def __init__(self, key, toggle=True):
    super(_HelpKeyBinding, self).__init__(
        key=key, label='help', toggle=toggle, status={False: 'OFF', True: 'ON'})


class _QuitKeyBinding(_KeyBinding):
  """The quit key binding."""

  def __init__(self, key):
    super(_QuitKeyBinding, self).__init__(key=key, label='quit')

  def Handle(self, event):
    del event
    sys.exit(1)


class KeyBindings(object):
  """All key bindings.

  Attributes:
    bindings: The list of key bindings in left to right order.
    browse_key: The browse key binding that pops up the full reference
      doc in a browser.
    edit_key: The emacs/vi edit mode key binding. True for emacs,
      False for vi.
    help_key: The help visibility key binding. True for ON, false for
      OFF.
    quit_key: The key binding that exits the shell.
  """

  def __init__(self, edit_mode=True, help_mode=True):
    """Associates keys with handlers. Toggle states are reachable from here."""

    # The actual key bindings. Changing keys.Keys.* here automatically
    # propagates to the bottom toolbar labels.
    self.help_key = _HelpKeyBinding(keys.Keys.ControlT, toggle=help_mode)
    self.edit_key = _EditKeyBinding(keys.Keys.F3, toggle=edit_mode)
    self.browse_key = _BrowseKeyBinding(keys.Keys.F8)
    self.quit_key = _QuitKeyBinding(keys.Keys.ControlQ)

    # This is the order of binding label appearance in the bottom toolbar.
    self.bindings = [
        self.quit_key,
        self.help_key,
    ]

  def MakeRegistry(self):
    """Makes and returns a key binding registry populated with the bindings."""
    m = manager.KeyBindingManager(
        enable_abort_and_exit_bindings=True,
        enable_system_bindings=True,
        enable_search=True,
        enable_auto_suggest_bindings=True,)

    for binding in self.bindings:
      m.registry.add_binding(binding.key, eager=True)(binding.Handle)

    return m.registry

  def Initialize(self, cli):
    """Initialize key binding defaults in the cli."""
    for binding in self.bindings:
      binding.SetMode(cli)
