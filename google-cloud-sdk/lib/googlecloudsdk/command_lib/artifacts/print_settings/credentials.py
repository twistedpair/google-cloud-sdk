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
"""Utility for forming settings for Artifacts Registry repositories."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64
import json

from googlecloudsdk.api_lib.auth import service_account
from googlecloudsdk.core import config
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.credentials import creds
from googlecloudsdk.core.credentials import exceptions as creds_exceptions
from googlecloudsdk.core.credentials import store
from googlecloudsdk.core.util import encoding
from googlecloudsdk.core.util import files


def _LoadJsonFile(filename):
  """Checks and validates if given filename is a proper JSON file.

  Args:
    filename: str, path to JSON file.

  Returns:
    bytes, the content of the file.
  """
  content = console_io.ReadFromFileOrStdin(filename, binary=True)
  try:
    json.loads(encoding.Decode(content))
    return content
  except ValueError as e:
    if filename.endswith(".json"):
      raise service_account.BadCredentialFileException(
          "Could not read JSON file {0}: {1}".format(filename, e))
  raise service_account.BadCredentialFileException(
      "Unsupported credential file: {0}".format(filename))


def GetServiceAccountCreds(json_key):
  """Gets service account credentials from given file path or default if any.

  Args:
    json_key: str, path to JSON key file.

  Returns:
    str, service account credentials.
  """
  if json_key:
    file_content = _LoadJsonFile(json_key)
    return base64.b64encode(file_content).decode("utf-8")

  account = properties.VALUES.core.account.Get()
  if not account:
    raise creds_exceptions.NoActiveAccountException()
  cred = store.Load(account, prevent_refresh=True)
  if not cred:
    raise store.NoCredentialsForAccountException(account)

  if _IsServiceAccountCredentials(cred):
    paths = config.Paths()
    json_content = files.ReadFileContents(
        paths.LegacyCredentialsAdcPath(account))
    return base64.b64encode(json_content.encode("utf-8")).decode("utf-8")
  return ""


def _IsServiceAccountCredentials(cred):
  return creds.CredentialTypeGoogleAuth.FromCredentials(
      cred) == creds.CredentialTypeGoogleAuth.SERVICE_ACCOUNT
