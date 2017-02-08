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
"""Utilities for job submission preparation.

The main entry point is UploadPythonPackages, which takes in parameters derived
from the command line arguments and returns a list of URLs to be given to the
Cloud ML API. See its docstring for details.
"""
import collections
import cStringIO
import os
import sys
import textwrap

from googlecloudsdk.api_lib.storage import storage_util
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
    'If `--package-path` is not specified, at least one Python package '
    'must be specified via `--packages`.')


class UploadFailureError(exceptions.Error):
  """Generic error with the packaging/upload process."""
  pass


class SetuptoolsFailedError(UploadFailureError):
  """Error indicating that setuptools itself failed."""

  def __init__(self, output, generated):
    msg = ('Packaging of user Python code failed with message:\n\n'
           '{}\n\n').format(output)
    if generated:
      msg += ('Try manually writing a setup.py file at your package root and '
              'rerunning the command.')
    else:
      msg += ('Try manually building your Python code by running:\n'
              '  $ python setup.py sdist\n'
              'and providing the output via the `--packages` flag (for '
              'example, `--packages dist/package.tar.gz,dist/package2.whl)`')
    super(SetuptoolsFailedError, self).__init__(msg)


class SysExecutableMissingError(UploadFailureError):
  """Error indicating that sys.executable was empty."""

  def __init__(self):
    super(SysExecutableMissingError, self).__init__(textwrap.dedent("""\
        No Python executable found on path. A Python executable with setuptools
        installed on the PYTHONPATH is required for building Cloud ML training
        jobs.
        """))


class MissingInitError(UploadFailureError):
  """Error indicating that the package to build had no __init__.py file."""

  def __init__(self, package_dir):
    super(MissingInitError, self).__init__(textwrap.dedent("""\
        [{}] is not a valid Python package because it does not contain an \
        `__init__.py` file. Please create one and try again.
        """).format(package_dir))


class UncopyablePackageError(UploadFailureError):
  """Error with copying: the source contains its destination."""

  def __init__(self, source_dir, temp_dir):
    super(UncopyablePackageError, self).__init__(textwrap.dedent("""\
        Cannot copy directory since temporary directory [{}] is inside of
        source directory [{}].
        """.format(source_dir, temp_dir)))


class DuplicateEntriesError(UploadFailureError):
  """Error indicating that multiple files with the same name were provided."""

  def __init__(self, duplicates):
    super(DuplicateEntriesError, self).__init__(
        'Cannot upload multiple packages with the same filename: [{}]'.format(
            ', '.join(duplicates)))


class NoStagingLocationError(UploadFailureError):
  """No staging location was provided but one was required."""


def _CopyIfNotWritable(source_dir, temp_dir):
  """Returns a writable directory with the same contents as source_dir.

  If source_dir is writable, it is used. Otherwise, a directory 'dest' inside of
  temp_dir is used.

  Args:
    source_dir: str, the directory to (potentially) copy
    temp_dir: str, the path to a writable temporary directory in which to store
      any copied code.

  Returns:
    str, the path to a writable directory with the same contents as source_dir
      (i.e. source_dir, if it's writable, or a copy otherwise).

  Raises:
    UploadFailureError: if the command exits non-zero.
  """
  if files.HasWriteAccessInDir(source_dir):
    return source_dir

  if files.IsDirAncestorOf(source_dir, temp_dir):
    raise UncopyablePackageError(source_dir, temp_dir)

  dest_dir = os.path.join(temp_dir, 'dest')
  log.debug('Copying local source tree from [%s] to [%s]', source_dir, dest_dir)
  files.CopyTree(source_dir, dest_dir)
  return dest_dir


def _GenerateSetupPyIfNeeded(setup_py_path, package_name):
  """Generates a temporary setup.py file if there is none at the given path.

  Args:
    setup_py_path: str, a path to the expected setup.py location.
    package_name: str, the name of the Python package for which to write a
      setup.py file (used in the generated file contents).

  Returns:
    bool, whether the setup.py file was generated.
  """
  log.debug('Looking for setup.py file at [%s]', setup_py_path)
  if os.path.isfile(setup_py_path):
    log.info('Using existing setup.py file at [%s]', setup_py_path)
    return False

  setup_contents = DEFAULT_SETUP_FILE.format(package_name=package_name)
  log.info('Generating temporary setup.py file:\n%s', setup_contents)
  with open(setup_py_path, 'w') as setup_file:
    setup_file.write(setup_contents)
  return True


