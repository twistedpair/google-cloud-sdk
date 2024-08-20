# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Direct Connectivity Diagnostic."""

import os
import tempfile
import uuid

from googlecloudsdk.command_lib.storage import path_util
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.diagnose import diagnostic
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files


class DirectConnectivityDiagnostic(diagnostic.Diagnostic):
  """Direct Connectivity Diagnostic."""

  def __init__(
      self,
      test_bucket_url: storage_url.CloudUrl,
      logs_path=None,
  ):
    """Initializes the Direct Connectivity Diagnostic."""
    self._bucket_url = test_bucket_url
    self._object_path = 'direct_connectivity_diagnostics_' + str(uuid.uuid4())
    self._results = []
    self._retain_logs = bool(logs_path)

    if logs_path is None:
      self._logs_path = os.path.join(
          tempfile.gettempdir(),
          'direct_connectivity_log_' + path_util.generate_random_int_for_path(),
      )
    else:
      self._logs_path = files.ExpandHomeDir(logs_path)

  @property
  def name(self) -> str:
    return 'Direct Connectivity Diagnostic'

  def _run(self):
    """Runs the diagnostic test."""
    log.warning(
        'This diagnostic is experimental. The output may change,'
        ' and checks may be added or removed at any time. Please do not rely on'
        ' the diagnostic flag values being present.'
    )
    with files.FileWriter(self._logs_path):
      pass
    # TODO(b/350509119): Add checks described in
    # go/gcloud-storage-diagnose-direct-connectivity

  def _post_process(self):
    """Restores environment variables and cleans up temporary cloud object."""
    super(DirectConnectivityDiagnostic, self)._post_process()
    if not self._retain_logs and os.path.exists(self._logs_path):
      os.remove(self._logs_path)
    self._clean_up_objects(self._bucket_url.url_string, self._object_path)

  @property
  def result(self) -> diagnostic.DiagnosticResult:
    """Returns the summarized result of the diagnostic execution."""
    return diagnostic.DiagnosticResult(
        name=self.name,
        operation_results=self._results,
    )
