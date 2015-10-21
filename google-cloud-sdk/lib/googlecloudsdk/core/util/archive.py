# Copyright 2015 Google Inc. All Rights Reserved.

"""Set of utilities for dealing with archives."""

import os
import zipfile

try:
  # pylint: disable=unused-import
  # pylint: disable=g-import-not-at-top
  import zlib
  _ZIP_COMPRESSION = zipfile.ZIP_DEFLATED
except ImportError:
  _ZIP_COMPRESSION = zipfile.ZIP_STORED


def MakeZipFromDir(dest_zip_file, src_dir):
  """Similar to shutil.make_archive (which is available in python >=2.7).

  Args:
    dest_zip_file: str, filesystem path to the zip file to be created. Note that
      directory should already exist for destination zip file.
    src_dir: str, filesystem path to the directory to zip up
  """
  zip_file = zipfile.ZipFile(dest_zip_file, 'w', _ZIP_COMPRESSION)
  try:
    for root, _, filelist in os.walk(src_dir):
      # In case this is empty directory.
      path = os.path.normpath(os.path.relpath(root, src_dir))
      if path and path != os.curdir:
        zip_file.write(root, path)
      for f in filelist:
        filename = os.path.normpath(os.path.join(root, f))
        if os.path.isfile(filename):
          arcname = os.path.join(os.path.relpath(root, src_dir), f)
          zip_file.write(filename, arcname)
  finally:
    zip_file.close()
