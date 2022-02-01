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
"""Resource parsing helpers."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.calliope import exceptions

STRING_MAX_LENGTH = 1000


def ValidatePort(port):
  """Python hook to validate that the port is between 1024 and 65535, inclusive."""
  if port < 1024 or port > 65535:
    raise exceptions.BadArgumentException(
        '--port', 'Port ({0}) is not in the range [1025, 65535].'.format(port))
  return port


def ValidateGcsUri(arg_name):
  """Validates the gcs uri is formatted correctly."""

  def Process(gcs_uri):
    if not gcs_uri.startswith('gs://'):
      raise exceptions.BadArgumentException(
          arg_name, 'Expected URI {0} to start with `gs://`.'.format(gcs_uri))
    return gcs_uri

  return Process


def ValidateKerberosPrincipal(kerberos_principal):
  pattern = re.compile(r'^(.+)/(.+)@(.+)$')
  if not pattern.match(kerberos_principal):
    raise exceptions.BadArgumentException(
        '--kerberos-principal',
        'Kerberos Principal {0} does not match ReGeX {1}.'.format(
            kerberos_principal, pattern))
  return kerberos_principal


def ValidateHourOfDay(hour):
  """Validates that the hour falls between 0 and 23, inclusive."""
  if hour < 0 or hour > 23:
    raise exceptions.BadArgumentException(
        '--maintenance-window-hour-of-day',
        'Hour of day ({0}) is not in [0, 23].'.format(hour))
  return hour


def ValidateStringField(arg_name):
  """Validates that the string field is not longer than STRING_MAX_LENGTH, to avoid abuse issues."""

  def Process(string):
    if len(string) > STRING_MAX_LENGTH:
      raise exceptions.BadArgumentException(
          arg_name,
          'The string field can not be longer than {0} characters.'.format(
              STRING_MAX_LENGTH))

  return Process


def ValidateServiceMutexConfig(unused_ref, unused_args, req):
  """Validates that the mutual exclusive configurations of Dataproc Metastore service are not set at the same time.

  Args:
    req: A request with `service` field.

  Returns:
    A request without service mutex configuration conflicts.
  Raises:
    BadArgumentException: when mutual exclusive configurations of service are
    set at the same time.
  """
  if (req.service.encryptionConfig and req.service.encryptionConfig.kmsKey and
      req.service.metadataIntegration.dataCatalogConfig.enabled):
    raise exceptions.BadArgumentException(
        '--data-catalog-sync',
        'Data Catalog synchronization cannot be used in conjunction with customer-managed encryption keys.'
    )
  if (req.service.hiveMetastoreConfig and
      req.service.hiveMetastoreConfig.kerberosConfig and
      req.service.hiveMetastoreConfig.kerberosConfig.principal and
      req.service.networkConfig):
    raise exceptions.BadArgumentException(
        '--kerberos-principal',
        'Kerberos configuration cannot be used in conjunction with --network-config-from-file or --consumer-subnetworks.'
    )
  if (req.service.hiveMetastoreConfig and
      req.service.hiveMetastoreConfig.auxiliaryVersions and
      req.service.networkConfig):
    raise exceptions.BadArgumentException(
        '--auxiliary-versions',
        'Auxiliary versions configuration cannot be used in conjunction with --network-config-from-file or --consumer-subnetworks.'
    )
  return req
