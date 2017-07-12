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

"""The meta cache command library support."""

from googlecloudsdk.api_lib.util import apis_util
from googlecloudsdk.calliope import parser_completer
from googlecloudsdk.calliope import walker
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import module_util
from googlecloudsdk.core import resources
from googlecloudsdk.core.cache import exceptions as cache_exceptions
from googlecloudsdk.core.cache import file_cache
from googlecloudsdk.core.cache import resource_cache


_CACHE_RI_DEFAULT = 'resource://'


class Error(exceptions.Error):
  """Base cache exception."""


class NoTablesMatched(Error):
  """No table names matched the patterns."""


def GetCache(name, create=False):
  """Returns the cache given a cache indentfier name.

  Args:
    name: The cache name to operate on. May be prefixed by "resource://" for
      resource cache names or "file://" for persistent file cache names. If
      only the prefix is specified then the default cache name for that prefix
      is used.
    create: Creates the persistent cache if it exists if True.

  Raises:
    CacheNotFound: If the cache does not exist.

  Returns:
    The cache object.
  """

  types = {
      'file': file_cache.Cache,
      'resource': resource_cache.ResourceCache,
  }

  def _OpenCache(cache_class, name):
    try:
      return cache_class(name, create=create)
    except cache_exceptions.Error as e:
      raise Error(e)

  if name:
    for cache_id, cache_class in types.iteritems():
      if name.startswith(cache_id + '://'):
        name = name[len(cache_id) + 3:]
        if not name:
          name = None
        return _OpenCache(cache_class, name)
  return _OpenCache(resource_cache.Cache, name)


def AddCacheFlag(parser):
  """Adds the persistent cache flag to the parser."""
  parser.add_argument(
      '--cache',
      metavar='CACHE_NAME',
      default='resource://',
      help=('The cache name to operate on. May be prefixed by '
            '"resource://" for resource cache names. If only the prefix is '
            'specified then the default cache name for that prefix is used.'))


class _CompleterModule(object):

  def __init__(self, module_path, collection, api_version):
    self.module_path = module_path
    self.collection = collection
    self.api_version = api_version
    self.attachments = []
    self._attachments_dict = {}


class _CompleterAttachment(object):

  def __init__(self, command):
    self.command = command
    self.arguments = []


class _CompleterModuleGenerator(walker.Walker):
  """Constructs a CLI command dict tree."""

  def __init__(self, cli):
    super(_CompleterModuleGenerator, self).__init__(cli)
    self._modules_dict = {}

  def Visit(self, command, parent, is_group):
    """Visits each command in the CLI command tree to construct the module list.

    Args:
      command: group/command CommandCommon info.
      parent: The parent Visit() return value, None at the top level.
      is_group: True if command is a group, otherwise its is a command.

    Returns:
      The subtree module list.
    """
    args = command.ai
    for arg in sorted(args.flag_args + args.positional_args):
      try:
        completer_class = arg.completer
      except AttributeError:
        continue
      collection = None
      api_version = None
      if isinstance(completer_class, parser_completer.ArgumentCompleter):
        completer_class = completer_class.completer_class
      module_path = module_util.GetModulePath(completer_class)
      if isinstance(completer_class, type):
        try:
          completer = completer_class()
          try:
            collection = completer.collection
          except AttributeError:
            pass
          try:
            api_version = completer.api_version
          except AttributeError:
            pass
        except (apis_util.UnknownAPIError,
                resources.InvalidCollectionException) as e:
          collection = u'ERROR: {}'.format(e)
      if arg.option_strings:
        name = arg.option_strings[0]
      else:
        name = arg.dest.replace('_', '-')
      module = self._modules_dict.get(module_path)
      if not module:
        module = _CompleterModule(
            collection=collection,
            api_version=api_version,
            module_path=module_path,
        )
      self._modules_dict[module_path] = module
      command_path = ' '.join(command.GetPath())
      # pylint: disable=protected-access
      attachment = module._attachments_dict.get(command_path)
      if not attachment:
        attachment = _CompleterAttachment(command_path)
        module._attachments_dict[command_path] = attachment
        module.attachments.append(attachment)
      attachment.arguments.append(name)
    return self._modules_dict


def ListAttachedCompleters(cli):
  """Returns the list of all attached CompleterModule objects in cli."""
  return _CompleterModuleGenerator(cli).Walk().values()
