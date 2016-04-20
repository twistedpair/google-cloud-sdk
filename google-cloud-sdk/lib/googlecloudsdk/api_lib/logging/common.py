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

"""A library that contains common logging commands and formatting utils."""

from collections import defaultdict
import datetime

from googlecloudsdk.api_lib.logging import util
from googlecloudsdk.core import apis
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base.py import list_pager


def FetchLogs(log_filter=None, log_ids=None, order_by='DESC', limit=None):
  """Fetches log entries.

  This method uses Cloud Logging V2 api.
  https://cloud.google.com/logging/docs/api/introduction_v2

  Entries are sorted on the timestamp field, and afterwards filter is applied.
  If limit is passed, returns only up to that many matching entries.

  It is recommended to provide a filter with resource.type, and log_ids.

  Args:
    log_filter: filter expression used in the request.
    log_ids: if present, contructs full log names and passes it in filter.
    order_by: the sort order, either DESC or ASC.
    limit: how many entries to return.

  Returns:
    A generator that returns matching log entries.
    Callers are responsible for handling any http exceptions.
  """
  client = apis.GetClientInstance('logging', 'v2beta1')
  messages = apis.GetMessagesModule('logging', 'v2beta1')
  project = properties.VALUES.core.project.Get(required=True)

  if order_by.upper() == 'DESC':
    order_by = 'timestamp desc'
  else:
    order_by = 'timestamp asc'

  if log_ids is not None:
    log_names = ['"%s"' %  util.CreateLogResourceName(project, log_id)
                 for log_id in log_ids]
    log_names = ' OR '.join(log_names)
    if log_filter:
      log_filter = 'logName=(%s) AND (%s)' % (log_names, log_filter)
    else:
      log_filter = 'logName=(%s)' % log_names

  request = messages.ListLogEntriesRequest(
      projectIds=[project], filter=log_filter, orderBy=order_by)

  # The backend has an upper limit of 1000 for page_size.
  # However, there is no need to retrieve more entries if limit is specified.
  page_size = min(limit, 1000) or 1000

  return list_pager.YieldFromList(
      client.entries, request, field='entries', limit=limit,
      batch_size=page_size, batch_size_attribute='pageSize')


class LogPrinter(object):
  """Formats V2 API log entries to human readable text on a best effort basis.

  A LogPrinter consists of a collection of formatter functions which attempts
  to format specific log entries in a human readable form. Each formatter is
  registered to a specific log ID, and multiple formatters per log
  ID are allowed. The `Format` method safely returns a human readable string
  representation of a log entry, even if the provided formatters fails or does
  not exist.

  The output format is `{timestamp} {log_text}`, where `timestamp` has a
  configurable but consistent format within a LogPrinter whereas `log_text` is
  emitted from one of its formatters (and truncated if necessary).

  See https://cloud.google.com/logging/docs/api/introduction_v2

  Attributes:
    project: The project ID.
    time_format: See datetime.strftime()
    max_length: The maximum length of a formatted log entry after truncation.
  """

  def __init__(self, project, time_format='%Y-%m-%d %H:%M:%S', max_length=None):
    self.project = project
    self.formatters = defaultdict(list)
    self.time_format = time_format
    self.max_length = max_length

  def Format(self, entry):
    """Safely formats a log entry into human readable text.

    Args:
      entry: A log entry message emitted from the V2 API client.

    Returns:
      A string without line breaks respecting the `max_length` property.
    """
    text = self._LogEntryToText(entry)
    text = text.strip().replace('\n', '  ')

    # Timestamp format from the Logging API (RFC 3339)
    time = datetime.datetime.strptime(entry.timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')

    out = '{timestamp} {log_text}'.format(
        timestamp=time.strftime(self.time_format),
        log_text=text)
    if self.max_length and len(out) > self.max_length:
      out = out[:self.max_length - 3] + '...'
    return out

  def RegisterFormatter(self, log_id, formatter):
    """Associate a log entry formatter function with a log ID.

    Note that if multiple formatters are attached to the same log ID, any of
    them may be used provided that it successfully formats the entry.

    Args:
      log_id: The log ID that the formatter will be invoked on.
      formatter: A dict mapping logName (see V2 API) to a formatter function,
          Fn, which accepts a single argument, a log entry. Fn must either
          return the formatted log entry as a string, or None if it is unable
          to format the log entry. Fn is furthermore permitted to fail with an
          AttributeError, but all other exceptions will not be caught and
          should hence be avoided.
    """
    self.formatters[
        util.CreateLogResourceName(self.project, log_id)].append(formatter)

  def _LogEntryToText(self, entry):
    """Use the formatters to convert a log entry to unprocessed text."""
    out = None
    for fn in self.formatters[entry.logName]:
      try:
        out = fn(entry)
        break
      # pylint:disable=bare-except
      except:
        pass
    if not out:
      out = self._FallbackFormatter(entry)
    return out

  def _FallbackFormatter(self, entry):
    # TODO(user): Is there better serialization for messages than str()?
    if entry.protoPayload:
      return str(entry.protoPayload)
    elif entry.jsonPayload:
      return str(entry.jsonPayload)
    elif entry.textPayload:
      return entry.textPayload
    else:
      return '< UNREADABLE LOG ENTRY. OPEN THE DEVELOPER CONSOLE TO INSPECT. >'
