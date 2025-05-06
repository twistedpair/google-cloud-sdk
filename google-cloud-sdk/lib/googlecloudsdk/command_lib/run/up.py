# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Wrapper for cloud-run-up binary."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.util.anthos import binary_operations
from googlecloudsdk.core import log


MISSING_BINARY = (
    'Could not locate Cloud Run executable run-compsose'
    ' on the system PATH. '
    'Please ensure gcloud run up component is properly '
    'installed. '
    'See https://cloud.google.com/sdk/docs/components for '
    'more details.'
)


class RunComposeWrapper(binary_operations.StreamingBinaryBackedOperation):
  """Binary operation wrapper for run-compose commands."""

  def __init__(self, **kwargs):
    super(RunComposeWrapper, self).__init__(
        binary='run-compose',
        custom_errors={'MISSING_EXEC': MISSING_BINARY},
        install_if_missing=True,
        std_err_func=StreamErrHandler,
        **kwargs
    )

  # Function required by StreamingBinaryBackedOperation to map command line args
  # from gcloud to the underlying component.
  def _ParseArgsForCommand(
      self, compose_file=None, repo=None, debug=False, dry_run=False, **kwargs
  ):
    del kwargs
    exec_args = ['up']
    if compose_file:
      exec_args += [compose_file]
    exec_args += ['--repo', repo]
    if debug:
      exec_args.append('--debug')
    if dry_run:
      exec_args.append('--dry-run')
    return exec_args


def StreamErrHandler(result_holder, capture_output=False):
  """Customized processing for streaming stderr from subprocess."""

  del result_holder, capture_output

  def HandleStdErr(line):
    if line:
      log.status.Print(line)

  return HandleStdErr
