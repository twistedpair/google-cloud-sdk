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

from googlecloudsdk.command_lib.compute import completers
from googlecloudsdk.core.resource import resource_property
from googlecloudsdk.core.resource import resource_registry


# TODO(b/38374705): Drop the DeprecatedListCommandCompleter.
class DeprecatedListCommandCompleter(completers.ListCommandCompleter):
  """A ListCommandCompleter for deprecated parser.add_argument() kwargs.

  This class encapsulates all of the assumptions made by the deprecated
  remote_completion module.  It derives from the compute ListCommandCompleter
  because it pulls in sub-completers for zone, region and project resource
  parameters.

  Attributes:
    _deprecated_list_command: The gcloud list command, either space or '.'
      separated, that returns the list of current resource URIs.
    _deprecated_list_command_callback: A function that returns list_command
      given the parsed args.
  """

  def __init__(self, list_command=None, list_command_callback=None, **kwargs):
    super(DeprecatedListCommandCompleter, self).__init__(**kwargs)
    self._deprecated_list_command = list_command
    self._deprecated_list_command_callback = list_command_callback

  def GetListCommand(self, parameter_info):
    """Returns the list command argv given parameter_info."""
    info = resource_registry.Get(self.collection)
    if info.cache_command:
      command = info.cache_command
    elif info.list_command:
      command = info.list_command
    elif self._deprecated_list_command_callback:
      command = ' '.join(self._deprecated_list_command_callback(
          parameter_info.parsed_args))
    else:
      if self._deprecated_list_command:
        command = self._deprecated_list_command
      else:
        command = resource_property.ConvertToSnakeCase(
            self.collection).replace('_', '-') + ' list'
      command = command.replace('.', ' ')
    return command.split(' ') + ['--uri', '--quiet', '--format=disable']
