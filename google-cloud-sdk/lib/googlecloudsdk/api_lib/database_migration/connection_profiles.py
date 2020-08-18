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
"""Database Migration Service connection profiles API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.database_migration import api_util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.core import resources


def GetConnectionProfileURI(resource):
  connection_profile = resources.REGISTRY.ParseRelativeName(
      resource.name,
      collection='datamigration.projects.locations.connectionProfiles')
  return connection_profile.SelfLink()


class ConnectionProfilesClient(object):
  """Client for connection profiles service in the API."""

  def __init__(self, client=None, messages=None):
    self.client = client or api_util.GetClientInstance()
    self.messages = messages or api_util.GetMessagesModule()
    self._service = self.client.projects_locations_connectionProfiles
    self.resource_parser = api_util.GetResourceParser()

  def _ValidateArgs(self, args):
    self._ValidateSslConfigArgs(args)

  def _ValidateSslConfigArgs(self, args):
    self._ValidateCertificateFormat(args.ca_certificate, 'CA certificate')
    self._ValidateCertificateFormat(args.certificate, 'client certificate')
    self._ValidateCertificateFormat(args.private_key, 'private key')

  def _ValidateCertificateFormat(self, certificate, name):
    if not certificate:
      return True
    cert = certificate.strip()
    cert_lines = cert.split('\n')
    if (not cert_lines[0].startswith('-----')
        or not cert_lines[-1].startswith('-----')):
      raise exceptions.InvalidArgumentException(
          name,
          'The certificate does not appear to be in PEM format: \n{0}'
          .format(cert))

  def _GetSslConfig(self, args):
    return self.messages.SslConfig(
        clientKey=args.private_key,
        clientCertificate=args.certificate,
        caCertificate=args.ca_certificate)

  def _UpdateSslConfig(self, connection_profile, args, update_fields):
    if args.IsSpecified('ca_certificate'):
      connection_profile.mysql.ssl.caCertificate = args.ca_certificate
      update_fields.append('mysql.ssl.caCertificate')
    if args.IsSpecified('private_key'):
      connection_profile.mysql.ssl.clientKey = args.private_key
      update_fields.append('mysql.ssl.clientKey')
    if args.IsSpecified('certificate'):
      connection_profile.mysql.ssl.clientCertificate = args.certificate
      update_fields.append('mysql.ssl.clientCertificate')

  def _GetMySqlConnectionProfile(self, args):
    ssl_config = self._GetSslConfig(args)
    return self.messages.MySqlConnectionProfile(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        ssl=ssl_config,
        cloudSqlId=args.instance)

  def _UpdateMySqlConnectionProfile(
      self, connection_profile, args, update_fields):
    """Updates MySQL connection profile."""
    if args.IsSpecified('host'):
      connection_profile.mysql.host = args.host
      update_fields.append('mysql.host')
    if args.IsSpecified('port'):
      connection_profile.mysql.port = args.port
      update_fields.append('mysql.port')
    if args.IsSpecified('username'):
      connection_profile.mysql.username = args.username
      update_fields.append('mysql.username')
    if args.IsSpecified('password'):
      connection_profile.mysql.password = args.password
      update_fields.append('mysql.password')
    if args.IsSpecified('instance'):
      connection_profile.mysql.cloudSqlId = args.instance
      update_fields.append('mysql.instance')
    self._UpdateSslConfig(connection_profile, args, update_fields)

  def _GetProvider(self, cp_type, provider):
    if not provider:
      return cp_type.ProviderValueValuesEnum.UNKNOWN
    if provider == 'CLOUDSQL':
      return cp_type.ProviderValueValuesEnum.CLOUDSQL
    if provider == 'RDS':
      return cp_type.ProviderValueValuesEnum.RDS
    raise exceptions.InvalidArgumentException(
        provider,
        'The connection profile provider {0} is either unknown or not supported yet.'
        .format(cp_type))

  def _GetConnectionProfile(self, cp_type, connection_profile_id, args):
    """Returns a connection profile according to type."""
    connection_profile_type = self.messages.ConnectionProfile
    provider = self._GetProvider(connection_profile_type, args.provider)
    if cp_type == 'MYSQL':
      mysql_connection_profile = self._GetMySqlConnectionProfile(args)
      return connection_profile_type(
          name=connection_profile_id,
          labels={},
          state=connection_profile_type.StateValueValuesEnum.CREATING,
          displayName=args.display_name,
          provider=provider,
          mysql=mysql_connection_profile)
    else:
      raise exceptions.InvalidArgumentException(
          cp_type,
          'The connection profile type {0} is either unknown or not supported yet.'
          .format(cp_type))

  def _GetExistingConnectionProfile(self, name):
    get_req = self.messages.DatamigrationProjectsLocationsConnectionProfilesGetRequest(
        name=name
    )
    return self._service.Get(get_req)

  def _UpdateLabels(self, connection_profile, args):
    """Updates labels of the connection profile."""
    add_labels = labels_util.GetUpdateLabelsDictFromArgs(args)
    remove_labels = labels_util.GetRemoveLabelsListFromArgs(args)
    value_type = self.messages.ConnectionProfile.LabelsValue
    update_result = labels_util.Diff(
        additions=add_labels,
        subtractions=remove_labels,
        clear=args.clear_labels
    ).Apply(value_type, connection_profile.labels)
    if update_result.needs_update:
      connection_profile.labels = update_result.labels

  def _GetUpdatedConnectionProfile(self, connection_profile, args):
    """Returns updated connection profile and list of updated fields."""
    update_fields = []
    if args.IsSpecified('display_name'):
      connection_profile.displayName = args.display_name
      update_fields.append('displayName')
    if hasattr(connection_profile, 'mysql'):
      self._UpdateMySqlConnectionProfile(connection_profile,
                                         args,
                                         update_fields)
    else:
      cp_type = ''
      if hasattr(connection_profile, 'postgresql'):
        cp_type = 'postgresql'
      elif hasattr(connection_profile, 'cloudsql'):
        cp_type = 'cloudsql'
      raise exceptions.InvalidArgumentException(
          cp_type,
          'The connection profile type {0} is either unknown or not supported yet.'
          .format(cp_type))
    self._UpdateLabels(connection_profile, args)
    return connection_profile, update_fields

  def Create(self, parent_ref, connection_profile_id, cp_type, args=None):
    """Creates a connection profile.

    Args:
      parent_ref: a Resource reference to a parent
        datamigration.projects.locations resource for this connection
        profile.
      connection_profile_id: str, the name of the resource to create.
      cp_type: str, the type of the connection profile ('MYSQL', ''
      args: argparse.Namespace, The arguments that this command was
          invoked with.

    Returns:
      Operation: the operation for creating the connection profile.
    """
    self._ValidateArgs(args)

    connection_profile = self._GetConnectionProfile(cp_type,
                                                    connection_profile_id, args)

    request_id = api_util.GenerateRequestId()
    create_req_type = self.messages.DatamigrationProjectsLocationsConnectionProfilesCreateRequest
    create_req = create_req_type(
        connectionProfile=connection_profile,
        connectionProfileId=connection_profile.name,
        parent=parent_ref,
        requestId=request_id
        )

    return self._service.Create(create_req)

  def Update(self, name, args=None):
    """Updates a connection profile.

    Args:
      name: str, the reference of the connection profile to
          update.
      args: argparse.Namespace, The arguments that this command was
          invoked with.

    Returns:
      Operation: the operation for updating the connection profile.
    """
    self._ValidateArgs(args)

    current_cp = self._GetExistingConnectionProfile(name)

    updated_cp, update_fields = self._GetUpdatedConnectionProfile(
        current_cp, args)

    request_id = api_util.GenerateRequestId()
    update_req_type = self.messages.DatamigrationProjectsLocationsConnectionProfilesPatchRequest
    update_req = update_req_type(
        connectionProfile=updated_cp,
        name=updated_cp.name,
        updateMask=','.join(update_fields),
        requestId=request_id
    )

    return self._service.Patch(update_req)
