# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Utilities for dealing with ML jobs API."""
import copy
import datetime
import time

from apitools.base.py import encoding
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.logging import common as logging_common
from googlecloudsdk.core import apis
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import times
import yaml


def Cancel(job):
  """Cancels given job."""
  client = apis.GetClientInstance('ml', 'v1beta1')
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  res = resources.REGISTRY.Parse(job, collection='ml.projects.jobs')
  req = msgs.MlProjectsJobsCancelRequest(
      projectsId=res.projectsId, jobsId=res.Name())
  resp = client.projects_jobs.Cancel(req)
  return resp


def Get(job):
  client = apis.GetClientInstance('ml', 'v1beta1')
  res = resources.REGISTRY.Parse(job, collection='ml.projects.jobs')
  req = res.Request()
  resp = client.projects_jobs.Get(req)
  return resp


class LogPosition(object):
  """Tracks a position in the log.

  Log messages are sorted by timestamp.  Within a given timestamp, logs will be
  returned in order of insert_id.
  """

  def __init__(self):
    self.timestamp = '1970-01-01T01:00:00.000000000Z'
    self.insert_id = ''

  def Update(self, timestamp, insert_id):
    """Update the log position based on new log entry data.

    Args:
        timestamp: the timestamp of the message we just read, as an RFC3339
                   string.
        insert_id: the insert id of the message we just read.

    Returns:
        True if the position was updated; False if not.
    """
    if timestamp < self.timestamp:
      # The message is behind this LogPosition.  No update required.
      return False
    elif timestamp == self.timestamp:
      # When the timestamp is the same, we need to move forward the insert id.
      if insert_id > self.insert_id:
        self.insert_id = insert_id
        return True
      return False
    else:
      # Once we see a new timestamp, move forward the minimum time that we're
      # willing to accept and clear the insert_id field.
      self.insert_id = ''
      self.timestamp = timestamp
      return True

  def GetFilterLowerBound(self):
    """The log message filter which keeps out messages which are too old.

    Returns:
        The lower bound filter text that we should use.
    """

    if self.insert_id:
      return '((timestamp="{0}" AND insertId>"{1}") OR timestamp>"{2}")'.format(
          self.timestamp, self.insert_id, self.timestamp)
    else:
      return 'timestamp>="{0}"'.format(self.timestamp)

  def GetFilterUpperBound(self, now):
    """The log message filter which keeps out messages which are too new.

    Args:
        now: The current time, as a datetime object.

    Returns:
        The upper bound filter text that we should use.
    """

    tzinfo = times.ParseDateTime(self.timestamp).tzinfo
    now = now.replace(tzinfo=tzinfo)
    upper_bound = now - datetime.timedelta(seconds=5)
    return 'timestamp<"{0}"'.format(
        times.FormatDateTime(upper_bound, '%Y-%m-%dT%H:%M:%S.%6f%Ez'))


class ApiAccessor(object):
  """Handles making calls to cloud APIs."""

  LOG_BATCH_SIZE = 5000

  def __init__(self, job_id):
    self.job_id = job_id
    self.client = apis.GetClientInstance('ml', 'v1beta1')

  def GetLogs(self, log_position):
    """Retrieve a batch of logs."""
    filters = ['resource.type="ml_job"',
               'resource.labels.job_id="{0}"'.format(self.job_id),
               log_position.GetFilterLowerBound(),
               log_position.GetFilterUpperBound(datetime.datetime.utcnow())]
    return logging_common.FetchLogs(
        log_filter=' AND '.join(filters),
        order_by='ASC',
        limit=self.LOG_BATCH_SIZE)

  def CheckJobFinished(self):
    """Returns True if the job is finished."""
    res = resources.REGISTRY.Parse(self.job_id, collection='ml.projects.jobs')
    req = res.Request()
    resp = self.client.projects_jobs.Get(req)
    return resp.endTime is not None


class LogFetcher(object):
  """A class which fetches job logs."""

  def __init__(self, job_id, polling_interval, allow_multiline_logs,
               api_accessor):
    self.job_id = job_id
    self.polling_interval = polling_interval
    self.log_position = LogPosition()
    self.allow_multiline_logs = allow_multiline_logs
    self.api_accessor = api_accessor

  def YieldLogs(self):
    """Return log messages from the given job.

    YieldLogs returns messages from the given job, in time order.  If the job
    is still running when we finish printing all the logs that exist, we will
    go into a polling loop where we check periodically for new logs.  On the
    other hand, if the job has ended, YieldLogs will raise StopException when
    there are no more logs to display.

    The log message storage system is optimized for throughput, not for
    immediate, in-order visibility.  It may take several seconds for a new log
    message to become visible.  To work around this limitation, we refrain from
    printing out log messages which are newer than 5 seconds old.

    Log messages are sorted by timestamp.  Log messages with the same timestamp
    are further sorted by their unique insertId.  By using the combination of
    timestamp and insertId, we can ensure that each query returns a set of log
    messages that we haven't seen before.

    Yields:
        A dictionary containing the fields of the log message.
    """

    while True:
      log_retriever = self.api_accessor.GetLogs(self.log_position)
      made_progress = False
      while True:
        try:
          log_entry = log_retriever.next()
        except StopIteration:
          break
        if not self.log_position.Update(log_entry.timestamp,
                                        log_entry.insertId):
          continue
        made_progress = True
        multiline_log_dict = self.EntryToDict(log_entry)
        if self.allow_multiline_logs:
          yield multiline_log_dict
        else:
          message_lines = multiline_log_dict['message'].splitlines()
          for message_line in message_lines:
            single_line_dict = copy.deepcopy(multiline_log_dict)
            single_line_dict['message'] = message_line
            yield single_line_dict
      if not made_progress:
        if self.api_accessor.CheckJobFinished():
          raise StopIteration
        time.sleep(self.polling_interval)

  def EntryToDict(self, log_entry):
    """Convert a log entry to a dictionary."""
    output = {}
    output['severity'] = log_entry.severity.name
    output['timestamp'] = log_entry.timestamp
    label_attributes = self.GetLabelAttributes(log_entry)
    output['task_name'] = label_attributes['task_name']
    if 'trial_id' in label_attributes:
      output['trial_id'] = label_attributes['trial_id']
    output['message'] = ''
    if log_entry.jsonPayload is not None:
      json_data = ToDict(log_entry.jsonPayload)
      # 'message' contains a free-text message that we want to pull out of the
      # JSON.
      if 'message' in json_data:
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

  def GetLabelAttributes(self, log_entry):
    """Read the label attributes of the given log entry."""
    label_attributes = {'task_name': 'unknown_task'}
    if not hasattr(log_entry, 'labels'):
      return label_attributes
    labels = ToDict(log_entry.labels)
    if labels.get('ml.googleapis.com/task_name') is not None:
      label_attributes['task_name'] = labels['ml.googleapis.com/task_name']
    if labels.get('ml.googleapis.com/trial_id') is not None:
      label_attributes['trial_id'] = labels['ml.googleapis.com/trial_id']
    return label_attributes


