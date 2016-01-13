# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Conversions between types used in API messages and internal types."""

from googlecloudsdk.core import resources


def DatasetResourceToReference(bigquery_messages, resource):
  """Converts a Resource for a dataset to a DatasetReference message.

  Args:
    bigquery_messages: The messages module for the Bigquery API.
    resource: the Resource

  Returns:
    the message
  """
  return bigquery_messages.DatasetReference(
      projectId=resource.projectId, datasetId=resource.datasetId)


def TableResourceToReference(bigquery_messages, resource):
  """Converts a Resource for a table to a TableReference message.

  Args:
    bigquery_messages: The messages module for the Bigquery API.
    resource: the Resource

  Returns:
    the message
  """
  return bigquery_messages.TableReference(
      projectId=resource.projectId,
      datasetId=resource.datasetId,
      tableId=resource.tableId)


def JobResourceToReference(bigquery_messages, resource):
  """Converts a Resource for a job to a JobReference message.

  Args:
    bigquery_messages: The messages module for the Bigquery API.
    resource: the Resource

  Returns:
    the message
  """
  return bigquery_messages.JobReference(
      projectId=resource.projectId, jobId=resource.jobId)


def JobReferenceToResource(reference):
  """Converts a JobReference message to a Resource for a job.

  Args:
    reference: the JobReference message

  Returns:
    the resource
  """
  return resources.Create(
      'bigquery.jobs', projectId=reference.projectId, jobId=reference.projectId)
