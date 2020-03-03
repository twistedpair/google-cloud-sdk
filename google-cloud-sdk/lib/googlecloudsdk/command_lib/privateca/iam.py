# Lint as: python3
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
"""Helpers for testing IAM permissions."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.cloudkms import iam as kms_iam
from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.command_lib.privateca import exceptions

# Permissions needed on a KMS key for creating a CA.
_KEY_CREATE_PERMISSIONS = [
    'cloudkms.setIamPolicy',
    'cloudkms.cryptoKeyVersions.viewPublicKey',
]

# Permissions needed on a project for creating a CA.
_PROJECT_CREATE_PERMISSIONS = [
    'privateca.certificateAuthorities.create',
    'storage.buckets.create'
]


def _HasAllPermissions(iam_response, requested_permissions):
  """Returns True if all the requested permissions are set in the response."""
  # IAM won't return more permissions than requested, so equality works here.
  return set(iam_response.permissions) == set(requested_permissions)


def CheckCreateCertificateAuthorityPermissions(project_ref, kms_key_ref):
  """Ensures that the current user has the required permissions to create a CA.

  Args:
    project_ref: The project where the new CA will be created.
    kms_key_ref: The KMS key that will be used by the CA.

  Raises:
    InsufficientPermissionException: If the user is missing permissions.
  """
  if not _HasAllPermissions(
      projects_api.TestIamPermissions(project_ref, _PROJECT_CREATE_PERMISSIONS),
      _PROJECT_CREATE_PERMISSIONS):
    raise exceptions.InsufficientPermissionException(resource='project')
  if not _HasAllPermissions(
      kms_iam.TestCryptoKeyIamPermissions(kms_key_ref, _KEY_CREATE_PERMISSIONS),
      _KEY_CREATE_PERMISSIONS):
    raise exceptions.InsufficientPermissionException(resource='KMS key')
