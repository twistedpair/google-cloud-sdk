# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Helper functions for the ml client to use command_lib.logs.stream."""
import copy

from apitools.base.py import encoding
from googlecloudsdk.core import apis
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

LOG_FORMAT = ('value('
              'severity,'
              'timestamp.date("%Y-%m-%d %H:%M:%S %z",tz="LOCAL"), '
              'task_name,'
              'trial_id,'
              'message'
              ')'
             )


def LogFilters(job_id, task_name=None):
  """Returns filters for log fetcher to use.

  Args:
    job_id: String id of job.
    task_name: String name of task.

  Returns:
    A list of filters to be passed to the logging API.
  """
  filters = ['resource.type="ml_job"',
             'resource.labels.job_id="{0}"'.format(job_id)]
  if task_name:
    filters.append('resource.labels.task_name="{0}"'.format(task_name))
  return filters


def MakeContinueFunction(job_id):
  """Returns a function to decide if log fetcher should continue polling.

  Args:
    job_id: String id of job.

  Returns:
    A one-argument function decides if log fetcher should continue.
  """
  def CheckJobNotFinished(periods_without_logs):
    """Checks if we haven't polled enough and then if job is not finished.

    Args:
      periods_without_logs: integer number of empty polls.

    Returns:
      True if we haven't tried polling more than once or if job is not finished.
    """
    client = apis.GetClientInstance('ml', 'v1beta1')
    if periods_without_logs > 1:
      # TODO(b/34171242): Use JobsClient() instead.
      proj_id = properties.VALUES.core.project.Get(required=True)
      res = resources.REGISTRY.Parse(job_id, collection='ml.projects.jobs',
                                     params={'projectsId': proj_id})
      req = client.MESSAGES_MODULE.MlProjectsJobsGetRequest(
          projectsId=res.projectsId, jobsId=res.jobsId)
      resp = client.projects_jobs.Get(req)
      return resp.endTime is None
    else:
      return True
  return CheckJobNotFinished


def SplitMultiline(log_generator, allow_multiline=False):
  """Splits the dict output of logs into multiple lines.

  Args:
    log_generator: iterator that returns a an ml log in dict format.
    allow_multiline: Tells us if logs with multiline messages are okay or not.

  Yields:
    Single-line ml log dictionaries.
  """
  for log in log_generator:
    log_dict = _EntryToDict(log)
    if allow_multiline:
      yield log_dict
    else:
      messages = log_dict['message'].splitlines()
      if not messages:
        messages = ['']
      for message in messages:
        single_line_log = copy.deepcopy(log_dict)
        single_line_log['message'] = message
        yield single_line_log


def _EntryToDict(log_entry):
  """Converts a log entry to a dictionary."""
  output = {}
  output['severity'] = log_entry.severity.name
  output['timestamp'] = log_entry.timestamp
  label_attributes = _GetLabelAttributes(log_entry)
  output['task_name'] = label_attributes['task_name']
  if 'trial_id' in label_attributes:
    output['trial_id'] = label_attributes['trial_id']
  output['message'] = ''
  if log_entry.jsonPayload is not None:
    json_data = _ToDict(log_entry.jsonPayload)
    # 'message' contains a free-text message that we want to pull out of the
    # JSON.
    if 'message' in json_data:
      if json_data['message']:
        output['message'] += json_data['message']
      del json_data['message']
    # Don't put 'levelname' in the JSON, since it duplicates the
    # information in log_entry.severity.name
    if 'levelname' in json_data:
      del json_data['levelname']
    output['json'] = json_data
  elif log_entry.textPayload is not None:
    output['message'] += str(log_entry.textPayload)
  elif log_entry.protoPayload is not None:
    output['json'] = encoding.MessageToDict(log_entry.protoPayload)
  return output


def _GetLabelAttributes(log_entry):
  """Reads the label attributes of the given log entry."""
  label_attributes = {'task_name': 'unknown_task'}
  if not hasattr(log_entry, 'labels'):
    return label_attributes
  labels = _ToDict(log_entry.labels)
  if labels.get('ml.googleapis.com/task_name') is not None:
    label_attributes['task_name'] = labels['ml.googleapis.com/task_name']
  if labels.get('ml.googleapis.com/trial_id') is not None:
    label_attributes['trial_id'] = labels['ml.googleapis.com/trial_id']
  return label_attributes


def _ToDict(message):
  if not message:
    return {}
  if isinstance(message, dict):
    return message
  else:
    return encoding.MessageToDict(message)
