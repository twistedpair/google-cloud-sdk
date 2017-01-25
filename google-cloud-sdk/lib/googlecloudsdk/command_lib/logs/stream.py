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
"""Logic for streaming logs.

We implement streaming with two important implementation details.  First,
we use polling because Cloud Logging does not support streaming. Second, we
have no guarantee that we will receive logs in chronological order.
This is because clients can emit logs with chosen timestamps.  However,
we want to generate an ordered list of logs.  So, we choose to not fetch logs
in the most recent N seconds.  We also decided to skip logs that are returned
too late (their timestamp is more than N seconds old).
"""
import datetime
import time

from googlecloudsdk.api_lib.logging import common as logging_common
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

  def __init__(self, filters=None, polling_interval=5, continue_func=None):
    """Initializes the LogFetcher.

    Args:
      filters: list of string filters used in the API call.
      polling_interval: amount of time to sleep between each poll.
      continue_func: One-arg function that takes in the number of empty polls
        and outputs a boolean to decide if we should keep polling or not.
    """
    self.base_filters = filters or []
    self.polling_interval = polling_interval
    # Default is to poll infinitely.
    if continue_func:
      self.should_continue = continue_func
    else:
      self.should_continue = lambda x: True
    self.log_position = LogPosition()

  def GetLogs(self):
    """Retrieves a batch of logs.

    After we fetch the logs, we ensure that none of the logs have been seen
    before.  Along the way, we update the most recent timestamp.

    Returns:
      A list of valid log entries.
    """
    utcnow = datetime.datetime.utcnow()
    lower_filter = self.log_position.GetFilterLowerBound()
    upper_filter = self.log_position.GetFilterUpperBound(utcnow)
    new_filter = self.base_filters + [lower_filter, upper_filter]
    entries = logging_common.FetchLogs(
        log_filter=' AND '.join(new_filter),
        order_by='ASC',
        limit=self.LOG_BATCH_SIZE)
    return [entry for entry in entries if
            self.log_position.Update(entry.timestamp, entry.insertId)]

  def YieldLogs(self):
    """Polls Get API for more logs.

    We poll so long as our continue function, which considers the number of
    periods without new logs, returns True.

    Yields:
        A single log entry.
    """
    empty_polls = 0
    logs = self.GetLogs()
    # If we find new logs, we continue to poll regardless of user-supplied
    # continue function.
    while logs or self.should_continue(empty_polls):
      if logs:
        empty_polls = 0
        for log in logs:
          yield log
      else:
        empty_polls += 1
      time.sleep(self.polling_interval)
      logs = self.GetLogs()
    raise StopIteration

