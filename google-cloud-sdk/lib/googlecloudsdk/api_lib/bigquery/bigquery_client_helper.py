# Copyright 2014 Google Inc. All Rights Reserved.

"""Utility methods used in multiple gcloud bigquery commands.
"""

import re
import time
from googlecloudsdk.api_lib.bigquery import bigquery
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.third_party.apitools.base import py as apitools_base


_DELIMITER_MAP = {
    'tab': '\t',
    '\\t': '\t',
}


_DATE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'  # passed to time.strftime


def ToLowerCamel(name):
  """Convert a name with underscores to camelcase."""
  return re.sub('_[a-z]', lambda match: match.group(0)[1].upper(), name)


def DatasetExists(apitools_client, bigquery_messages, reference):
  request = bigquery_messages.BigqueryDatasetsGetRequest(
      datasetId=reference.datasetId,
      projectId=reference.projectId)
  try:
    apitools_client.datasets.Get(request)
    return True
  except apitools_base.HttpError as server_error:
    try:
      raise bigquery.Error.ForHttpError(server_error)
    except bigquery.NotFoundError:
      return False
    except bigquery.Error:
      raise


def TableExists(apitools_client, bigquery_messages, reference):
  request = bigquery_messages.BigqueryTablesGetRequest(
      datasetId=reference.datasetId,
      projectId=reference.projectId,
      tableId=reference.tableId)
  try:
    apitools_client.tables.Get(request)
    return True
  except apitools_base.HttpError as server_error:
    try:
      raise bigquery.Error.ForHttpError(server_error)
    except bigquery.NotFoundError:
      return False
    except bigquery.Error:
      raise


def NormalizeFieldDelimiter(field_delimiter):
  """Validates and returns the correct field_delimiter."""
  # The only non-string delimiter we allow is None, which represents
  # no field delimiter specified by the user.
  if field_delimiter is None:
    return field_delimiter
  try:
    # We check the field delimiter flag specifically, since a
    # mis-entered Thorn character generates a difficult to
    # understand error during request serialization time.
    _ = field_delimiter.decode('UTF-8')
  except UnicodeDecodeError:
    raise exceptions.ToolException(
        'The field delimiter flag is not valid. Flags must be '
        'specified in your default locale. For example, '
        'the Latin 1 representation of Thorn is byte code FE, '
        'which in the UTF-8 locale would be expressed as C3 BE.')

  # Allow TAB and \\t substitution.
  key = field_delimiter.lower()
  return _DELIMITER_MAP.get(key, field_delimiter)


def NormalizeTextualFormat(user_specified_format):
  """Translates the format name specified in a flag into internal form.

  For example, 'newline-delimited-json' is translated into the form expected
  in job configurations, 'NEWLINE_DELIMITED_JSON'.

  Args:
    user_specified_format: the flag value, or None

  Returns:
    If user_specified_format is None, None; otherwise, the form of the flag
    value expected in job configurations.
  """
  if user_specified_format:
    return user_specified_format.upper().replace('-', '_')
  else:
    return None


def FormatTime(millis_since_epoch):
  return time.strftime(
      _DATE_TIME_FORMAT, time.localtime(millis_since_epoch / 1000))
