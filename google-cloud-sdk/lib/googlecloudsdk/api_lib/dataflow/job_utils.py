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
"""Helpers for writing commands interacting with jobs and their IDs.
"""

from apitools.base.py import exceptions

from googlecloudsdk.api_lib.dataflow import dataflow_util
from surface import dataflow as commands


class _JobViewSummary(object):

  def JobsGetRequest(self, context):
    return (context[commands.DATAFLOW_MESSAGES_MODULE_KEY]
            .DataflowProjectsJobsGetRequest
            .ViewValueValuesEnum.JOB_VIEW_SUMMARY)


class _JobViewAll(object):

  def JobsGetRequest(self, context):
    return (context[commands.DATAFLOW_MESSAGES_MODULE_KEY]
            .DataflowProjectsJobsGetRequest
            .ViewValueValuesEnum.JOB_VIEW_ALL)


JOB_VIEW_SUMMARY = _JobViewSummary()
JOB_VIEW_ALL = _JobViewAll()


def GetJob(context, job_ref, view=JOB_VIEW_SUMMARY):
  """Retrieve a specific view of a job.

  Args:
    context: Command context.
    job_ref: To retrieve.
    view: The job view to retrieve. Should be JOB_VIEW_SUMMARY or JOB_VIEW_ALL.

  Returns:
    The requested Job message.
  """
  apitools_client = context[commands.DATAFLOW_APITOOLS_CLIENT_KEY]

  request = job_ref.Request()
  request.view = view.JobsGetRequest(context)

  try:
    return apitools_client.projects_jobs.Get(request)
  except exceptions.HttpError as error:
    raise dataflow_util.MakeErrorMessage(error, job_ref.jobId,
                                         job_ref.projectId)


def GetJobForArgs(context, job, view=JOB_VIEW_ALL):
  """Retrieve a job for the JobRef specified in the arguments.

  Args:
    context: Command context.
    job: The job id to retrieve.
    view: The job view to retrieve. Should be JOB_VIEW_SUMMARY or JOB_VIEW_ALL.
        If not set will default to JOB_VIEW_ALL.

  Returns:
    The requested Job message.
  """
  job_ref = ExtractJobRef(context, job)
  return GetJob(context, job_ref, view=view)


def ArgsForJobRef(parser):
  """Register flags for specifying a single Job ID.

  Args:
    parser: The argparse.ArgParser to configure with job-filtering arguments.
  """
  parser.add_argument('job', metavar='JOB_ID', help='The job ID to operate on.')


def ArgsForJobRefs(parser, **kwargs):
  """Register flags for specifying jobs using positional job IDs.

  Args:
    parser: The argparse.ArgParser to configure with job ID arguments.
    **kwargs: Extra arguments to pass to the add_argument call.
  """
  parser.add_argument(
      'jobs', metavar='JOB', help='The jobs to operate on.', **kwargs)


def ExtractJobRef(context, job):
  """Extract the Job Ref for a command. Used with ArgsForJobRef.

  Args:
    context: The command context.
    job: The parsed job id that was provided to this invocation.
  Returns:
    A Job resource.
  """
  resources = context[commands.DATAFLOW_REGISTRY_KEY]
  return resources.Parse(job, collection='dataflow.projects.jobs')


def ExtractJobRefs(context, jobs):
  """Extract the Job Refs for a command. Used with ArgsForJobRefs.

  Args:
    context: The command context.
    jobs: The parsed list of job ids that were provided to this invocation.
  Returns:
    A list of job resources.
  """
  resources = context[commands.DATAFLOW_REGISTRY_KEY]
  return [resources.Parse(job, collection='dataflow.projects.jobs')
          for job in jobs]
