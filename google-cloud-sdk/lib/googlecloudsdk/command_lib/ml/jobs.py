# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Utilities for job submission preparation."""
import cStringIO
import os
import shutil
import sys

from googlecloudsdk.command_lib.ml import flags
from googlecloudsdk.command_lib.ml import uploads
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files


DEFAULT_SETUP_FILE = """\
from setuptools import setup

if __name__ == '__main__':
    setup(name='{package_name}', packages=['{package_name}'])
"""
_NO_PACKAGES_ERROR_MSG = (
    'If --package-path is not specified, at least '
    'one tar.gz archive must be specified with --packages')
_SETUP_FAILURE_ERROR_MSG_GENERATED = """
    Packaging of user python code failed with message:
      {message}
    Try manually writing a setup.py file at your package root
    and rerunning the command
"""
_SETUP_FAILURE_ERROR_MSG_EXISTING = """
    Packing of user python code failed with message:
      {message}
    Try manually building your python code by running:
      python setup.py sdist
    using your existing setup.py file, and providing the
    output via the packages flag, e.g. --packages ./dist/*
"""
_NO_EXECUTABLE_ERROR_MSG = """
    No python executable found on path, a python executable,
    with setuptools installed on the PYTHON_PATH is required for
    building cloud ml training jobs
"""
_NO_INIT_ERROR_MSG = """\
[{}] is not a valid Python package because it does not contain an \
`__init__.py` file. Please create one and try again.\
"""


class SetupFailureError(exceptions.Error):
  pass


def RunSetupAndUpload(packages, staging_bucket, package_path, job_name):
  """Runs setup.py and uploads the resulting tar.gz archives.

  Copies the source directory to a temporary directory and uses
  _RunSetup (which runs setuptools.sandbox.run_setup) to generate or run
  setup.py from the temporary directory. Uploads the resulting tar.gz
  archives and any extra from package_path.
  Args:
    packages: [str]. Path to extra tar.gz packages to upload.
    staging_bucket: storage_util.BucketReference. Bucket to which archives are
      uploaded.
    package_path: str. Relative path to source directory to be built.
    job_name: str. Name of the Cloud ML Job. Used to prefix uploaded packages.

  Returns:
      [str]. Fully qualified gcs paths from uploaded packages.

  Raises:
    ValueError: If packages is empty, and building package_path produces no
    tar archives.
    SetupFailureError: If the provided package path does not contain
      `__init__.py`.
    ArgumentError: if no packages were found in the given path.
  """
  def _MakePairs(paths):
    """Return tuples corresponding to the files and their upload paths."""
    return [(path, os.path.basename(path)) for path in paths]

  if package_path:
    if not os.path.exists(os.path.join(package_path, '__init__.py')):
      # We could drop `__init__.py` in here, but it's pretty likely that this
      # indicates an incorrect directory or some bigger problem and we don't
      # want to obscure that.
      #
      # Note that we could more strictly validate here by checking each package
      # in the `--module-name` argument, but this should catch most issues.
      raise SetupFailureError(_NO_INIT_ERROR_MSG.format(package_path))
    with files.TemporaryDirectory() as temp_dir:
      setup_dir, package_name = os.path.split(os.path.abspath(package_path))
      dest_dir = os.path.join(temp_dir, 'dest')
      log.debug(
          ('Copying local source tree from'
           '[{setup_dir}] to [{temp_dir}]').format(
               setup_dir=setup_dir, temp_dir=dest_dir))
      shutil.copytree(setup_dir, dest_dir)
      package_paths = _RunSetup(dest_dir, package_name) + packages
      if not package_paths:
        raise flags.ArgumentError(_NO_PACKAGES_ERROR_MSG)
      return uploads.UploadFiles(
          _MakePairs(package_paths),
          staging_bucket,
          job_name)
  else:
    if not packages:
      raise flags.ArgumentError(_NO_PACKAGES_ERROR_MSG)
    return uploads.UploadFiles(_MakePairs(packages), staging_bucket, job_name)


def _RunSetup(setup_dir, package_name):
  """Runs setup.py in specified setup_dir.

  Ensures setup.py exists in the necessary directory and generates a
  setup.py if no such file exists.
  Args:
    setup_dir: str. Absolute path to the parent of the package root.
    package_name: str. Used as the package name and directory
      in the event that a setup.py must be generated.
  Returns:
    [str]. The local path to tar.gz archives generated by running setup.py.
  Raises:
    SetupFailureError: If the setup.py file fails to successfully build.
  """
  setup_path = os.path.join(setup_dir, 'setup.py')
  log.debug('Looking for setup.py file at [{0}]'.format(setup_path))
  generated = False
  if not os.path.isfile(setup_path):
    generated = True
    with open(setup_path, 'w') as setup_file:
      setup_contents = DEFAULT_SETUP_FILE.format(package_name=package_name)
      log.info('Generating temporary setup.py file: \n[{0}]'.format(
          setup_contents))
      setup_file.write(setup_contents)
  else:
    log.info('Using existing setup.py file at [{0}]'.format(setup_path))

  out = cStringIO.StringIO()
  if not sys.executable:
    raise SetupFailureError(_NO_EXECUTABLE_ERROR_MSG)
  args = [sys.executable, 'setup.py', 'sdist', '--dist-dir=dist']
  return_code = execution_utils.Exec(
      args,
      no_exit=True,
      out_func=out.write,
      err_func=out.write,
      cwd=setup_dir)
  if return_code:
    if generated:
      msg = _SETUP_FAILURE_ERROR_MSG_GENERATED.format(
          message=out.getvalue())
    else:
      msg = _SETUP_FAILURE_ERROR_MSG_EXISTING.format(
          message=out.getvalue())
    raise SetupFailureError(msg)

  dist_dir = os.path.join(setup_dir, 'dist')
  local_paths = [os.path.join(dist_dir, rel_file)
                 for rel_file in os.listdir(dist_dir)]
  log.debug('Python packaging resulted in [{0}]'.format(str(local_paths)))
  return local_paths
