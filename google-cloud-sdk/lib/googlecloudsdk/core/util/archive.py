# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Set of utilities for dealing with archives."""

import os
import re
import zipfile

try:
  # pylint: disable=unused-import
  # pylint: disable=g-import-not-at-top
  import zlib
  _ZIP_COMPRESSION = zipfile.ZIP_DEFLATED
except ImportError:
  _ZIP_COMPRESSION = zipfile.ZIP_STORED


def MakeZipFromDir(dest_zip_file, src_dir, skip_file_regex=None):
  """Similar to shutil.make_archive (which is available in python >=2.7).

  Examples:
    Filesystem:
    /tmp/a/
    /tmp/b/B

    >>> MakeZipFromDir('my.zip', '/tmp')
    Creates zip with content:
    a/
    b/B

    >>> MakeZipFromDir('my.zip', '/tmp', 'b.*')
    Creates zip with content:
    a/

    >>> MakeZipFromDir('my.zip', '/tmp', 'b/.*')
    Creates zip with content:
    a/
    b/

  Note this is caller responsibility to use appropriate platform-dependent
  path separator.

  Note filenames containing path separator are supported, but specifying
  skip_file_regex might be slightly more tricky.

  Args:
    dest_zip_file: str, filesystem path to the zip file to be created. Note that
      directory should already exist for destination zip file.
    src_dir: str, filesystem path to the directory to zip up
    skip_file_regex: regex, files and directories with names relative to src_dir
      matching this pattern will be excluded from the archive.
  """
  def IsSkipped(relative_name):
    """Decides if given file or directory should be skipped."""
    if skip_file_regex is None:
      return False
    return re.match(skip_file_regex, relative_name) is not None

  zip_file = zipfile.ZipFile(dest_zip_file, 'w', _ZIP_COMPRESSION)
  try:
    for root, _, filelist in os.walk(src_dir):
      # In case this is empty directory.
      path = os.path.normpath(os.path.relpath(root, src_dir))
      if IsSkipped(path):
        continue
      if path and path != os.curdir:
        zip_file.write(root, path)
      for f in filelist:
        filename = os.path.normpath(os.path.join(root, f))
        relpath = os.path.relpath(filename, src_dir)
        if IsSkipped(relpath):
          continue
        if os.path.isfile(filename):
          zip_file.write(filename, relpath)
  finally:
    zip_file.close()
