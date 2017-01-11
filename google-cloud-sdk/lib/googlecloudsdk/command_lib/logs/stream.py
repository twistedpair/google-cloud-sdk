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
"""Utilities for streaming logs."""
import copy
import datetime
import time

from apitools.base.py import encoding
from googlecloudsdk.api_lib.logging import common as logging_common
from googlecloudsdk.core import apis
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import times


class LogPosition(object):
  """Tracks a position in the log.

  Log messages are sorted by timestamp.  Within a given timestamp, logs will be
  returned in order of insert_id.
  """

  def __init__(self):
    self.timestamp = '1970-01-01T01:00:00.000000000Z'
    self.insert_id = ''
    self.need_insert_id_in_lb_filter = False

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
        self.need_insert_id_in_lb_filter = True
        return True
      return False
    else:
      # Once we see a new timestamp, move forward the minimum time that we're
      # willing to accept.
      self.need_insert_id_in_lb_filter = False
      self.insert_id = insert_id
      self.timestamp = timestamp
      return True

  def GetFilterLowerBound(self):
    """The log message filter which keeps out messages which are too old.

    Returns:
        The lower bound filter text that we should use.
    """

    if self.need_insert_id_in_lb_filter:
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


class LogFetcher(object):
  """A class which fetches job logs."""

  LOG_BATCH_SIZE = 5000
  LOG_FORMAT = """\
      value(
          severity,
          timestamp.date("%Y-%m-%d %H:%M:%S %z",tz="LOCAL"),
          task_name,
          trial_id,
          message
      )"""

  def __init__(self, job_id, polling_interval, allow_multiline_logs,
               task_name=None):
    self.job_id = job_id
    self.polling_interval = polling_interval
    self.log_position = LogPosition()
    self.allow_multiline_logs = allow_multiline_logs
    self.client = apis.GetClientInstance('ml', 'v1beta1')
    self.task_name = task_name

  def GetLogs(self, log_position, utcnow=None):
    """Retrieve a batch of logs."""
    if utcnow is None:
      utcnow = datetime.datetime.utcnow()
    filters = ['resource.type="ml_job"',
               'resource.labels.job_id="{0}"'.format(self.job_id),
               log_position.GetFilterLowerBound(),
               log_position.GetFilterUpperBound(utcnow)]
    if self.task_name:
      filters.append('resource.labels.task_name="{}"'.format(self.task_name))
    return logging_common.FetchLogs(
        log_filter=' AND '.join(filters),
        order_by='ASC',
        limit=self.LOG_BATCH_SIZE)

  def CheckJobFinished(self):
    """Returns True if the job is finished."""
    res = resources.REGISTRY.Parse(self.job_id, collection='ml.projects.jobs')
    req = self.client.MESSAGES_MODULE.MlProjectsJobsGetRequest(
        projectsId=res.projectsId, jobsId=res.jobsId)
    resp = self.client.projects_jobs.Get(req)
    return resp.endTime is not None

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

    periods_without_progress = 0
    last_progress_time = datetime.datetime.utcnow()
    while True:
      log_retriever = self.GetLogs(log_position=self.log_position)
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
        last_progress_time = datetime.datetime.utcnow()
        multiline_log_dict = self.EntryToDict(log_entry)
        if self.allow_multiline_logs:
          yield multiline_log_dict
        else:
          message_lines = multiline_log_dict['message'].splitlines()
          if not message_lines:
            message_lines = ['']
          for message_line in message_lines:
            single_line_dict = copy.deepcopy(multiline_log_dict)
            single_line_dict['message'] = message_line
            yield single_line_dict
      if made_progress:
        periods_without_progress = 0
      else:
        # If our last log query was the second in a row to make no progress,
        # and the last progress was more than 5 seconds ago, check the job
        # status to make sure that it's still running.
        # If it is not, terminate the stream-logs command.
        periods_without_progress += 1
        if periods_without_progress > 1:
          if last_progress_time + datetime.timedelta(
              seconds=5) <= datetime.datetime.utcnow():
            if self.CheckJobFinished():
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
