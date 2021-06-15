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
from googlecloudsdk.api_lib.datastream import exceptions as ds_exceptions
from googlecloudsdk.api_lib.datastream import util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
from googlecloudsdk.core.console import console_io


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

  def _ParseSslConfig(self, data):
    return self._messages.MysqlSslConfig(
        clientKey=data.get('client_key'),
        clientCertificate=data.get('client_certificate'),
        caCertificate=data.get('ca_certificate'))

  def _ParseMySqlProfile(self, data):
    if not data:
      return {}
    ssl_config = self._ParseSslConfig(data)
    return self._messages.MysqlProfile(
        hostname=data.get('hostname'),
        port=data.get('port'),
        username=data.get('username'),
        password=data.get('password'),
        sslConfig=ssl_config)

  def _ParseOracleProfile(self, data):
    if not data:
      return {}
    return self._messages.OracleProfile(
        hostname=data.get('hostname'),
        port=data.get('port'),
        username=data.get('username'),
        password=data.get('password'),
        databaseService=data.get('database_service'))

  def _ParseGCSProfile(self, data):
    if not data:
      return {}
    return self._messages.GcsProfile(
        bucketName=data.get('bucket_name'), rootPath=data.get('root_path'))

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

  def _ParseConnectionProfileObjectFile(self, connection_profile_object_file):
    """Parses a connection-profile-file into the ConnectionProfile message."""
    data = console_io.ReadFromFileOrStdin(
        connection_profile_object_file, binary=False)
    try:
      connection_profile_data = yaml.load(data)
    except Exception as e:
      raise ds_exceptions.ParseError('Cannot parse YAML:[{0}]'.format(e))

    display_name = connection_profile_data.get('display_name')
    labels = connection_profile_data.get('labels')
    connection_profile_msg = self._messages.ConnectionProfile(
        displayName=display_name,
        labels=labels)

    oracle_profile = self._ParseOracleProfile(
        connection_profile_data.get('oracle_profile', {}))
    mysql_profile = self._ParseMySqlProfile(
        connection_profile_data.get('mysql_profile', {}))
    gcs_profile = self._ParseGCSProfile(
        connection_profile_data.get('gcs_profile', {}))
    if oracle_profile:
      connection_profile_msg.oracleProfile = oracle_profile
    elif mysql_profile:
      connection_profile_msg.mysqlProfile = mysql_profile
    elif gcs_profile:
      connection_profile_msg.gcsProfile = gcs_profile

    if 'no_connectivity' in connection_profile_data:
      connection_profile_msg.noConnectivity = connection_profile_data.get(
          'no_connectivity')
    elif 'static_service_ip_connectivity' in connection_profile_data:
      connection_profile_msg.staticServiceIpConnectivity = connection_profile_data.get(
          'static_service_ip_connectivity')
    elif 'forward_ssh_connectivity' in connection_profile_data:
      connection_profile_msg.forwardSshConnectivity = connection_profile_data.get(
          'forward_ssh_connectivity')
    elif 'private_connectivity' in connection_profile_data:
      connection_profile_msg.privateConnectivity = connection_profile_data.get(
          'private_connectivity')
    else:
      raise ds_exceptions.ParseError(
          'Cannot parse YAML: missing connectivity method.')

    return connection_profile_msg

  def _ParseMysqlColumn(self, mysql_column_object):
    """Parses a raw mysql column json/yaml into the MysqlColumn message."""
    return self._messages.MysqlColumn(
        columnName=mysql_column_object.get('column_name', {}),
        dataType=mysql_column_object.get('data_type', {}),
        collation=mysql_column_object.get('collation', {}),
        length=mysql_column_object.get('length', {}),
        nullable=mysql_column_object.get('nullable', {}),
        ordinalPosition=mysql_column_object.get('ordinal_position', {}),
        primaryKey=mysql_column_object.get('primary_key', {}))

  def _ParseMysqlTable(self, mysql_table_object):
    """Parses a raw mysql table json/yaml into the MysqlTable message."""
    mysql_column_msg_list = []
    for column in mysql_table_object.get('mysql_columns', []):
      mysql_column_msg_list.append(self._ParseMysqlColumn(column))
    table_name = mysql_table_object.get('table_name')
    if not table_name:
      raise ds_exceptions.ParseError(
          'Cannot parse YAML: missing key "table_name".')
    return self._messages.MysqlTable(
        tableName=table_name,
        mysqlColumns=mysql_column_msg_list)

  def _ParseMysqlDatabase(self, mysql_database_object):
    """Parses a raw mysql database json/yaml into the MysqlDatabase message."""
    mysql_tables_msg_list = []
    for table in mysql_database_object.get('mysql_tables', []):
      mysql_tables_msg_list.append(self._ParseMysqlTable(table))
    database_name = mysql_database_object.get('database_name')
    if not database_name:
      raise ds_exceptions.ParseError(
          'Cannot parse YAML: missing key "database_name".')
    return self._messages.MysqlDatabase(
        databaseName=database_name,
        mysqlTables=mysql_tables_msg_list)

  def _ParseMysqlRdbmsFile(self, mysql_rdbms_file):
    """Parses a mysql_rdbms_file into the MysqlRdbms message."""
    data = console_io.ReadFromFileOrStdin(mysql_rdbms_file, binary=False)
    try:
      mysql_rdbms_head_data = yaml.load(data)
    except Exception as e:
      raise ds_exceptions.ParseError('Cannot parse YAML:[{0}]'.format(e))

    mysql_rdbms_data_object = mysql_rdbms_head_data.get('mysql_rdbms')
    mysql_rdbms_data = mysql_rdbms_data_object if mysql_rdbms_data_object else mysql_rdbms_head_data
    mysql_databases_raw = mysql_rdbms_data.get('mysql_databases', [])
    mysql_database_msg_list = []
    for schema in mysql_databases_raw:
      mysql_database_msg_list.append(self._ParseMysqlDatabase(schema))

    mysql_rdbms_msg = self._messages.MysqlRdbms(
        mysqlDatabases=mysql_database_msg_list)
    return mysql_rdbms_msg

  def _ParseOracleColumn(self, oracle_column_object):
    """Parses a raw oracle column json/yaml into the OracleColumn message."""
    return self._messages.OracleColumn(
        columnName=oracle_column_object.get('column_name', {}),
        dataType=oracle_column_object.get('data_type', {}),
        encoding=oracle_column_object.get('encoding', {}),
        length=oracle_column_object.get('length', {}),
        nullable=oracle_column_object.get('nullable', {}),
        ordinalPosition=oracle_column_object.get('ordinal_position', {}),
        precision=oracle_column_object.get('precision', {}),
        primaryKey=oracle_column_object.get('primary_key', {}),
        scale=oracle_column_object.get('scale', {}))

  def _ParseOracleTable(self, oracle_table_object):
    """Parses a raw oracle table json/yaml into the OracleTable message."""
    oracle_columns_msg_list = []
    for column in oracle_table_object.get('oracle_columns', []):
      oracle_columns_msg_list.append(self._ParseOracleColumn(column))
    table_name = oracle_table_object.get('table_name')
    if not table_name:
      raise ds_exceptions.ParseError(
          'Cannot parse YAML: missing key "table_name".')
    return self._messages.OracleTable(
        tableName=table_name,
        oracleColumns=oracle_columns_msg_list)

  def _ParseOracleSchema(self, oracle_schema_object):
    """Parses a raw oracle schema json/yaml into the OracleSchema message."""
    oracle_tables_msg_list = []
    for table in oracle_schema_object.get('oracle_tables', []):
      oracle_tables_msg_list.append(self._ParseOracleTable(table))
    schema_name = oracle_schema_object.get('schema_name')
    if not schema_name:
      raise ds_exceptions.ParseError(
          'Cannot parse YAML: missing key "schema_name".')
    return self._messages.OracleSchema(
        schemaName=schema_name,
        oracleTables=oracle_tables_msg_list)

  def _ParseOracleRdbmsFile(self, oracle_rdbms_file):
    """Parses a oracle_rdbms_file into the OracleRdbms message."""
    data = console_io.ReadFromFileOrStdin(oracle_rdbms_file, binary=False)
    try:
      oracle_rdbms_head_data = yaml.load(data)
    except Exception as e:
      raise ds_exceptions.ParseError('Cannot parse YAML:[{0}]'.format(e))

    oracle_rdbms_data_object = oracle_rdbms_head_data.get('oracle_rdbms')
    oracle_rdbms_data = oracle_rdbms_data_object if oracle_rdbms_data_object else oracle_rdbms_head_data
    oracle_schemas_raw = oracle_rdbms_data.get('oracle_schemas', [])
    oracle_schema_msg_list = []
    for schema in oracle_schemas_raw:
      oracle_schema_msg_list.append(self._ParseOracleSchema(schema))

    oracle_rdbms_msg = self._messages.OracleRdbms(
        oracleSchemas=oracle_schema_msg_list)
    return oracle_rdbms_msg

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

  def Discover(self, parent_ref, args):
    """Discover a connection profile.

    Args:
      parent_ref: a Resource reference to a parent datastream.projects.locations
        resource for this connection profile.
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Returns:
      Operation: the operation for discovering the connection profile.
    """
    request = self._messages.DiscoverConnectionProfileRequest()
    if args.connection_profile_name:
      connection_profile_ref = args.CONCEPTS.connection_profile_name.Parse()
      request.connectionProfileName = connection_profile_ref.RelativeName()
    elif args.connection_profile_object_file:
      request.connectionProfile = self._ParseConnectionProfileObjectFile(
          args.connection_profile_object_file)

    if args.recursive:
      request.recursive = True
    else:
      request.recursionDepth = (int)(args.recursive_depth)

    if args.mysql_rdbms_file:
      request.mysqlRdbms = self._ParseMysqlRdbmsFile(args.mysql_rdbms_file)
    elif args.oracle_rdbms_file:
      request.oracleRdbms = self._ParseOracleRdbmsFile(args.oracle_rdbms_file)

    discover_req_type = self._messages.DatastreamProjectsLocationsConnectionProfilesDiscoverRequest
    discover_req = discover_req_type(
        discoverConnectionProfileRequest=request, parent=parent_ref)
    return self._service.Discover(discover_req)

  def GetUri(self, name):
    """Get the URL string for a connnection profile.

    Args:
      name: connection profile's full name.

    Returns:
      URL of the connection profile resource
    """

    uri = self._resource_parser.ParseRelativeName(
        name, collection='datastream.projects.locations.connectionProfiles')
    return uri.SelfLink()
