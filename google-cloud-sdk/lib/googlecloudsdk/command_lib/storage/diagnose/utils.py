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
"""General utility functions for diagnostics."""

import io
from typing import List, Tuple

from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log


def run_gcloud(args: List[str], in_str: str = None) -> Tuple[str, str]:
  """Runs a gcloud command.

  Args:
    args: The arguments to pass to the gcloud command.
    in_str: The input to pass to the gcloud command.

  Returns:
    A tuple containing the stdout and stderr of the command.
  """
  command = execution_utils.ArgsForGcloud()
  command.extend(args)
  out = io.StringIO()
  err = io.StringIO()

  returncode = execution_utils.Exec(
      command,
      no_exit=True,
      out_func=out.write,
      err_func=err.write,
      in_str=in_str,
  )

  stdout = out.getvalue()
  stderr = err.getvalue()

  log.debug('stdout: %s', stdout)
  log.debug('stderr: %s', stderr)

  if returncode != 0 and not stderr:
    stderr = f'gcloud exited with return code {returncode}'
  return (
      stdout if returncode == 0 else None,
      stderr if returncode != 0 else None,
  )
