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

"""Utilities for building the dataflow CLI."""

import json
import re

from apitools.base.py import exceptions
from apitools.base.py import list_pager

from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

# Regular expression to match only metrics from Dataflow. Currently, this should
# match at least "dataflow" and "dataflow/v1b3". User metrics have an origin set
# as /^user/.
DATAFLOW_METRICS_RE = re.compile('^dataflow')

# Regular expression to only match watermark metrics.
WINDMILL_WATERMARK_RE = re.compile('^(.*)-windmill-(.*)-watermark')


JOBS_COLLECTION = 'dataflow.projects.jobs'


class ServiceException(calliope_exceptions.ToolException):
  """Generic exception related to calling the Dataflow service APIs."""

  def __init__(self, message):
    super(calliope_exceptions.ToolException, self).__init__(message)


def GetErrorMessage(error):
  """Extract the error message from an HTTPError.

  Args:
    error: The error exceptions.HttpError thrown by the API client.

  Returns:
    A string describing the error.
  """
  try:
    content_obj = json.loads(error.content)
    return content_obj.get('error', {}).get('message', '')
  except ValueError:
    log.err.Print(error.response)
    return 'Unknown error'


def MakeErrorMessage(error, job_id='', project_id=''):
  """Create a standard error message across commands.

  Args:
    error: The error exceptions.HttpError thrown by the API client.
    job_id: The job ID that was used in the command.
    project_id: The project ID that was used in the command.

  Returns:
    ServiceException
  """
  if job_id:
    job_id = ' with job ID [{0}]'.format(job_id)
  if project_id:
    project_id = ' in project [{0}]'.format(project_id)
  return ServiceException('Failed operation{0}{1}: {2}'.format(
      job_id, project_id, GetErrorMessage(error)))


def YieldExceptionWrapper(generator, job_id='', project_id=''):
  """Wraps a generator to catch any exceptions.

  Args:
    generator: The error exceptions.HttpError thrown by the API client.
    job_id: The job ID that was used in the command.
    project_id: The project ID that was used in the command.

  Yields:
    The generated object.

  Raises:
    ServiceException
  """
  try:
    while True:
      yield next(generator)
  except exceptions.HttpError as e:
    raise MakeErrorMessage(e, job_id, project_id)


def YieldFromList(service, request, limit=None, batch_size=100, field='items',
                  batch_size_attribute='maxResults', predicate=None, job_id='',
                  project_id=''):
  pager = list_pager.YieldFromList(
      service=service,
      request=request,
      limit=limit,
      batch_size=batch_size,
      field=field,
      batch_size_attribute=batch_size_attribute,
      predicate=predicate)
  return YieldExceptionWrapper(pager, job_id, project_id)


def JobsUriFunc(resource):
  """Transform a job resource into a URL string.

  Args:
    resource: The DisplayInfo job object

  Returns:
    URL to the job
  """

  ref = resources.REGISTRY.Parse(
      resource.id,
      params={'projectId': properties.VALUES.core.project.GetOrFail},
      collection=JOBS_COLLECTION)
  return ref.SelfLink()


def JobsUriFromId(job_id):
  """Transform a job ID into a URL string.

  Args:
    job_id: The job ID

  Returns:
    URL to the job
  """
  ref = resources.REGISTRY.Parse(
      job_id,
      params={'projectId': properties.VALUES.core.project.GetOrFail},
      collection=JOBS_COLLECTION)
  return ref.SelfLink()