def _RunSetupTools(package_root, setup_py_path, output_dir):
  """Executes the setuptools `sdist` command.

  Specifically, runs `python setup.py sdist` (with the full path to `setup.py`
  given by setup_py_path) with arguments to put the final output in output_dir
  and all possible temporary files in a temporary directory. package_root is
  used as the working directory.

  package_root must be writable, or setuptools will fail (there are
  temporary files from setuptools that get put in the CWD).

  Args:
    package_root: str, the directory containing the package (that is, the
      *parent* of the package itself).
    setup_py_path: str, the path to the `setup.py` file to execute.
    output_dir: str, path to a directory in which the built packages should be
      created.

  Returns:
    list of str, the full paths to the generated packages.

  Raises:
    SysExecutableMissingError: if sys.executable is None
    RuntimeError: if the execution of setuptools exited non-zero.
  """
  if not sys.executable:
    raise SysExecutableMissingError()

  # We could just include the 'sdist' command and its flags here, but we want
  # to avoid leaving artifacts in the setup directory. That's what the
  # 'egg_info' and 'build' options do (these are both invoked as subcommands
  # of 'sdist').
  # Unfortunately, there doesn't seem to be any easy way to move *all*
  # temporary files out of the current directory, so we'll fail here if we
  # can't write to it.
  with files.TemporaryDirectory() as temp_dir:
    args = [sys.executable, setup_py_path,
            'egg_info', '--egg-base', temp_dir,
            'build', '--build-base', temp_dir, '--build-temp', temp_dir,
            'sdist', '--dist-dir', output_dir]
    out = cStringIO.StringIO()
    if execution_utils.Exec(args, no_exit=True, out_func=out.write,
                            err_func=out.write, cwd=package_root):
      raise RuntimeError(out.getvalue())

  local_paths = [os.path.join(output_dir, rel_file)
                 for rel_file in os.listdir(output_dir)]
  log.debug('Python packaging resulted in [%s]', ', '.join(local_paths))
  return local_paths


def BuildPackages(package_path, output_dir):
  """Builds Python packages from the given package source.

  That is, builds Python packages from the code in package_path, using its
  parent directory (the 'package root') as its context using the setuptools
  `sdist` command.

  If there is a `setup.py` file in the package root, use that. Otherwise,
  use a simple, temporary one made for this package.

  We try to be as unobstrustive as possible (see _RunSetupTools for details):

  - setuptools writes some files to the package root--we move as many temporary
    generated files out of the package root as possible
  - the final output gets written to output_dir
  - any temporary setup.py file is written outside of the package root.
  - if the current directory isn't writable, we silenly make a temporary copy

  Args:
    package_path: str. Path to the package. This should be the path to
      the directory containing the Python code to be built, *not* its parent
      (which optionally contains setup.py and other metadata).
    output_dir: str, path to a long-lived directory in which the built packages
      should be created.

  Returns:
    list of str. The full local path to all built Python packages.

  Raises:
    SetuptoolsFailedError: If the setup.py file fails to successfully build.
    MissingInitError: If the package doesn't contain an `__init__.py` file.
  """
  package_path = os.path.abspath(package_path)
  with files.TemporaryDirectory() as temp_dir:
    package_root = _CopyIfNotWritable(os.path.dirname(package_path), temp_dir)
    if not os.path.exists(os.path.join(package_path, '__init__.py')):
      # We could drop `__init__.py` in here, but it's pretty likely that this
      # indicates an incorrect directory or some bigger problem and we don't
      # want to obscure that.
      #
      # Note that we could more strictly validate here by checking each package
      # in the `--module-name` argument, but this should catch most issues.
      raise MissingInitError(package_path)

    setup_py_path = os.path.join(package_root, 'setup.py')
    package_name = os.path.basename(package_path)
    generated = _GenerateSetupPyIfNeeded(setup_py_path, package_name)
    try:
      return _RunSetupTools(package_root, setup_py_path, output_dir)
    except RuntimeError as err:
      raise SetuptoolsFailedError(str(err), generated)
    finally:
      if generated:
        # For some reason, this artifact gets generated in the package root by
        # setuptools, even after setting PYTHONDONTWRITEBYTECODE or running
        # `python setup.py clean --all`. It's weird to leave someone a .pyc for
        # a file they never knew they had, so we clean it up.
        pyc_file = os.path.join(package_root, 'setup.pyc')
        for path in (setup_py_path, pyc_file):
          try:
            os.unlink(path)
          except OSError:
            log.debug(
                "Couldn't remove file [%s] (it may never have been created).",
                pyc_file)


