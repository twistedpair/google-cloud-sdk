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

"""Deprecated completers to assist the completion cache refactor."""

from googlecloudsdk.command_lib.util import parameter_info_lib
from googlecloudsdk.core import remote_completion


# TODO(b/38374705): Drop the DeprecatedListCommandCompleter.
class DeprecatedListCommandCompleter(object):
  """A ListCommandCompleter for deprecated parser.add_argument() kwargs.

  This class is also temporarily used to allow new completers to use the old
  cache.  This will allow a small CL to switch from the old cache to the new
  one.

  Attributes:
    _deprecated_list_command: The gcloud list command, either space or '.'
      separated, that returns the list of current resource URIs.
    _deprecated_list_command_callback: A function that returns list_command
      given the parsed args.
  """

  def __init__(self, collection=None, list_command=None,
               list_command_callback=None, **kwargs):
    del kwargs
    self.collection = collection
    self._list_command = list_command
    self._list_command_callback = list_command_callback

  def ParameterInfo(self, parsed_args, argument):
    """Returns the parameter info object.

    Args:
      parsed_args: The command line parsed args object.
      argument: The argparse argument object attached to this completer.

    Returns:
      The parameter info object.
    """
    return parameter_info_lib.ParameterInfoByConvention(parsed_args, argument)

  def GetListCommand(self, parameter_info):
    """Returns the completion value list command argv."""
    if self._list_command_callback:
      return self._list_command_callback(parameter_info.parsed_args)
    if not self._list_command:
      return None
    list_command = self._list_command.split()
    if ' --quiet' not in self._list_command:
      list_command.append('--quiet')
    if ' --uri' in self._list_command and '--format' not in self._list_command:
      list_command.append('--format=disable')
    return list_command

  def Complete(self, prefix, parameter_info):
    """Returns the list of strings matching prefix.

    Args:
      prefix: The resource prefix string to match.
      parameter_info: A ParamaterInfo object for accessing parameter values in
        the program state.

    Returns:
      The list of strings matching prefix.
    """
    list_command = self.GetListCommand(parameter_info)
    command_line = ' '.join(list_command) if list_command else None
    completer = remote_completion.RemoteCompletion.GetCompleterForResource(
        resource=self.collection, command_line=command_line)
    return completer(parameter_info.parsed_args, prefix=prefix)
