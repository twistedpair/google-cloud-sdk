# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utilities for meta generate-config-commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os.path
import re

from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import files
from mako import runtime
from mako import template


_COMMAND_PATH_COMPONENTS = ('third_party', 'py', 'googlecloudsdk', 'surface')
_SPEC_PATH_COMPONENTS = ('cloud', 'sdk', 'surface_specs', 'gcloud')
_TEST_PATH_COMPONENTS = ('third_party', 'py', 'googlecloudsdk', 'tests', 'unit',
                         'surface')


class CollectionNotFoundError(core_exceptions.Error):
  """Exception for attempts to generate unsupported commands."""

  def __init__(self, collection):
    message = '{collection} collection is not found'.format(
        collection=collection)
    super(CollectionNotFoundError, self).__init__(message)


def WriteConfigYaml(collection,
                    output_root,
                    command_group,
                    release_tracks,
                    enable_overwrites=True):
  """Writes <comand|spec|test> declarative command files for collection.

  Args:
    collection: Name of collection to generate commands for.
    output_root: Path to the root of the directory. Should just be $PWD
      when executing the `meta generate-config-commands` command.
    command_group: Command group to generate the `config export` command for.
      Should be of the form `compute.instances`.
    release_tracks: Release tracks to generate files for.
    enable_overwrites: True to enable overwriting of existing config export
      files.
  """

  collection_info = resources.REGISTRY.GetCollectionInfo(collection)
  file_paths = _BuildFilePaths(output_root, command_group)
  context_dicts = _BuildContexts(collection_info, command_group, release_tracks)
  file_templates = _BuildTemplates()

  for file_path, file_template, context_dict in zip(file_paths, file_templates,
                                                    context_dicts):
    if not os.path.exists(file_path) or enable_overwrites:
      with files.FileWriter(file_path) as f:
        ctx = runtime.Context(f, **context_dict)
        file_template.render_context(ctx)


def _BuildFilePaths(output_root, command_group):
  """Builds filepaths for output spec, command, and test files."""
  command_path_args = (output_root,) + _COMMAND_PATH_COMPONENTS + tuple(
      command_group.split('.')) + ('config', 'export.yaml')
  command_path = os.path.join(*command_path_args)

  surface_spec_path_args = (output_root,) + _SPEC_PATH_COMPONENTS + tuple(
      command_group.split('.')) + ('config', 'export.yaml')
  surface_spec_path = os.path.join(*surface_spec_path_args)

  test_path_args = (output_root,) + _TEST_PATH_COMPONENTS + tuple(
      command_group.split('.')) + ('config_export_test.py',)
  test_path = os.path.join(*test_path_args)
  return [command_path, surface_spec_path, test_path]


def _BuildTemplates():
  """Returns template objects for config export command/spec/test files."""

  dir_name = os.path.dirname(__file__)

  command_template = template.Template(
      filename=os.path.join(dir_name, 'command_templates',
                            'config_export_template.tpl'))
  test_template = template.Template(
      filename=os.path.join(dir_name, 'test_templates',
                            'config_export_template.tpl'))
  surface_spec_template = template.Template(
      filename=os.path.join(dir_name, 'surface_spec_templates',
                            'config_export_template.tpl'))

  return [command_template, surface_spec_template, test_template]


def _BuildContexts(collection_info, command_group, release_tracks):
  """Returns context dicts for config command/xpec/test files."""
  command_dict = _BuildCommandContext(collection_info, release_tracks)
  surface_spec_dict = _BuildSurfaceSpecContext(collection_info, release_tracks)
  test_dict = _BuildTestDictContext(collection_info, command_group)
  return [command_dict, surface_spec_dict, test_dict]


