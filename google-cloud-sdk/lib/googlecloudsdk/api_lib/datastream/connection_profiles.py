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
"""Cloud Datastream connection profiles API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager

from googlecloudsdk.api_lib.datastream import util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import resources


def GetConnectionProfileURI(resource):
  connection_profile = resources.REGISTRY.ParseRelativeName(
      resource.name,
      collection='datastream.projects.locations.connectionProfiles')
  return connection_profile.SelfLink()


class ConnectionProfilesClient(object):
  """Client for connection profiles service in the API."""

  def __init__(self, client=None, messages=None):
    self._client = client or util.GetClientInstance()
    self._messages = messages or util.GetMessagesModule()
    self._service = self._client.projects_locations_connectionProfiles
    self._resource_parser = util.GetResourceParser()

  def _ValidateArgs(self, args):
    self._ValidateSslConfigArgs(args)

  def _ValidateSslConfigArgs(self, args):
    self._ValidateCertificateFormat(args.ca_certificate, 'CA certificate')
    self._ValidateCertificateFormat(args.client_certificate,
                                    'client certificate')
    self._ValidateCertificateFormat(args.client_key, 'client key')

  def _ValidateCertificateFormat(self, certificate, name):
    if not certificate:
      return True
    cert = certificate.strip()
    cert_lines = cert.split('\n')
    if (not cert_lines[0].startswith('-----') or
        not cert_lines[-1].startswith('-----')):
      raise exceptions.InvalidArgumentException(
          name,
          'The certificate does not appear to be in PEM format: \n{0}'.format(
              cert))

  def _GetSslConfig(self, args):
    return self._messages.MysqlSslConfig(
        clientKey=args.client_key,
        clientCertificate=args.client_certificate,
        caCertificate=args.ca_certificate)

  def _GetMySqlProfile(self, args):
    ssl_config = self._GetSslConfig(args)
    return self._messages.MysqlProfile(
        hostname=args.mysql_hostname,
        port=args.mysql_port,
        username=args.mysql_username,
        password=args.mysql_password,
        sslConfig=ssl_config)

  def _GetOracleProfile(self, args):
    return self._messages.OracleProfile(
        hostname=args.oracle_hostname,
        port=args.oracle_port,
        username=args.oracle_username,
        password=args.oracle_password,
        databaseService=args.database_service)

  def _GetGCSProfile(self, args):
    return self._messages.GcsProfile(
        bucketName=args.bucket_name, rootPath=args.root_path)

  def _GetForwardSshTunnelConnectivity(self, args):
    return self._messages.ForwardSshTunnelConnectivity(
        hostname=args.forward_ssh_hostname,
        port=args.forward_ssh_port,
        username=args.forward_ssh_username,
        privateKey=args.forward_ssh_private_key,
        password=args.forward_ssh_password)

  def _GetConnectionProfile(self, cp_type, connection_profile_id, args):
    """Returns a connection profile according to type."""
    connection_profile_obj = self._messages.ConnectionProfile(
        name=connection_profile_id, labels={}, displayName=args.display_name)

    if cp_type == 'MYSQL':
      connection_profile_obj.mysqlProfile = self._GetMySqlProfile(args)
    elif cp_type == 'ORACLE':
      connection_profile_obj.oracleProfile = self._GetOracleProfile(args)
    elif cp_type == 'GOOGLE-CLOUD-STORAGE':
      connection_profile_obj.gcsProfile = self._GetGCSProfile(args)
    else:
      raise exceptions.InvalidArgumentException(
          cp_type,
          'The connection profile type {0} is either unknown or not supported yet.'
          .format(cp_type))

    private_connectivity_ref = args.CONCEPTS.private_connection_name.Parse()
    if private_connectivity_ref:
      connection_profile_obj.privateConnectivity = self._messages.PrivateConnectivity(
          privateConnectionName=private_connectivity_ref.RelativeName())
    elif args.forward_ssh_hostname:
      connection_profile_obj.forwardSshConnectivity = self._GetForwardSshTunnelConnectivity(
          args)
    elif args.static_ip_connectivity:
      connection_profile_obj.staticServiceIpConnectivity = {}
    else:
      connection_profile_obj.noConnectivity = {}

    return connection_profile_obj

  def Create(self, parent_ref, connection_profile_id, cp_type, args=None):
    """Creates a connection profile.

    Args:
      parent_ref: a Resource reference to a parent datastream.projects.locations
        resource for this connection profile.
      connection_profile_id: str, the name of the resource to create.
      cp_type: str, the type of the connection profile ('MYSQL', ''
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Returns:
      Operation: the operation for creating the connection profile.
    """
    self._ValidateArgs(args)

    connection_profile = self._GetConnectionProfile(cp_type,
                                                    connection_profile_id, args)

    request_id = util.GenerateRequestId()
    create_req_type = self._messages.DatastreamProjectsLocationsConnectionProfilesCreateRequest
    create_req = create_req_type(
        connectionProfile=connection_profile,
        connectionProfileId=connection_profile.name,
        parent=parent_ref,
        requestId=request_id)

    return self._service.Create(create_req)

  def List(self, project_id, args):
    """Get the list of connection profiles in a project.

    Args:
      project_id: The project ID to retrieve
      args: parsed command line arguments

    Returns:
      An iterator over all the matching connection profiles.
    """
    location_ref = self._resource_parser.Create(
        'datastream.projects.locations',
        projectsId=project_id,
        locationsId=args.location)

    list_req_type = self._messages.DatastreamProjectsLocationsConnectionProfilesListRequest
    list_req = list_req_type(
        parent=location_ref.RelativeName(),
        filter=args.filter,
        orderBy=','.join(args.sort_by) if args.sort_by else None)

    return list_pager.YieldFromList(
        service=self._client.projects_locations_connectionProfiles,
        request=list_req,
        limit=args.limit,
        batch_size=args.page_size,
        field='connectionProfiles',
        batch_size_attribute='pageSize')

  def GetUri(self, name):
    """Get the URL string for a connnection profile.

    Args:
      name: connection profile's full name.

    Returns:
      URL of the connection profile resource
    """

    uri = self._resource_parser.ParseRelativeName(
        name,
        collection='datastream.projects.locations.connectionProfiles')
    return uri.SelfLink()
