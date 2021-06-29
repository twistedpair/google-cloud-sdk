# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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

from googlecloudsdk.api_lib.datastream import exceptions as ds_exceptions
from googlecloudsdk.api_lib.datastream import util
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
from googlecloudsdk.core.console import console_io


def GetStreamURI(resource):
  stream = resources.REGISTRY.ParseRelativeName(
      resource.name,
      collection='datastream.projects.locations.streams')
  return stream.SelfLink()


class StreamsClient(object):
  """Client for streams service in the API."""

  def __init__(self, client=None, messages=None):
    self._client = client or util.GetClientInstance()
    self._messages = messages or util.GetMessagesModule()
    self._service = self._client.projects_locations_streams
    self._resource_parser = util.GetResourceParser()

  def _GetBackfillAllStrategy(self, args):
    if args.oracle_excluded_objects:
      return self._messages.BackfillAllStrategy(
          oracleExcludedObjects=util.ParseOracleRdbmsFile(
              self._messages, args.oracle_excluded_objects))
    elif args.mysql_excluded_objects:
      return self._messages.BackfillAllStrategy(
          mysqlExcludedObjects=util.ParseMysqlRdbmsFile(
              self._messages, args.mysql_excluded_objects))

  def _ParseOracleSourceConfig(self, oracle_source_config_file):
    """Parses a oracle_sorce_config into the OracleSourceConfig message."""
    data = console_io.ReadFromFileOrStdin(
        oracle_source_config_file, binary=False)
    try:
      oracle_sorce_config_head_data = yaml.load(data)
    except Exception as e:
      raise ds_exceptions.ParseError('Cannot parse YAML:[{0}]'.format(e))

    oracle_sorce_config_data_object = oracle_sorce_config_head_data.get(
        'oracle_source_config')
    oracle_rdbms_data = oracle_sorce_config_data_object if oracle_sorce_config_data_object else oracle_sorce_config_head_data
    allowlist_raw = oracle_rdbms_data.get('allowlist', {})
    allowlist_data = util.ParseOracleSchemasListToOracleRdbmsMessage(
        self._messages, allowlist_raw)

    rejectlist_raw = oracle_rdbms_data.get('rejectlist', {})
    rejectlist_data = util.ParseOracleSchemasListToOracleRdbmsMessage(
        self._messages, rejectlist_raw)

    oracle_sourec_config_msg = self._messages.OracleSourceConfig(
        allowlist=allowlist_data, rejectlist=rejectlist_data)
    return oracle_sourec_config_msg

  def _ParseMysqlSourceConfig(self, mysql_source_config_file):
    """Parses a mysql_sorce_config into the MysqlSourceConfig message."""
    data = console_io.ReadFromFileOrStdin(
        mysql_source_config_file, binary=False)
    try:
      mysql_sorce_config_head_data = yaml.load(data)
    except Exception as e:
      raise ds_exceptions.ParseError('Cannot parse YAML:[{0}]'.format(e))

    mysql_sorce_config_data_object = mysql_sorce_config_head_data.get(
        'mysql_source_config')
    mysql_rdbms_data = mysql_sorce_config_data_object if mysql_sorce_config_data_object else mysql_sorce_config_head_data

    allowlist_raw = mysql_rdbms_data.get('allowlist', {})
    allowlist_data = util.ParseMysqlSchemasListToMysqlRdbmsMessage(
        self._messages, allowlist_raw)

    rejectlist_raw = mysql_rdbms_data.get('rejectlist', {})
    rejectlist_data = util.ParseMysqlSchemasListToMysqlRdbmsMessage(
        self._messages, rejectlist_raw)

    mysql_sourec_config_msg = self._messages.MysqlSourceConfig(
        allowlist=allowlist_data, rejectlist=rejectlist_data)
    return mysql_sourec_config_msg

  def _ParseGcsDestinationConfig(self, gcs_destination_config_file):
    """Parses a gcs_destination_config into the GcsDestinationConfig message."""
    data = console_io.ReadFromFileOrStdin(
        gcs_destination_config_file, binary=False)
    try:
      gcs_destination_head_config_data = yaml.load(data)
    except Exception as e:
      raise ds_exceptions.ParseError('Cannot parse YAML:[{0}]'.format(e))

    gcs_destination_config_data_object = gcs_destination_head_config_data.get(
        'gcs_destination_config')
    gcs_destination_config_data = gcs_destination_config_data_object if gcs_destination_config_data_object else gcs_destination_head_config_data

    path = gcs_destination_config_data.get('path', '')
    file_rotation_mb = gcs_destination_config_data.get('file_rotation_mb', {})
    file_rotation_interval = gcs_destination_config_data.get(
        'file_rotation_interval', {})
    gcs_dest_config_msg = self._messages.GcsDestinationConfig(
        path=path, fileRotationMb=file_rotation_mb,
        fileRotationInterval=file_rotation_interval)
    if 'avro_file_format' in gcs_destination_config_data:
      gcs_dest_config_msg.avroFileFormat = self._messages.AvroFileFormat()
    elif 'json_file_format' in gcs_destination_config_data:
      json_file_format_data = gcs_destination_config_data.get(
          'json_file_format')
      gcs_dest_config_msg.jsonFileFormat = self._messages.JsonFileFormat(
          compression=json_file_format_data.get('compression'),
          schemaFileFormat=json_file_format_data.get('schema_file_format'))
    else:
      raise ds_exceptions.ParseError(
          'Cannot parse YAML: missing file format.')
    return gcs_dest_config_msg

  def _GetStream(self, stream_id, args):
    """Returns a Stream object."""
    labels = labels_util.ParseCreateArgs(
        args, self._messages.Stream.LabelsValue)
    stream_obj = self._messages.Stream(
        name=stream_id, labels=labels, displayName=args.display_name)

    stream_source_config = self._messages.SourceConfig()
    source_connection_profile_ref = args.CONCEPTS.source_name.Parse()
    stream_source_config.sourceConnectionProfileName = (
        source_connection_profile_ref.RelativeName())
    if args.oracle_source_config:
      stream_source_config.oracleSourceConfig = self._ParseOracleSourceConfig(
          args.oracle_source_config)
    elif args.mysql_source_config:
      stream_source_config.mysqlSourceConfig = self._ParseMysqlSourceConfig(
          args.mysql_source_config)
    stream_obj.sourceConfig = stream_source_config

    stream_destination_config = self._messages.DestinationConfig()
    destination_connection_profile_ref = args.CONCEPTS.destination_name.Parse()
    stream_destination_config.destinationConnectionProfileName = (
        destination_connection_profile_ref.RelativeName())
    if args.gcs_destination_config:
      stream_destination_config.gcsDestinationConfig = (
          self._ParseGcsDestinationConfig(args.gcs_destination_config))
    stream_obj.destinationConfig = stream_destination_config

    if args.backfill_none:
      stream_obj.backfillNone = self._messages.BackfillNoneStrategy()
    elif args.backfill_all:
      backfill_all_strategy = self._GetBackfillAllStrategy(args)
      stream_obj.backfillAll = backfill_all_strategy

    return stream_obj

  def Create(self, parent_ref, stream_id, args=None):
    """Creates a stream.

    Args:
      parent_ref: a Resource reference to a parent datastream.projects.locations
        resource for this stream.
      stream_id: str, the name of the resource to create.
      args: argparse.Namespace, The arguments that this command was invoked
        with.

    Returns:
      Operation: the operation for creating the stream.
    """
    stream = self._GetStream(stream_id, args)
    validate_only = args.validate_only
    force = args.force

    request_id = util.GenerateRequestId()
    create_req_type = self._messages.DatastreamProjectsLocationsStreamsCreateRequest
    create_req = create_req_type(
        stream=stream,
        streamId=stream.name,
        parent=parent_ref,
        requestId=request_id,
        validateOnly=validate_only,
        force=force)

    return self._service.Create(create_req)
