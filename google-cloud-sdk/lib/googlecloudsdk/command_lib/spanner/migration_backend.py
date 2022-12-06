# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Spanner migration library functions and utilities for the harbourbridge binary."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import copy
import os

from googlecloudsdk.command_lib.util.anthos import binary_operations
from googlecloudsdk.core import exceptions as c_except


def GetEnvArgsForCommand(extra_vars=None, exclude_vars=None):
  """Return an env dict to be passed on command invocation."""
  env = copy.deepcopy(os.environ)
  if extra_vars:
    env.update(extra_vars)
  if exclude_vars:
    for k in exclude_vars:
      env.pop(k)
  return env


class SpannerMigrationException(c_except.Error):
  """Base Exception for any errors raised by gcloud spanner migration surface."""


class HarbourbridgeWrapper(binary_operations.StreamingBinaryBackedOperation):
  """Binary operation wrapper for harbourbridge commands."""

  def __init__(self, **kwargs):
    super(HarbourbridgeWrapper, self).__init__(
        binary='harbourbridge', install_if_missing=True, **kwargs)

  def _ParseSchemaArgs(self,
                       source,
                       prefix=None,
                       source_profile=None,
                       target=None,
                       target_profile=None,
                       dry_run=False,
                       log_level=None,
                       **kwargs):
    """"Parse args for the schema command."""
    del kwargs
    exec_args = ['schema']
    if source:
      exec_args.extend(['--source', source])
    if prefix:
      exec_args.extend(['--prefix', prefix])
    if source_profile:
      exec_args.extend(['--source-profile', source_profile])
    if target:
      exec_args.extend(['--target', target])
    if target_profile:
      exec_args.extend(['--target-profile', target_profile])
    if dry_run:
      exec_args.append('--dry-run')
    if log_level:
      exec_args.extend(['--log-level', log_level])

    return exec_args

  def _ParseDataArgs(self,
                     source,
                     session,
                     prefix=None,
                     skip_foreign_keys=False,
                     source_profile=None,
                     target=None,
                     target_profile=None,
                     write_limit=None,
                     dry_run=False,
                     log_level=None,
                     **kwargs):
    """"Parse args for the data command."""
    del kwargs
    exec_args = ['data']
    if source:
      exec_args.extend(['--source', source])
    if session:
      exec_args.extend(['--session', session])
    if prefix:
      exec_args.extend(['--prefix', prefix])
    if skip_foreign_keys:
      exec_args.append('--skip-foreign-keys')
    if source_profile:
      exec_args.extend(['--source-profile', source_profile])
    if target:
      exec_args.extend(['--target', target])
    if target_profile:
      exec_args.extend(['--target-profile', target_profile])
    if write_limit:
      exec_args.extend(['--write-limit', write_limit])
    if dry_run:
      exec_args.append('--dry-run')
    if log_level:
      exec_args.extend(['--log-level', log_level])
    return exec_args

  def _ParseSchemaAndDataArgs(self,
                              source,
                              prefix=None,
                              skip_foreign_keys=False,
                              source_profile=None,
                              target=None,
                              target_profile=None,
                              write_limit=None,
                              dry_run=False,
                              log_level=None,
                              **kwargs):
    """"Parse args for the schema-and-data command."""
    del kwargs
    exec_args = ['schema-and-data']
    if source:
      exec_args.extend(['--source', source])
    if prefix:
      exec_args.extend(['--prefix', prefix])
    if skip_foreign_keys:
      exec_args.append('--skip-foreign-keys')
    if source_profile:
      exec_args.extend(['--source-profile', source_profile])
    if target:
      exec_args.extend(['--target', target])
    if target_profile:
      exec_args.extend(['--target-profile', target_profile])
    if write_limit:
      exec_args.extend(['--write-limit', write_limit])
    if dry_run:
      exec_args.append('--dry-run')
    if log_level:
      exec_args.extend(['--log-level', log_level])
    return exec_args

  def _ParseArgsForCommand(self, command, **kwargs):
    """Call the parser corresponding to the command."""
    if command == 'schema':
      return self._ParseSchemaArgs(**kwargs)
    elif command == 'data':
      return self._ParseDataArgs(**kwargs)
    elif command == 'schema-and-data':
      return self._ParseSchemaAndDataArgs(**kwargs)
    elif command == 'web':
      return ['web']
    else:
      raise binary_operations.InvalidOperationForBinary(
          'Invalid Operation [{}] for harbourbridge'.format(command))
