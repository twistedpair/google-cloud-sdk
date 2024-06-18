# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Download utils for Artifact Registry commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import sys

from apitools.base.py import transfer
from googlecloudsdk.command_lib.artifacts import requests
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.credentials import transports


def Download(dest_path, file_res_name, file_name, allow_overwrite):
  """Downloads a file to a local path."""
  client = requests.GetClient()
  chunksize = 3 * 1024 * 1024

  # call expanduser so that `~` can be used to represent the home directory.
  dest_path = os.path.expanduser(dest_path)

  # Only move the file to the user specified path if overwrites are allowed.
  if os.path.exists(dest_path) and not allow_overwrite:
    log.error('File {} already exists.'.format(dest_path))
    sys.exit(1)

  m = requests.GetMessages()
  request = m.ArtifactregistryProjectsLocationsRepositoriesFilesDownloadRequest(
      name=file_res_name
  )
  with console_io.ProgressBar(
      f'Downloading {file_name}'
  ) as progress_bar:

    def ProgressCallback(_, download):
      """callback function to print the progress of the download."""
      if download.total_size:
        progress = download.progress / download.total_size
        if progress < 1:
          progress_bar.SetProgress(progress)
    d = transfer.Download.FromFile(
        dest_path,
        allow_overwrite,
        chunksize=chunksize,
        progress_callback=ProgressCallback,
    )
    d.bytes_http = transports.GetApitoolsTransport(response_encoding=None)
    try:
      client.projects_locations_repositories_files.Download(request, download=d)
    finally:
      d.stream.close()
