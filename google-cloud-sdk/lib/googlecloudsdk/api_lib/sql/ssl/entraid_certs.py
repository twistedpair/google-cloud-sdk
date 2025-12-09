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

"""Common command-agnostic utility functions for entraid-certs commands."""


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

ACTIVE_CERT_LABEL = 'Active'
NEXT_CERT_LABEL = 'Next'
PREVIOUS_CERT_LABEL = 'Previous'


def ListEntraIdCertificates(sql_client, sql_messages, instance_ref):
  """Calls the list entraid certs endpoint and returns the response."""
  return sql_client.instances.ListEntraIdCertificates(
      sql_messages.SqlInstancesListEntraIdCertificatesRequest(
          project=instance_ref.project, instance=instance_ref.instance
      )
  )


def _GetCurrentEntraIdCertificate(list_entraid_certs_response):
  """Returns the current Entra ID Cert."""
  entraid_cert_types = GetEntraIdCertificateTypeDict(
      list_entraid_certs_response
  )
  return (entraid_cert_types.get(ACTIVE_CERT_LABEL), ACTIVE_CERT_LABEL)


def GetNextEntraIdCertificate(sql_client, sql_messages, instance_ref):
  """Returns the next Entra ID Cert."""
  list_entraid_certs_response = ListEntraIdCertificates(
      sql_client, sql_messages, instance_ref
  )
  return _GetNextEntraIdCertificateFromListResponse(list_entraid_certs_response)


def _GetNextEntraIdCertificateFromListResponse(list_entraid_certs_response):
  entraid_cert_types = GetEntraIdCertificateTypeDict(
      list_entraid_certs_response
  )
  return (entraid_cert_types.get(NEXT_CERT_LABEL), NEXT_CERT_LABEL)


def GetPreviousEntraIdCertificate(sql_client, sql_messages, instance_ref):
  """Returns the previous Entra ID Cert.

  Args:
    sql_client: Sql client.
    sql_messages: Sql messages.
    instance_ref: Instance reference.

  Returns:
    A tuple of the previous Entra ID Cert and the status of the cert.
  """
  list_entraid_certs_response = ListEntraIdCertificates(
      sql_client, sql_messages, instance_ref
  )
  return _GetPreviousEntraIdCertificate(list_entraid_certs_response)


def _GetPreviousEntraIdCertificate(list_entraid_certs_response):
  entraid_cert_types = GetEntraIdCertificateTypeDict(
      list_entraid_certs_response
  )
  return (entraid_cert_types.get(PREVIOUS_CERT_LABEL), PREVIOUS_CERT_LABEL)


def GetAddedEntraIdCertificate(sql_client, sql_messages, instance_ref):
  """Returns the added Entra ID Cert.

  If this is the first cert, that cert will be Active. Subsequent certs will be
  Next.

  Args:
    sql_client: Sql client.
    sql_messages: Sql messages.
    instance_ref: Instance reference.

  Returns:
    A tuple of the added Entra ID Cert and the status of the cert.
  """
  list_entraid_certs_response = ListEntraIdCertificates(
      sql_client, sql_messages, instance_ref
  )
  if len(list_entraid_certs_response.certs) == 1:
    return _GetCurrentEntraIdCertificate(list_entraid_certs_response)
  else:
    return _GetNextEntraIdCertificateFromListResponse(
        list_entraid_certs_response
    )


def GetEntraIdCertificateTypeDict(list_entraid_certs_response):
  """Gets a dictionary mapping Entra ID Cert types to certs.

  The keys to the dictionary returned will be some combination of 'Current',
  'Next', and 'Previous'.

  Args:
    list_entraid_certs_response: InstancesListEntraIdCertificatesResponse
      instance.

  Returns:
    A dictionary mapping Entra ID Cert types to SslCert instances.
  """
  entraid_cert_types = {}

  active_id = list_entraid_certs_response.activeVersion

  # Get the active cert.
  certs = list_entraid_certs_response.certs
  active_cert = None
  for cert in certs:
    if cert.sha1Fingerprint == active_id:
      active_cert = cert
      break
  if not active_cert:
    # No entraid cert types can be discerned; return an empty dict.
    return entraid_cert_types
  entraid_cert_types[ACTIVE_CERT_LABEL] = active_cert

  # Get the inactive certs.
  inactive_certs = [cert for cert in certs if cert.sha1Fingerprint != active_id]
  if len(inactive_certs) == 1:
    inactive_cert = inactive_certs[0]
    if inactive_cert.createTime > active_cert.createTime:
      # Found the next cert.
      entraid_cert_types[NEXT_CERT_LABEL] = inactive_cert
    else:
      # Found the previous cert.
      entraid_cert_types[PREVIOUS_CERT_LABEL] = inactive_cert
  elif len(inactive_certs) > 1:
    # Sort by expiration date.
    inactive_certs = sorted(inactive_certs, key=lambda cert: cert.createTime)
    entraid_cert_types[PREVIOUS_CERT_LABEL] = inactive_certs[0]
    entraid_cert_types[NEXT_CERT_LABEL] = inactive_certs[-1]

  return entraid_cert_types
