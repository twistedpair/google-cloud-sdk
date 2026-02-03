# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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
"""Utilities for building Python environments for declarative pipelines."""

import contextlib

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files


@contextlib.contextmanager
def _temp_build_dir(work_dir):
  """Context manager for a temporary build directory."""
  build_root = work_dir / 'temp_build_libs'
  try:
    files.RmTree(build_root)
  except FileNotFoundError:
    pass
  build_root.mkdir(parents=True, exist_ok=True)
  try:
    yield build_root
  finally:
    try:
      files.RmTree(build_root)
    except FileNotFoundError:
      pass


def build_env_local(
    subprocess_mod,
    work_dir,
    requirements_file_path,
    output_tar_gz_path,
    python_version,
):
  """Builds dependencies.tar.gz locally using uv and venv-pack.

  Args:
    subprocess_mod: The subprocess module or mock.
    work_dir: The working directory as a pathlib.Path object.
    requirements_file_path: Path to requirements.txt file.
    output_tar_gz_path: The path for the output tar.gz file.
    python_version: The target Python version for pip install.
  """

  with _temp_build_dir(work_dir) as build_root:
    venv_path = build_root / 'deployment_env'
    output_path = str(output_tar_gz_path)

    try:
      # 1. Create the virtual environment using uv
      log.info('Creating virtual environment with uv...')
      subprocess_mod.check_call(
          ['uv', 'venv', str(venv_path), '--python', python_version]
      )

      # 2. Install requirements using uv pip
      log.info('Installing requirements using uv pip...')
      pip_install_cmd = [
          'uv',
          'pip',
          'install',
          '--python',
          str(venv_path),
          '-r',
          str(requirements_file_path),
          '--no-cache',
          '--link-mode=copy',
      ]

      subprocess_mod.check_call(pip_install_cmd)

      # 3. Pack the environment using venv-pack
      log.info('Packing environment with venv-pack...')
      subprocess_mod.check_call([
          'uvx',
          'venv-pack',
          '-p',
          str(venv_path),
          '-o',
          output_path,
          '--force',
      ])

    except subprocess_mod.CalledProcessError as e:
      log.error('Command failed: %s', e)
      raise exceptions.ToolException(
          'Local build with uv failed. Ensure uv is installed in your PATH.'
      ) from e
