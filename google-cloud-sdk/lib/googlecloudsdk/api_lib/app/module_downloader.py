# Copyright 2015 Google Inc. All Rights Reserved.

"""Downloads all the files for an app module from the server."""

import os
import urllib2

from googlecloudsdk.api_lib.app import util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files


class Error(exceptions.Error):
  """Base exception for this module."""
  pass


class InvalidFileListError(Error):
  """Exception for when the server returned invalid file information."""
  pass


class FileDownloadFailedError(Error):
  """Exception for when a file could not be downloaded from the server."""
  pass


class FileWriteFailedError(Error):
  """Exception when a file was unable to be written to disk."""
  pass


class ModuleDownloader(object):
  """A class to download all files from a deployed module."""

  def __init__(self, rpcserver, project, module, version):
    """Constructs a module downloader.

    Args:
      rpcserver: The RPC server to use.
      project: The project id of the module to download.
      module: The module to download.
      version: The version of the module to download.
    """
    self._rpcserver = rpcserver
    self._project = project
    self._module = module
    self._version = version

  def _GetFile(self, full_version, file_id):
    """Gets an individual file from the server.

    This is function is meant to be used in a retry loop and returns values
    that work with RetryWithBackoff.

    Args:
      full_version: str, The full version id of the module that is being
        downloaded.  This comes from the list files API call.
      file_id: int, The ID number of the file you want to download.

    Returns:
      (True, str), If successful, True and the contents of the file.
    """
    try:
      contents = self._rpcserver.Send('/api/files/get', app_id=self._project,
                                      version=full_version, id=file_id)
      return True, contents
    except urllib2.HTTPError as exc:
      # Retry on "Server busy" errors.  Relay all other exception
      # types as-is.
      if exc.code == 503:
        return False, exc
      else:
        raise

  def GetFileList(self):
    """Gets the file listing for the module from the server.

    Returns:
      (str, [str]), The full version of the module and a list files that it
      contains.  The files are in the format ID|SIZE|PATH.

    Raises:
      InvalidFileListError: If the server response is invalid.
    """
    log.status.Print('Fetching file list from server...')
    url_args = {'app_id': self._project,
                'module': self._module,
                'version_match': self._version
               }
    result = self._rpcserver.Send('/api/files/list', **url_args)
    lines = result.splitlines()
    if not lines:
      raise InvalidFileListError('Invalid response from server: empty')

    full_version = lines[0]
    file_lines = lines[1:]
    return (full_version, file_lines)

  def Download(self, full_version, file_lines, output_dir,
               progress_callback=None):
    """Downloads all the files in the module.

    Args:
      full_version: str, The full version id of the module that is being
        downloaded.  This comes from the list files API call.
      file_lines: [str], The list of files to download.  The files are in the
        format ID|SIZE|PATH.
      output_dir: str, The path to download the files to.
      progress_callback: console_io.ProgressTracker.SetProgress, A function
        reference to use for updating progress if set.

    Raises:
      InvalidFileListError: If the file list from the server is invalid.
      FileDownloadFailedError: If download an individual file failed.
      FileWriteFailedError: If the file contents could not be written to disk.
    """
    log.info('Fetching files...')
    # Use a float because of the progress tracker.
    num_files = float(len(file_lines))
    current_file_num = 0

    for line in file_lines:
      parts = line.split('|', 2)
      if len(parts) != 3:
        raise InvalidFileListError(
            'Invalid response from server: expecting [<id>|<size>|<path>], '
            'found: [{0}]'.format(line))
      file_id, size_str, path = parts
      current_file_num += 1
      log.debug('Found file: [%d / %d] %s', current_file_num, num_files, path)
      try:
        size = int(size_str)
      except ValueError:
        raise InvalidFileListError(
            'Invalid file list entry from server: invalid size: [{0}]'
            .format(size_str))

      def PrintRetryMessage(msg, delay):
        log.status.Print('{0}.  Will try again in {1} seconds.'
                         .format(msg, delay))

      # pylint: disable=cell-var-from-loop, This closure doesn't get used
      # outside the context of the loop iteration.
      success, contents = util.RetryWithBackoff(
          lambda: self._GetFile(full_version, file_id), PrintRetryMessage)
      if not success:
        raise FileDownloadFailedError('Unable to download file: [{0}]'
                                      .format(path))
      if len(contents) != size:
        raise FileDownloadFailedError(
            'File [{file}]: server listed as [{expected}] bytes but served '
            '[{actual}] bytes.'.format(file=path, expected=size,
                                       actual=len(contents)))

      full_path = os.path.join(output_dir, path)
      if os.path.exists(full_path):
        raise FileWriteFailedError(
            'Unable to create file [{0}]: path conflicts with an existing file '
            'or directory'.format(path))

      full_dir = os.path.dirname(full_path)
      try:
        files.MakeDir(full_dir)
      except OSError as e:
        raise FileWriteFailedError('Failed to create directory [{0}]: {1}'
                                   .format(full_dir, e))
      try:
        with open(full_path, 'wb') as f:
          f.write(contents)
      except IOError as e:
        raise FileWriteFailedError('Failed to write to file [{0}]: {1}'
                                   .format(full_path, e))

      if progress_callback:
        progress_callback(current_file_num / num_files)