def ToDict(message):
  if not message:
    return {}
  if isinstance(message, dict):
    return message
  else:
    return encoding.MessageToDict(message)


def StreamLogs(args):
  log_fetcher = LogFetcher(job_id=args.job,
                           polling_interval=args.polling_interval,
                           allow_multiline_logs=args.allow_multiline_logs,
                           api_accessor=ApiAccessor(args.job))
  return log_fetcher.YieldLogs()


def List():
  client = apis.GetClientInstance('ml', 'v1beta1')
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  req = msgs.MlProjectsJobsListRequest(
      projectsId=properties.VALUES.core.project.Get())
  return list_pager.YieldFromList(
      client.projects_jobs, req, field='jobs', batch_size_attribute='pageSize')


def Create(job):
  client = apis.GetClientInstance('ml', 'v1beta1')
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  req = msgs.MlProjectsJobsCreateRequest(
      projectsId=properties.VALUES.core.project.Get(),
      googleCloudMlV1beta1Job=job)
  resp = client.projects_jobs.Create(req)
  return resp


def BuildTrainingJob(path=None,
                     module_name=None,
                     job_name=None,
                     trainer_uri=None,
                     region=None,
                     user_args=None):
  """Builds a GoogleCloudMlV1beta1Job from a config file and/or flag values.

  Args:
      path: path to a yaml configuration file
      module_name: value to set for moduleName field (overrides yaml file)
      job_name: value to set for jobName field (overrides yaml file)
      trainer_uri: List of values to set for trainerUri field (overrides yaml
        file)
      region: compute region in which to run the job (overrides yaml file)
      user_args: [str]. A list of arguments to pass through to the job.
      (overrides yaml file)
  Returns:
      A constructed GoogleCloudMlV1beta1Job object.
  """
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  request_class = msgs.GoogleCloudMlV1beta1Job
  obj = request_class()
  if path:
    with files.Context(open(path)) as config_file:
      data = yaml.load(config_file)
    if data:
      obj = encoding.DictToMessage(data, request_class)
  if not obj.trainingInput:
    obj.trainingInput = msgs.GoogleCloudMlV1beta1TrainingInput()
  if module_name:
    obj.trainingInput.pythonModule = module_name
  if user_args:
    obj.trainingInput.args = user_args
  if job_name:
    obj.jobId = job_name
  if trainer_uri:
    obj.trainingInput.packageUris = trainer_uri
  if region:
    obj.trainingInput.region = region
  return obj


def BuildBatchPredictionJob(job_name=None,
                            model_name=None,
                            version_name=None,
                            input_paths=None,
                            data_format=None,
                            output_path=None,
                            region=None):
  """Builds a GoogleCloudMlV1beta1Job for batch prediction from flag values.

  Args:
      job_name: value to set for jobName field
      model_name: value to set for modelName field
      version_name: value to set for versionName field
      input_paths: list of input files
      data_format: format of the input files
      output_path: single value for the output location
      region: compute region in which to run the job
  Returns:
      A constructed GoogleCloudMlV1beta1Job object.
  """
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  request_class = msgs.GoogleCloudMlV1beta1Job
  obj = request_class()
  obj.predictionInput = msgs.GoogleCloudMlV1beta1PredictionInput()

  obj.jobId = job_name
  project_id = properties.VALUES.core.project.Get()
  if version_name:
    # pylint: disable=g-backslash-continuation
    obj.predictionInput.versionName = 'projects/{0}/models/{1}/versions/{2}'. \
        format(project_id, model_name, version_name)
  else:
    # pylint: disable=g-backslash-continuation
    obj.predictionInput.modelName = \
        'projects/{0}/models/{1}'.format(project_id, model_name)
  obj.predictionInput.inputPaths = input_paths
  data_format_dict = {'TEXT': msgs.GoogleCloudMlV1beta1PredictionInput.
                              DataFormatValueValuesEnum.TEXT,
                      'TF_RECORD': msgs.GoogleCloudMlV1beta1PredictionInput.
                                   DataFormatValueValuesEnum.TF_RECORD}
  obj.predictionInput.dataFormat = data_format_dict[data_format]
  obj.predictionInput.outputPath = output_path
  obj.predictionInput.region = region
  return obj
