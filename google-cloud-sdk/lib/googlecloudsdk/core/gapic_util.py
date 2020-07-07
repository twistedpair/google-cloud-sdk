# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Helper Classes for using gapic clients in gcloud."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core.credentials import store
from google.auth import credentials


class MissingStoredCredentialsError(Exception):
  """Indicates stored credentials do not exist or are not available."""


class StoredCredentials(credentials.Credentials):
  """Implements the Credentials interface required by gapic."""

  def __init__(self):
    super(StoredCredentials, self).__init__()
    self.stored_credentials = store.LoadIfEnabled(
        allow_account_impersonation=True, use_google_auth=False)
    if self.stored_credentials is None:
      raise MissingStoredCredentialsError()
    self.token = self.stored_credentials.access_token

  def __str__(self):
    return self.stored_credentials.to_json()

  def refresh(self, request):
    pass
