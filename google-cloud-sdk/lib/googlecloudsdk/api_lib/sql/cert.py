# Copyright 2015 Google Inc. All Rights Reserved.

"""Common utility functions for sql instances using v1beta3 API."""


def GetCertRefFromName(
    sql_client, sql_messages, resources, instance_ref, common_name):
  """Get a cert reference for a particular instance, given its common name.

  Args:
    sql_client: apitools.BaseApiClient, A working client for the sql version to
        be used.
    sql_messages: module, The module that defines the messages for the sql
        version to be used.
    resources: resources.Registry, The registry that can create resource refs
        for the sql version to be used.
    instance_ref: resources.Resource, The instance whos ssl cert is being
        fetched.
    common_name: str, The common name of the ssl cert to be fetched.

  Returns:
    resources.Resource, A ref for the ssl cert being fetched. Or None if it
    could not be found.
  """
  cert = GetCertFromName(sql_client, sql_messages, instance_ref, common_name)

  if not cert:
    return None

  return resources.Create(
      collection='sql.sslCerts',
      project=instance_ref.project,
      instance=instance_ref.instance,
      sha1Fingerprint=cert.sha1Fingerprint)


def GetCertFromName(
    sql_client, sql_messages, instance_ref, common_name):
  """Get a cert for a particular instance, given its common name.

  In versions of the SQL API up to at least v1beta3, the last parameter of the
  URL is the sha1fingerprint, which is not something writeable or readable by
  humans. Instead, the CLI will ask for the common name. To allow this, we first
  query all the ssl certs for the instance, and iterate through them to find the
  one with the correct common name.

  Args:
    sql_client: apitools.BaseApiClient, A working client for the sql version to
        be used.
    sql_messages: module, The module that defines the messages for the sql
        version to be used.
    instance_ref: resources.Resource, The instance whos ssl cert is being
        fetched.
    common_name: str, The common name of the ssl cert to be fetched.

  Returns:
    resources.Resource, A ref for the ssl cert being fetched. Or None if it
    could not be found.
  """
  certs = sql_client.sslCerts.List(
      sql_messages.SqlSslCertsListRequest(
          project=instance_ref.project,
          instance=instance_ref.instance))
  for cert in certs.items:
    if cert.commonName == common_name:
      return cert

  return None
