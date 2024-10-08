# -*- coding: utf-8 -*- #
# Copyright 2017 Google LLC. All Rights Reserved.
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
"""Common command-agnostic utility functions for sql export commands."""


def ParseBakType(sql_messages, bak_type):
  if bak_type is None:
    return (
        sql_messages.ExportContext.BakExportOptionsValue.BakTypeValueValuesEnum.FULL
    )
  return sql_messages.ExportContext.BakExportOptionsValue.BakTypeValueValuesEnum.lookup_by_name(
      bak_type.upper()
  )


def SqlExportContext(
    sql_messages,
    uri,
    database=None,
    table=None,
    offload=False,
    parallel=False,
    threads=None,
    clean=False,
    if_exists=False,
):
  """Generates the ExportContext for the given args, for exporting to SQL.

  Args:
    sql_messages: module, The messages module that should be used.
    uri: The URI of the bucket to export to; the output of the 'uri' arg.
    database: The list of databases to export from; the output of the
      '--database' flag.
    table: The list of tables to export from; the output of the '--table' flag.
    offload: bool, The export offload flag.
    parallel: Whether to use parallel export or not.
    threads: The number of threads to use. Only applicable for parallel export.
    clean: Whether to include SQL statement (DROP <object>) required to drop
    database objects prior to import; corresponds to the clean flag on pg_dump.
    Only applies to PostgreSQL non-parallel exports.
    if_exists: Whether to include SQL statement (IF EXISTS) to each drop
    statement produced by the clean flag; corresponds to the if-exists flag on
    pg_dump. Only applies to PostgreSQL non-parallel exports.


  Returns:
    ExportContext, for use in InstancesExportRequest.exportContext.
  """
  if parallel:
    return sql_messages.ExportContext(
        kind='sql#exportContext',
        uri=uri,
        databases=database or [],
        offload=offload,
        fileType=sql_messages.ExportContext.FileTypeValueValuesEnum.SQL,
        sqlExportOptions=sql_messages.ExportContext.SqlExportOptionsValue(
            tables=table or [], parallel=parallel, threads=threads
        ),
    )
  else:
    postgres_export_options = (
        sql_messages.
        ExportContext.SqlExportOptionsValue.PostgresExportOptionsValue(
            clean=clean, ifExists=if_exists
        )
    )
    return sql_messages.ExportContext(
        kind='sql#exportContext',
        uri=uri,
        databases=database or [],
        offload=offload,
        fileType=sql_messages.ExportContext.FileTypeValueValuesEnum.SQL,
        sqlExportOptions=sql_messages.ExportContext.SqlExportOptionsValue(
            tables=table or [],
            threads=threads,
            postgresExportOptions=postgres_export_options,
        ),
    )


def CsvExportContext(sql_messages,
                     uri,
                     database=None,
                     query=None,
                     offload=False,
                     quote=None,
                     escape=None,
                     fields_terminated_by=None,
                     lines_terminated_by=None):
  """Generates the ExportContext for the given args, for exporting to CSV.

  Args:
    sql_messages: module, The messages module that should be used.
    uri: The URI of the bucket to export to; the output of the 'uri' arg.
    database: The list of databases to export from; the output of the
      '--database' flag.
    query: The query string to use to generate the table; the output of the
      '--query' flag.
    offload: bool, The export offload flag.
    quote: character in Hex. The quote character for CSV format; the output of
      the '--quote' flag.
    escape: character in Hex. The escape character for CSV format; the output of
      the '--escape' flag.
    fields_terminated_by: character in Hex. The fields delimiter character for
      CSV format; the output of the '--fields-terminated-by' flag.
    lines_terminated_by: character in Hex. The lines delimiter character for CSV
      format; the output of the '--lines-terminated-by' flag.

  Returns:
    ExportContext, for use in InstancesExportRequest.exportContext.
  """
  return sql_messages.ExportContext(
      kind='sql#exportContext',
      uri=uri,
      databases=database or [],
      offload=offload,
      fileType=sql_messages.ExportContext.FileTypeValueValuesEnum.CSV,
      csvExportOptions=sql_messages.ExportContext.CsvExportOptionsValue(
          selectQuery=query,
          quoteCharacter=quote,
          escapeCharacter=escape,
          fieldsTerminatedBy=fields_terminated_by,
          linesTerminatedBy=lines_terminated_by))


def BakExportContext(
    sql_messages,
    uri,
    database,
    stripe_count,
    striped,
    bak_type,
    differential_base,
    export_log_start_time,
    export_log_end_time,
):
  """Generates the ExportContext for the given args, for exporting to BAK.

  Args:
    sql_messages: module, The messages module that should be used.
    uri: The URI of the bucket to export to; the output of the 'uri' arg.
    database: The list of databases to export from; the output of the
      '--database' flag.
    stripe_count: How many stripes to perform the export with.
    striped: Whether the export should be striped.
    bak_type: Type of bak file that will be exported. SQL Server only.
    differential_base: Whether the bak file export can be used as differential
      base for future differential backup. SQL Server only.
    export_log_start_time: start time of the log export. SQL Server only.
    export_log_end_time: end time of the log export. SQL Server only.

  Returns:
    ExportContext, for use in InstancesExportRequest.exportContext.
  """
  bak_export_options = sql_messages.ExportContext.BakExportOptionsValue()
  if striped is not None:
    bak_export_options.striped = striped
  if stripe_count is not None:
    bak_export_options.stripeCount = stripe_count

  bak_export_options.differentialBase = differential_base
  bak_export_options.bakType = ParseBakType(sql_messages, bak_type)

  if export_log_start_time is not None:
    bak_export_options.exportLogStartTime = export_log_start_time.strftime(
        '%Y-%m-%dT%H:%M:%S.%fZ'
    )

  if export_log_end_time is not None:
    bak_export_options.exportLogEndTime = export_log_end_time.strftime(
        '%Y-%m-%dT%H:%M:%S.%fZ'
    )

  return sql_messages.ExportContext(
      kind='sql#exportContext',
      uri=uri,
      databases=database,
      fileType=sql_messages.ExportContext.FileTypeValueValuesEnum.BAK,
      bakExportOptions=bak_export_options)


def TdeExportContext(
    sql_messages,
    certificate,
    cert_path,
    pvk_path,
    pvk_password,
):
  """Generates the ExportContext for the given args, for exporting to TDE.

  Args:
    sql_messages: module, The messages module that should be used.
    certificate: The certificate name; the output of the
      `--certificate` flag.
    cert_path: The certificate path in Google Cloud Storage; the output of the
      `--cert-path` flag.
    pvk_path: The private key path in Google Cloud Storage; the output of the
      `--pvk-path` flag.
    pvk_password: The password that encrypts the private key; the output
      of the `--pvk-password` or `--prompt-for-pvk-password` flag.

  Returns:
    ExportContext, for use in InstancesImportRequest.exportContext.
  """
  tde_export_options = sql_messages.ExportContext.TdeExportOptionsValue(
      name=certificate,
      certificatePath=cert_path,
      privateKeyPath=pvk_path,
      privateKeyPassword=pvk_password)

  return sql_messages.ExportContext(
      kind='sql#exportContext',
      fileType=sql_messages.ExportContext.FileTypeValueValuesEnum.TDE,
      tdeExportOptions=tde_export_options)
