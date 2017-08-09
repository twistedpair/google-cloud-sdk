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

"""Helpers to load commands from the filesystem."""

import abc
import os
import re
import sys

from googlecloudsdk.calliope import base
from googlecloudsdk.core.util import pkg_resources
import yaml


class CommandLoadFailure(Exception):
  """An exception for when a command or group module cannot be imported."""

  def __init__(self, command, root_exception):
    self.command = command
    self.root_exception = root_exception
    super(CommandLoadFailure, self).__init__(
        'Problem loading {command}: {issue}.'.format(
            command=command, issue=str(root_exception)))


class LayoutException(Exception):
  """An exception for when a command or group .py file has the wrong types."""


class ReleaseTrackNotImplementedException(Exception):
  """An exception for when a command or group does not support a release track.
  """


class YamlCommandTranslator(object):
  """An interface to implement when registering a custom command loader."""
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def Translate(self, path, command_data):
    """Translates a yaml command into a calliope command.

    Args:
     path: [str], The same as module_path but with the groups named as they
       will be in the CLI.
      command_data: dict, The parsed contents of the command spec from the
        yaml file that corresponds to the release track being loaded.

    Returns:
      calliope.base.Command, A command class (not instance) that
      implements the spec.
    """
    pass


def FindSubElements(module_dir, module_path, release_track):
  """Find all the sub groups and commands under this group.

  Args:
    module_dir: str, The path to the tools directory that this command or
      group lives within.
    module_path: [str], The command group names that brought us down to this
      command group or command from the top module directory.
    release_track: ReleaseTrack, The release track that we should load.

  Raises:
    LayoutException: if there is a command or group with an illegal name.

  Returns:
    ([groups_info], [commands_info]), The info needed to construct sub groups
    and sub commands.
  """
  location = os.path.join(module_dir, *module_path)
  groups, commands = pkg_resources.ListPackage(location,
                                               extra_extensions=['.yaml'])
  for collection in [groups, commands]:
    for name in collection:
      if re.search('[A-Z]', name):
        raise LayoutException(
            'Commands and groups cannot have capital letters: {0}.'
            .format(name))

  return (_GenerateElementInfo(module_dir, module_path, release_track, groups),
          _GenerateElementInfo(module_dir, module_path, release_track, commands)
         )


def _GenerateElementInfo(module_dir, module_path, release_track, names):
  """Generates the data a group needs to load sub elements.

  Args:
    module_dir: str, The path to the tools directory that this command or
      group lives within.
    module_path: [str], The command group names that brought us down to this
      command group or command from the top module directory.
    release_track: ReleaseTrack, The release track that we should load.
    names: [str], The names of the sub groups or commands the paths are for.

  Returns:
    A list of tuples of (module_dir, module_path, name, release_track) for the
    given names. These terms are that as used by the constructor of
    CommandGroup and Command.
  """
  return [(module_dir,
           module_path + [name],
           name[:-5] if name.endswith('.yaml') else name,
           release_track)
          for name in names]


def LoadCommonType(module_dir, module_path, path, release_track,
                   construction_id, is_command, yaml_command_translator=None):
  """Loads a calliope command or group from a file.

  Args:
    module_dir: str, The path to the tools directory that this command or
      group lives within.
    module_path: [str], The command group names that brought us down to this
      command group or command from the top module directory.
    path: [str], The same as module_path but with the groups named as they
      will be in the CLI.
    release_track: ReleaseTrack, The release track that we should load.
    construction_id: str, A unique identifier for the CLILoader that is
      being constructed.
    is_command: bool, True if we are loading a command, False to load a group.
    yaml_command_translator: YamlCommandTranslator, An instance of a translator
      to use to load the yaml data.

  Raises:
    CommandLoadFailure: If the command is invalid and cannot be loaded.

  Returns:
    The base._Common class for the command or group.
  """
  impl_file = os.path.join(module_dir, *module_path)
  if module_path[-1].endswith('.yaml'):
    if not is_command:
      raise CommandLoadFailure(
          '.'.join(path),
          Exception('Command groups cannot be implemented in yaml'))
    data = yaml.load(pkg_resources.GetData(impl_file))
    common_type = _FromYaml(
        impl_file, path, data, release_track, yaml_command_translator)
  else:
    module = _GetModuleFromPath(impl_file, path, construction_id)
    common_type = _FromModule(
        module.__file__, module.__dict__.values(), release_track,
        is_command=is_command)

  return common_type


def _GetModuleFromPath(impl_file, path, construction_id):
  """Import the module and dig into it to return the namespace we are after.

  Import the module relative to the top level directory.  Then return the
  actual module corresponding to the last bit of the path.

  Args:
    impl_file: str, The path to the file this was loaded from (for error
      reporting).
    path: [str], The same as module_path but with the groups named as they
      will be in the CLI.
    construction_id: str, A unique identifier for the CLILoader that is
      being constructed.

  Returns:
    The imported module.
  """
  # Make sure this module name never collides with any real module name.
  # Use the CLI naming path, so values are always unique.
  name_to_give = '__calliope__command__.{construction_id}.{name}'.format(
      construction_id=construction_id,
      name='.'.join(path).replace('-', '_'))
  try:
    return pkg_resources.GetModuleFromPath(name_to_give, impl_file)
  # pylint:disable=broad-except, We really do want to catch everything here,
  # because if any exceptions make it through for any single command or group
  # file, the whole CLI will not work. Instead, just log whatever it is.
  except Exception as e:
    _, _, exc_traceback = sys.exc_info()
    raise CommandLoadFailure('.'.join(path), e), None, exc_traceback


