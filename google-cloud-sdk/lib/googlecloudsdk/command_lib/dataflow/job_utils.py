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

from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


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
      'jobs', metavar='JOB_ID', help='The job IDs to operate on.', **kwargs)


def ExtractJobRef(job):
  """Extract the Job Ref for a command. Used with ArgsForJobRef.

  Args:
    job: The parsed job id that was provided to this invocation.
  Returns:
    A Job resource.
  """
  return resources.REGISTRY.Parse(
      job,
      params={'projectId': properties.VALUES.core.project.GetOrFail},
      collection='dataflow.projects.jobs')


def ExtractJobRefs(jobs):
  """Extract the Job Refs for a command. Used with ArgsForJobRefs.

  Args:
    jobs: The parsed list of job ids that were provided to this invocation.
  Returns:
    A list of job resources.
  """
  return [resources.REGISTRY.Parse(
      job,
      params={'projectId': properties.VALUES.core.project.GetOrFail},
      collection='dataflow.projects.jobs') for job in jobs]
