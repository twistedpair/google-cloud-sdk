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
"""Hooks for Privateca surface."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.privateca import base
from googlecloudsdk.command_lib.privateca import exceptions as exceptions


def _CheckTypeHook(response, ca_type):
  """Raises an exception if the response is not of type ca_type.

  Args:
    response: The ca response from the server.
    ca_type: The string descripting the type. Either 'subordinate' or 'root'.

  Returns:
    The response, unmodified.
  """
  ca_type_enum = base.GetMessagesModule(
  ).CertificateAuthority.TypeValueValuesEnum
  if ca_type == ca_type_enum.SUBORDINATE and response.type != ca_type:
    raise exceptions.InvalidCertificateAuthorityTypeError(
        'Cannot perform subordinates command on Root CA. Please use the `privateca roots` command group instead.'
    )
  elif ca_type == ca_type_enum.SELF_SIGNED and response.type != ca_type:
    raise exceptions.InvalidCertificateAuthorityTypeError(
        'Cannot perform roots command on Subordinate CA. Please use the `privateca subordinates` command group instead.'
    )
  return response


def CheckSubordinateTypeHook(response, _):
  """Raises an exception if the response is not a subordinate ca."""
  return _CheckTypeHook(
      response,
      base.GetMessagesModule().CertificateAuthority.TypeValueValuesEnum
      .SUBORDINATE)


def CheckRootTypeHook(response, _):
  """Raises an exception if the response is not a root ca."""
  return _CheckTypeHook(
      response,
      base.GetMessagesModule().CertificateAuthority.TypeValueValuesEnum
      .SELF_SIGNED)
