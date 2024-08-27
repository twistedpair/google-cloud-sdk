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
"""Common command-agnostic utility functions for server-certs commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

ACTIVE_CERT_LABEL = 'Active'
NEXT_CERT_LABEL = 'Next'
PREVIOUS_CERT_LABEL = 'Previous'


def ListServerCertificates(sql_client, sql_messages, instance_ref):
  """Calls the list server certs endpoint and returns the response."""
  return sql_client.instances.ListServerCertificates(
      sql_messages.SqlInstancesListServerCertificatesRequest(
          project=instance_ref.project, instance=instance_ref.instance
      )
  )


def GetServerCertificateTypeDict(list_server_certs_response):
  """Gets a dictionary mapping Server Cert types to certs.

  The keys to the dictionary returned will be some combinatiaon of 'Current',
  'Next', and 'Previous'.

  Args:
    list_server_certs_response: InstancesListServerCertificatesResponse
      instance.

  Returns:
    A dictionary mapping Server Cert types to SslCert instances.
  """
  server_cert_types = {}

  active_id = list_server_certs_response.activeVersion

  # Get the active cert.
  certs = list_server_certs_response.serverCerts
  active_cert = None
  for cert in certs:
    if cert.sha1Fingerprint == active_id:
      active_cert = cert
      break
  if not active_cert:
    # No server cert types can be discerned; return an empty dict.
    return server_cert_types
  server_cert_types[ACTIVE_CERT_LABEL] = active_cert

  # Get the inactive certs.
  inactive_certs = [cert for cert in certs if cert.sha1Fingerprint != active_id]
  if len(inactive_certs) == 1:
    inactive_cert = inactive_certs[0]
    if inactive_cert.createTime > active_cert.createTime:
      # Found the next cert.
      server_cert_types[NEXT_CERT_LABEL] = inactive_cert
    else:
      # Found the previous cert.
      server_cert_types[PREVIOUS_CERT_LABEL] = inactive_cert
  elif len(inactive_certs) > 1:
    # Sort by expiration date.
    inactive_certs = sorted(inactive_certs, key=lambda cert: cert.createTime)
    server_cert_types[PREVIOUS_CERT_LABEL] = inactive_certs[0]
    server_cert_types[NEXT_CERT_LABEL] = inactive_certs[-1]

  return server_cert_types


def GetCurrentServerCertificate(sql_client, sql_messages, instance_ref):
  """Returns the currently active Server Cert."""
  server_cert_types = GetServerCertificateTypeDict(
      ListServerCertificates(sql_client, sql_messages, instance_ref)
  )
  return server_cert_types.get(ACTIVE_CERT_LABEL)


def GetNextServerCertificate(sql_client, sql_messages, instance_ref):
  """Returns the upcoming Server Cert."""
  server_cert_types = GetServerCertificateTypeDict(
      ListServerCertificates(sql_client, sql_messages, instance_ref)
  )
  return server_cert_types.get(NEXT_CERT_LABEL)


def GetPreviousServerCertificate(sql_client, sql_messages, instance_ref):
  """Returns the previously active Server Cert."""
  server_cert_types = GetServerCertificateTypeDict(
      ListServerCertificates(sql_client, sql_messages, instance_ref)
  )
  return server_cert_types.get(PREVIOUS_CERT_LABEL)