def _FromModule(mod_file, module_attributes, release_track, is_command):
  """Get the type implementing CommandBase from the module.

  Args:
    mod_file: str, The __file__ attribute of the module resulting from
      importing the file containing a command.
    module_attributes: The __dict__.values() of the module.
    release_track: ReleaseTrack, The release track that we should load from
      this module.
    is_command: bool, True if we are loading a command, False to load a group.

  Returns:
    type, The custom class that implements CommandBase.

  Raises:
    LayoutException: If there is not exactly one type inheriting
        CommonBase.
    ReleaseTrackNotImplementedException: If there is no command or group
      implementation for the request release track.
  """
  commands = []
  groups = []

  # Collect all the registered groups and commands.
  for command_or_group in module_attributes:
    if issubclass(type(command_or_group), type):
      if issubclass(command_or_group, base.Command):
        commands.append(command_or_group)
      elif issubclass(command_or_group, base.Group):
        groups.append(command_or_group)

  if is_command:
    if groups:
      # Ensure that there are no groups if we are expecting a command.
      raise LayoutException(
          'You cannot define groups [{0}] in a command file: [{1}]'
          .format(', '.join([g.__name__ for g in groups]), mod_file))
    if not commands:
      # Make sure we found a command.
      raise LayoutException('No commands defined in file: [{0}]'.format(
          mod_file))
    commands_or_groups = commands
  else:
    # Ensure that there are no commands if we are expecting a group.
    if commands:
      raise LayoutException(
          'You cannot define commands [{0}] in a command group file: [{1}]'
          .format(', '.join([c.__name__ for c in commands]), mod_file))
    if not groups:
      # Make sure we found a group.
      raise LayoutException('No command groups defined in file: [{0}]'.format(
          mod_file))
    commands_or_groups = groups

  return _ExtractReleaseTrackImplementation(
      mod_file, release_track,
      [(c, c.ValidReleaseTracks()) for c in commands_or_groups])


def _FromYaml(impl_file, path, data, release_track, yaml_command_translator):
  """Get the type implementing CommandBase from the module.

  Args:
    impl_file: str, The path to the file this was loaded from (for error
      reporting).
    path: [str], The same as module_path but with the groups named as they
      will be in the CLI.
    data: dict, The loaded yaml data.
    release_track: ReleaseTrack, The release track that we should load from
      this module.
    yaml_command_translator: YamlCommandTranslator, An instance of a translator
      to use to load the yaml data.

  Raises:
    CommandLoadFailure: If the command is invalid and cannot be loaded.

  Returns:
    type, The custom class that implements CommandBase.
  """
  if not yaml_command_translator:
    raise CommandLoadFailure(
        '.'.join(path),
        Exception('No yaml command translator has been registered'))

  implementations = [
      (i, {base.ReleaseTrack.FromId(t) for t in i.get('release_tracks', [])})
      for i in data]
  command_data = _ExtractReleaseTrackImplementation(
      impl_file, release_track, implementations)
  return yaml_command_translator.Translate(path, command_data)


def _ExtractReleaseTrackImplementation(
    impl_file, expected_track, implementations):
  """Validates and extracts the correct implementation of the command or group.

  Args:
    impl_file: str, The path to the file this was loaded from (for error
      reporting).
    expected_track: base.ReleaseTrack, The release track we are trying to load.
    implementations: [(object, {base.ReleaseTrack})], A list of implementations
      to search. Each item is a tuple of an arbitrary object and a list of
      release tracks it is valid for.

  Raises:
    LayoutException: If there is not exactly one type inheriting
        CommonBase.
    ReleaseTrackNotImplementedException: If there is no command or group
      implementation for the request release track.

  Returns:
    object, The single implementation that matches the expected release track.
  """
  # We found a single thing, if it's valid for this track, return it.
  if len(implementations) == 1:
    impl, valid_tracks = implementations[0]
    # If there is a single thing defined, and it does not declare any valid
    # tracks, just assume it is enabled for all tracks that it's parent is.
    if not valid_tracks or expected_track in valid_tracks:
      return impl
    raise ReleaseTrackNotImplementedException(
        'No implementation for release track [{0}] in file: [{1}]'
        .format(expected_track.id, impl_file))

  # There was more than one thing found, make sure there are no conflicts.
  implemented_release_tracks = set()
  for impl, valid_tracks in implementations:
    # When there are multiple definitions, they need to explicitly register
    # their track to keep things sane.
    if not valid_tracks:
      raise LayoutException(
          'Multiple implementations defined in file: [{0}]. Each must '
          'explicitly declare valid release tracks.'.format(impl_file))
    # Make sure no two classes define the same track.
    duplicates = implemented_release_tracks & valid_tracks
    if duplicates:
      raise LayoutException(
          'Multiple definitions for release tracks [{0}] in file: [{1}]'
          .format(', '.join([str(d) for d in duplicates]), impl_file))
    implemented_release_tracks |= valid_tracks

  valid_commands_or_groups = [impl for impl, valid_tracks in implementations
                              if expected_track in valid_tracks]
  # We know there is at most 1 because of the above check.
  if len(valid_commands_or_groups) != 1:
    raise ReleaseTrackNotImplementedException(
        'No implementation for release track [{0}] in file: [{1}]'
        .format(expected_track.id, impl_file))

  return valid_commands_or_groups[0]