def _UploadFilesByPath(paths, staging_location):
  """Uploads files after validating and transforming input type."""
  if not staging_location:
    raise NoStagingLocationError()
  counter = collections.Counter(map(os.path.basename, paths))
  duplicates = [name for name, count in counter.iteritems() if count > 1]
  if duplicates:
    raise DuplicateEntriesError(duplicates)

  upload_pairs = [(path, os.path.basename(path)) for path in paths]
  return uploads.UploadFiles(upload_pairs, staging_location.bucket_ref,
                             staging_location.name)


def UploadPythonPackages(packages=(), package_path=None, staging_location=None):
  """Uploads Python packages (if necessary), building them as-specified.

  A Cloud ML job needs one or more Python packages to run. These Python packages
  can be specified in one of three ways:

    1. As a path to a local, pre-built Python package file.
    2. As a path to a Cloud Storage-hosted, pre-built Python package file (paths
       beginning with 'gs://').
    3. As a local Python source tree (the `--package-path` flag).

  In case 1, we upload the local files to Cloud Storage[1] and provide their
  paths. These can then be given to the Cloud ML API, which can fetch these
  files.

  In case 2, we don't need to do anything. We can just send these paths directly
  to the Cloud ML API.

  In case 3, we perform a build using setuptools[2], and upload the resulting
  artifacts to Cloud Storage[1]. The paths to these artifacts can be given to
  the Cloud ML API. See the `BuildPackages` method.

  These methods of specifying Python packages may be combined.


  [1] Uploads are to a specially-prefixed location in a user-provided Cloud
  Storage staging bucket. If the user provides bucket `gs://my-bucket/`, a file
  `package.tar.gz` is uploaded to
  `gs://my-bucket/<job name>/<checksum>/package.tar.gz`.

  [2] setuptools must be installed on the local user system.

  Args:
    packages: list of str. Path to extra tar.gz packages to upload, if any. If
      empty, a package_path must be provided.
    package_path: str. Relative path to source directory to be built, if any. If
      omitted, one or more packages must be provided.
    staging_location: storage_util.ObjectReference. Cloud Storage prefix to
      which archives are uploaded. Not necessary if only remote packages are
      given.

  Returns:
    list of str. Fully qualified Cloud Storage URLs (`gs://..`) from uploaded
      packages.

  Raises:
    ValueError: If packages is empty, and building package_path produces no
      tar archives.
    SetuptoolsFailedError: If the setup.py file fails to successfully build.
    MissingInitError: If the package doesn't contain an `__init__.py` file.
    DuplicateEntriesError: If multiple files with the same name were provided.
    ArgumentError: if no packages were found in the given path or no
      staging_location was but uploads were required.
  """
  remote_paths = []
  local_paths = []
  for package in packages:
    if storage_util.ObjectReference.IsStorageUrl(package):
      remote_paths.append(package)
    else:
      local_paths.append(package)

  if package_path:
    with files.TemporaryDirectory() as temp_dir:
      local_paths.extend(BuildPackages(package_path,
                                       os.path.join(temp_dir, 'output')))
      remote_paths.extend(_UploadFilesByPath(local_paths, staging_location))
  elif local_paths:
    # Can't combine this with above because above requires the temporary
    # directory to still be around
    remote_paths.extend(_UploadFilesByPath(local_paths, staging_location))

  if not remote_paths:
    raise flags.ArgumentError(_NO_PACKAGES_ERROR_MSG)
  return remote_paths


def GetStagingLocation(job_id=None, staging_bucket=None, job_dir=None):
  """Get the appropriate staging location for the job given the arguments."""
  staging_location = None
  if staging_bucket:
    staging_location = storage_util.ObjectReference(staging_bucket,
                                                    job_id)
  elif job_dir:
    staging_location = storage_util.ObjectReference(
        job_dir.bucket_ref, '/'.join((job_dir.name.rstrip('/'), 'packages')))
  return staging_location
