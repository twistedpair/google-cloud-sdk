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

"""Calliope argparse argument completer objects."""

import sys

from googlecloudsdk.command_lib.util import deprecated_completers
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.console import progress_tracker


class ArgumentCompleter(object):
  """Argument completer wrapper to delay instantiation until first use.

  Attributes:
    _argument: The argparse argument object.
    _completer_class: The uninstantiated completer class.
  """

  def __init__(self, completer_class, argument):
    self._completer_class = completer_class
    self._argument = argument

  @property
  def completer_class(self):
    return self._completer_class

  @classmethod
  def _MakeCompletionErrorMessages(cls, msgs):
    """Returns a msgs list that will display 1 per line as completions."""
    attr = console_attr.GetConsoleAttr(out=sys.stdin)
    width, _ = attr.GetTermSize()
    # No worries for long msg: negative_integer * ' ' yields ''.
    return [msg + (width / 2 - len(msg)) * ' ' for msg in msgs]

  def __call__(self, prefix='', parsed_args=None, **kwargs):
    """A completer function called by argparse in arg_complete mode."""
    with progress_tracker.CompletionProgressTracker():
      completer = None
      try:
        completer = self._completer_class()
        parameter_info = completer.ParameterInfo(parsed_args, self._argument)
        if not isinstance(completer,
                          deprecated_completers.DeprecatedListCommandCompleter):
          completer = deprecated_completers.DeprecatedListCommandCompleter(
              collection=completer.collection,
              list_command=' '.join(completer.GetListCommand(parameter_info)))
        return completer.Complete(prefix, parameter_info)
      except (Exception, SystemExit) as e:  # pylint: disable=broad-except, e shall not pass
        # Fatal completer errors return two "completions", each an error
        # message that is displayed by the shell completers, and look more
        # like a pair of error messages than completions.  This is much better
        # than the default that falls back to the file completer, typically
        # yielding the list of all files in the current directory.
        #
        # NOTICE: Each message must start with different characters,
        # otherwise they will be taken as valid completions.  Also, the
        # messages are sorted in the display, so choose the first words wisely.
        if properties.VALUES.core.print_completion_tracebacks.Get():
          raise
        if completer:
          completer_name = completer.collection
        else:
          completer_name = self._completer_class.__name__
        return self._MakeCompletionErrorMessages([
            u'{} [[ERROR: {} resource completer failed.]]'.format(
                prefix, completer_name),
            u'{} [[REASON: {}]]'.format(prefix, unicode(e)),
        ])
