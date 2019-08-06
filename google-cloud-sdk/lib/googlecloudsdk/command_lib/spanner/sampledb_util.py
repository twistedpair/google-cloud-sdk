# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Provides helper methods for creating a Spanner Sample Database."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import csv
import io

from googlecloudsdk.api_lib.spanner import database_sessions
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.command_lib.spanner import write_util
from googlecloudsdk.core.util import encoding
import six


def GetSchemaFromGCS(bucket, schema_file):
  """Retrieve the schema from a GCS Bucket.

  Args:
    bucket: String. The name of the bucket to read from.
    schema_file: String. The name of schema file to use.

  Returns:
    A string containing the schema in question.
  """
  client = storage_api.StorageClient()

  schema_object = storage_util.ObjectReference.FromUrl(
      '{bucket}/{schema}'.format(bucket=bucket, schema=schema_file))

  schema_ref = client.ReadObject(schema_object)
  schema = schema_ref.getvalue()

  return schema.decode('utf-8')


def ReadCSVFileFromGCS(bucket, csv_file):
  """Read a CSV file from a bucket.

  Args:
    bucket: String. The name of the bucket to read from.
    csv_file: String. The name of csv file located in a GCS Bucket.

  Returns:
    A 2D list of data.
    Example:
      table_data[0] = ['1', 'Some name', 'Some value']
      table_data[1] = ['2', 'Some other name', 'Some value']
  """
  client = storage_api.StorageClient()

  table_object_reference = storage_util.ObjectReference.FromUrl(
      '{bucket}/{table}'.format(bucket=bucket, table=csv_file))
  data = client.ReadObject(table_object_reference)

  table_data = []
  #  Different implementation due to differences in strings
  #  between Py2 and Py3
  if six.PY3:
    data = io.TextIOWrapper(data, encoding='utf-8')
  reader = csv.reader(data)
  for row in reader:
    table_data.append(row)

  return table_data


def CreateInsertMutationFromCSVRow(table, data, columns):
  """Create an INSERT mutation from a CSV row of data.

  Args:
    table: A write_util.Table object
    data: A list containing data from a single row from a CSV file. Each element
      corresponds to a string.
    columns: An ordered dictionary containing column names {col -> data_type}

  Returns:
    A single INSERT mutation
  """
  col_to_data = collections.OrderedDict()

  for col, data_cell in zip(columns, data):
    col_to_data[col] = encoding.Decode(data_cell)

  valid_data = write_util.ValidateArrayInput(table, col_to_data)
  mutation = database_sessions.MutationFactory.Insert(table, valid_data)

  return mutation
