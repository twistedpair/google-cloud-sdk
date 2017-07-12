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

"""Utilities for accessing modules by installation independent paths."""

from googlecloudsdk.core import exceptions


class Error(exceptions.Error):
  """Exceptions for this module."""


class ImportModuleError(Error):
  """ImportModule failed."""


def ImportModule(module_path):
  """Imports a module given its ModulePath and returns it.

  A module_path from GetModulePath() from any valid installation is importable
  by ImportModule() in another installation of same release.

  Args:
    module_path: The googlecloudsdk relative module path to import.

  Raises:
    ImportModuleError: Any failure to import.

  Returns:
    The Cloud SDK module named by module_path.
  """
  module_parts = module_path.split('.')
  module_name = module_parts.pop()
  module_parts.insert(0, 'googlecloudsdk')
  try:
    module_package = __import__('.'.join(module_parts), fromlist=[module_name])
    module_parts.pop(0)  # googlecloudsdk is implied in module paths
  except ImportError:
    module_parts.pop(0)
    try:
      module_package = __import__('.'.join(module_parts),
                                  fromlist=[module_name])
    except ImportError:
      raise ImportModuleError('Package [{}] not found.'.format(
          '.'.join(module_parts)))
  try:
    return getattr(module_package, module_name)
  except AttributeError:
    raise ImportModuleError('Module [{}] not found in package [{}].'.format(
        module_name, '.'.join(module_parts)))


def GetModulePath(obj):
  """Returns the module path string for obj, None if its builtin.

  The module path is relative and importable by ImportModule() from any
  installation of the current release.

  Args:
    obj: The object to get the module path from.

  Returns:
    The module path name for obj if not builtin else None.
  """
  try:
    # An object either has a module ...
    module = obj.__module__
  except AttributeError:
    # ... or it has a __class__ that has a __module__.
    obj = obj.__class__
    module = obj.__module__
  if module.startswith('__builtin__'):
    return None
  path = '.' + module
  part = '.googlecloudsdk.'  # This factors out the current installation dir.
  i = path.find(part)
  path = path[i + len(part):] if i >= 0 else module
  try:
    return path + '.' + obj.__name__
  except AttributeError:
    try:
      return path + '.' + obj.__class__.__name__
    except AttributeError:
      return None
