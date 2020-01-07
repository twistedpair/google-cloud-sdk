# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Anthos command library functions and utilities for the anthoscli binary."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from googlecloudsdk.command_lib.anthos.common import messages
from googlecloudsdk.command_lib.util.anthos import binary_operations

import six


def RelativePkgPathFromFullPath(path):
  """Splits full path into relative(basename) path and parent dir."""
  normpath = os.path.normpath(path)
  rel_path = os.path.basename(normpath)
  parent_dir = os.path.dirname(normpath) or rel_path
  return  rel_path, parent_dir


class AnthosCliWrapper(binary_operations.BinaryBackedOperation):
  """Binary operation wrapper for anthoscli commands."""

  _ENV_ARGS = {'COBRA_SILENCE_USAGE': 'true'}

  def __init__(self, **kwargs):
    custom_errors = {
        'MISSING_EXEC': messages.MISSING_BINARY.format(binary='anthoscli')
    }
    super(AnthosCliWrapper, self).__init__(binary='anthoscli',
                                           custom_errors=custom_errors,
                                           **kwargs)

  def _ParseGetArgs(self, repo_uri, local_dest, file_pattern=None, **kwargs):
    del kwargs  # Not Used Here
    exec_args = ['get', repo_uri, local_dest]

    if file_pattern:
      exec_args.extend(['--pattern', file_pattern])

    return exec_args

  def _ParseUpdateArgs(self, local_dir, repo_uri=None, strategy=None,
                       dry_run=False, verbose=False, **kwargs):
    del kwargs  # Not Used here

    exec_args = ['update', local_dir]
    if repo_uri:
      exec_args.extend(['--repo', repo_uri])

    if dry_run:
      exec_args.append('--dry-run')

    if strategy:
      exec_args.extend(['--strategy', strategy])

    if verbose:
      exec_args.append('--verbose')

    return  exec_args

  def _ParseDescribeArgs(self, local_dir, **kwargs):
    del kwargs  # Not Used here
    return  ['desc', local_dir]

  def _ParseTags(self, tags):
    return ','.join(['{}={}'.format(x, y) for x, y in six.iteritems(tags)])

  def _ParseInitArgs(self, local_dir, description=None, name=None,
                     tags=None, info_url=None, **kwargs):
    del kwargs  # Not Used here
    package_path = local_dir

    if not package_path.endswith('/'):
      package_path += '/'
    exec_args = ['init', package_path]

    if description:
      exec_args.extend(['--description', description])
    if name:
      exec_args.extend(['--name', name])
    if tags:
      exec_args.extend(['--tag', self._ParseTags(tags)])

    if info_url:
      exec_args.extend(['--url', info_url])

    return  exec_args

  def _ParseApplyArgs(self, apply_dir, project, **kwargs):
    del kwargs  # Not Used Here
    exec_args = ['apply', '-f', apply_dir, '--project', project]

    return exec_args

  def _ParseArgsForCommand(self, command, **kwargs):
    kwargs['env'] = self._ENV_ARGS
    if command == 'get':
      return self._ParseGetArgs(**kwargs)
    if command == 'update':
      return self._ParseUpdateArgs(**kwargs)
    if command == 'desc':
      return self._ParseDescribeArgs(**kwargs)
    if command == 'init':
      return self._ParseInitArgs(**kwargs)
    if command == 'apply':
      return self._ParseApplyArgs(**kwargs)

    raise binary_operations.InvalidOperationForBinary(
        'Invalid Operation [{}] for anthoscli'.format(command))
