# -*- coding: utf-8 -*- #
# Copyright 2018 Google LLC. All Rights Reserved.
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
"""General BQ surface command utilites for python commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.command_lib.util.args import resource_args
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import yaml
import six


DEFAULT_MAX_QUERY_RESULTS = 1000


class BqJobPoller(waiter.OperationPoller):
  """Poller for managing Bq Jobs."""

  def __init__(
      self,
      job_service,
      result_service,
      max_query_results=DEFAULT_MAX_QUERY_RESULTS,
  ):
    """Sets up poller for BigQuery Jobs.

    Args:
      job_service: apitools.base.py.base_api.BaseApiService, api service for
        retrieving information about ongoing job.
      result_service: apitools.base.py.base_api.BaseApiService, api service for
        retrieving created result of initiated operation.
      max_query_results: maximum number of records to return from a query job.
    """
    self.result_service = result_service
    self.job_service = job_service
    self.max_query_results = max_query_results

  def IsDone(self, job):
    """Overrides."""
    if job.status.state == 'DONE':
      if job.status.errorResult:
        raise waiter.OperationError(job.status.errorResult.message)
      return True
    return False

  def Poll(self, job_ref):
    """Overrides.

    Args:
      job_ref: googlecloudsdk.core.resources.Resource.

    Returns:
      fetched job message.
    """
    request_type = self.job_service.GetRequestType('Get')
    return self.job_service.Get(
        request_type(jobId=job_ref.Name(), projectId=job_ref.Parent().Name())
    )

  def GetResult(self, job):
    """Overrides to get the response from the completed job by job type.

    Args:
      job: api_name_messages.Job.

    Returns:
      the 'response' field of the job.
    """
    request_type = self.result_service.GetRequestType('Get')
    job_type = job.configuration.jobType

    if job_type == 'COPY':
      result_table = job.configuration.copy.destinationTable
      request = request_type(
          datasetId=result_table.datasetId,
          tableId=result_table.tableId,
          projectId=result_table.projectId,
      )
    elif job_type == 'LOAD':
      result_table = job.configuration.load.destinationTable
      request = request_type(
          datasetId=result_table.datasetId,
          tableId=result_table.tableId,
          projectId=result_table.projectId,
      )
    elif job_type == 'QUERY':
      request_type = self.result_service.GetRequestType('GetQueryResults')
      request = request_type(
          jobId=job.jobReference.jobId,
          maxResults=self.max_query_results,
          projectId=job.jobReference.projectId,
      )
      return self.result_service.GetQueryResults(request)
    else:  # EXTRACT OR UNKNOWN type
      return job

    return self.result_service.Get(request)


class BqMigrationWorkflowPoller(waiter.OperationPoller):
  """Poller for managing BigQuery Migration Workflows."""

  def __init__(
      self,
      migration_service,
  ):
    """Sets up poller for generic long running processes.

    Args:
      migration_service: apitools.base.py.base_api.BaseApiService, api service
        for retrieving information about migration workflows.
    """
    self.migration_service = migration_service

  def IsDone(self, migration_workflow):
    """Overrides."""
    return str(migration_workflow.state) == 'COMPLETED'

  def Poll(self, migration_workflow_ref):
    """Overrides.

    Args:
      migration_workflow_ref: googlecloudsdk.core.resources.Resource.

    Returns:
      fetched migration workflow message.
    """
    request_type = self.migration_service.GetRequestType('Get')
    request = request_type(name=migration_workflow_ref.RelativeName())
    res = self.migration_service.Get(request)
    return res

  def GetResult(self, migration_workflow):
    """Overrides to get the response from the completed job by job type.

    Args:
      migration_workflow: api_name_messages.MigrationWorkflow.

    Returns:
      the 'response' field of the Operation.
    """
    request_type = self.migration_service.GetRequestType('Get')
    request = request_type(name=migration_workflow.name)
    return self.migration_service.Get(request)


def GetResourceFromFile(file_path, resource_message_type):
  """Returns the resource message and update fields in file."""
  try:
    resource_to_parse = yaml.load_path(file_path)
  except yaml.YAMLParseError as e:
    raise exceptions.BadFileException(
        'File [{0}] cannot be parsed. {1}'.format(file_path, six.text_type(e))
    )
  except yaml.FileLoadError as e:
    raise exceptions.BadFileException(
        'File [{0}] cannot be opened or read. {1}'.format(
            file_path, six.text_type(e)
        )
    )

  if not isinstance(resource_to_parse, dict):
    raise exceptions.BadFileException(
        'File [{0}] is not a properly formatted YAML or JSON file.'.format(
            file_path
        )
    )

  try:
    resource = encoding.PyValueToMessage(
        resource_message_type, resource_to_parse
    )
  except AttributeError as e:
    raise exceptions.BadFileException(
        'File [{0}] is not a properly formatted YAML or JSON file. {1}'.format(
            file_path, six.text_type(e)
        )
    )

  return resource


def ProcessTableCopyOverwrite(ref, args, request):
  """Process the overwrite flag on tables copy."""
  del ref  # Unused
  if args.overwrite:
    request.job.configuration.copy.writeDisposition = 'WRITE_TRUNCATE'
  return request


def ProcessTableCopyConfiguration(ref, args, request):
  """Build JobConfigurationTableCopy from request resource args."""
  del ref  # Unused
  source_ref = args.CONCEPTS.source.Parse()
  destination_ref = args.CONCEPTS.destination.Parse()
  arg_utils.SetFieldInMessage(
      request,
      'job.configuration.copy.destinationTable.datasetId',
      destination_ref.Parent().Name(),
  )
  arg_utils.SetFieldInMessage(
      request,
      'job.configuration.copy.destinationTable.projectId',
      destination_ref.projectId,
  )
  arg_utils.SetFieldInMessage(
      request,
      'job.configuration.copy.destinationTable.tableId',
      destination_ref.Name(),
  )
  arg_utils.SetFieldInMessage(
      request,
      'job.configuration.copy.sourceTable.datasetId',
      source_ref.Parent().Name(),
  )
  arg_utils.SetFieldInMessage(
      request,
      'job.configuration.copy.sourceTable.projectId',
      source_ref.projectId,
  )
  arg_utils.SetFieldInMessage(
      request, 'job.configuration.copy.sourceTable.tableId', source_ref.Name()
  )
  return request


# Resource Argument utils
def GetTableCopyResourceArgs():
  """Get Table resource args (source, destination) for copy command."""
  table_spec_data = yaml_data.ResourceYAMLData.FromPath('bq.table')
  arg_specs = [
      resource_args.GetResourcePresentationSpec(
          verb='to copy from',
          name='source',
          required=True,
          prefixes=True,
          attribute_overrides={'table': 'source'},
          positional=False,
          resource_data=table_spec_data.GetData(),
      ),
      resource_args.GetResourcePresentationSpec(
          verb='to copy to',
          name='destination',
          required=True,
          prefixes=True,
          attribute_overrides={'table': 'destination'},
          positional=False,
          resource_data=table_spec_data.GetData(),
      ),
  ]
  fallthroughs = {
      '--source.dataset': ['--destination.dataset'],
      '--destination.dataset': ['--source.dataset'],
  }
  return [concept_parsers.ConceptParser(arg_specs, fallthroughs)]