def _BuildCommandContext(collection_info, release_tracks):
  """Makes context dictionary for config export command template rendering."""
  command_dict = {}

  # apiname.collectionNames
  command_dict['collection_name'] = collection_info.name
  # apiname
  command_dict['api_name'] = collection_info.api_name
  # Apiname
  command_dict['capitalized_api_name'] = command_dict['api_name'].capitalize()

  # collection names
  command_dict['plural_resource_name_with_spaces'] = _SplitCollectionOnCapitals(
      _SplitNameAndGetLastIndex(collection_info.name)).lower()

  # collection name
  command_dict['singular_name_with_spaces'] = _MakeSingular(
      command_dict['plural_resource_name_with_spaces'])

  # Collection name
  command_dict['singular_capitalized_name'] = command_dict[
      'singular_name_with_spaces'].capitalize()

  # collection_name
  command_dict['resource_file_name'] = command_dict[
      'singular_name_with_spaces'].replace(' ', '_')

  # my-collection-name
  command_dict['resource_argument_name'] = _MakeResourceArgName(
      collection_info.name)

  # Release tracks
  command_dict['release_tracks'] = _GetReleaseTracks(
      release_tracks)

  # "a" or "an" for correct grammar.
  api_a_or_an = 'a'
  if command_dict['api_name'][0] in 'aeiou':
    api_a_or_an = 'an'
  command_dict['api_a_or_an'] = api_a_or_an

  resource_a_or_an = 'a'
  if command_dict['singular_name_with_spaces'][0] in 'aeiou':
    resource_a_or_an = 'an'
  command_dict['resource_a_or_an'] = resource_a_or_an

  return command_dict


def _BuildSurfaceSpecContext(collection_info, release_tracks):
  """Makes context dictionary for surface spec rendering."""
  surface_spec_dict = {}
  surface_spec_dict['release_tracks'] = _GetReleaseTracks(release_tracks)
  surface_spec_dict['surface_spec_resource_arg'] = _MakeSurfaceSpecResourceArg(
      collection_info)
  return surface_spec_dict


def _BuildTestDictContext(collection_info, command_group):
  """Makes context dictionary for config export est files rendering."""
  test_dict = {}
  test_dict['utf_encoding'] = '-*- coding: utf-8 -*- #'
  resource_arg_flags = _MakeResourceArgFlags(collection_info)
  resource_arg_positional = _MakeResourceArgName(collection_info.name)
  test_dict['test_command_arguments'] = ' '.join(
      [resource_arg_positional, resource_arg_flags])
  test_dict['full_collection_name'] = '.'.join(
      [collection_info.api_name, collection_info.name])
  test_dict['test_command_string'] = _MakeTestCommandString(command_group)
  return test_dict


def _MakeSingular(collection_name):
  """Convert the input collection name to singular form."""
  ending_plurals = [('cies', 'cy'), ('xies', 'xy'), ('ries', 'ry'),
                    ('xes', 'x'), ('esses', 'ess')]
  singular_collection_name = None
  for plural_suffix, replacement_singular in ending_plurals:
    if collection_name.endswith(plural_suffix):
      singular_collection_name = collection_name.replace(
          plural_suffix, replacement_singular)
  if not singular_collection_name:
    singular_collection_name = collection_name[:-1]
  return singular_collection_name


def _SplitCollectionOnCapitals(collection_name, delimiter=' '):
  """Split camel-cased collection names on capital letters."""
  split_with_spaces = delimiter.join(
      re.findall('[a-zA-Z][^A-Z]*', collection_name))
  return split_with_spaces


def _SplitNameAndGetLastIndex(collection_name, delimiter='.'):
  return collection_name.split(delimiter)[-1]


def _GetReleaseTracks(release_tracks):
  """Returns a string representation of release tracks.

  Args:
    release_tracks: API versions to generate release tracks for.
  """
  release_tracks_normalized = '[{}]'.format(', '.join(
      [track.upper() for track in sorted(release_tracks)]))
  return release_tracks_normalized


def _MakeSurfaceSpecResourceArg(collection_info):
  """Makes resource arg name for surface specification context."""
  return _SplitCollectionOnCapitals(
      _MakeSingular(collection_info.name), delimiter='_').upper()


def _MakeTestCommandString(command_group):
  """Makes gcloud command string for test execution."""
  return '{} config export'.format(
      command_group.replace('_', '-').replace('.', ' '))


def _MakeResourceArgName(collection_name):
  resource_arg_name = 'my-{}'.format(_MakeSingular(
      _SplitCollectionOnCapitals(_SplitNameAndGetLastIndex(collection_name),
                                 delimiter='-')).lower())
  return resource_arg_name


def _MakeResourceArgFlags(collection_info):
  """Makes input resource arg flags for config export test file."""
  resource_arg_flags = []
  for param in collection_info.params:
    if (param.lower() not in (_MakeSingular(collection_info.name).lower(),
                              'project', 'name')):
      resource_arg = '--{param}=my-{param}'.format(param=param)
      resource_arg_flags.append(resource_arg)

  return ' '.join(resource_arg_flags)
