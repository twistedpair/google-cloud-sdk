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
"""General formatting utils, App Engine specific formatters."""

import datetime
import re

from googlecloudsdk.api_lib.logging import util
from googlecloudsdk.core import log


def FormatAppEntry(entry):
  """App Engine formatter for `LogPrinter`.

  Args:
    entry: A log entry message emitted from the V2 API client.

  Returns:
    A string representing the entry or None if there was no text payload.
  """
  # TODO(user): Output others than text here too?
  if entry.resource.type != 'gae_app':
    return None
  if entry.protoPayload:
    text = str(entry.protoPayload)
  elif entry.jsonPayload:
    text = str(entry.jsonPayload)
  else:
    text = entry.textPayload
  service, version = _ExtractServiceAndVersion(entry)
  return '{service}[{version}]  {text}'.format(service=service,
                                               version=version,
                                               text=text)


def FormatRequestLogEntry(entry):
  """App Engine request_log formatter for `LogPrinter`.

  Args:
    entry: A log entry message emitted from the V2 API client.

  Returns:
    A string representing the entry if it is a request entry.
  """
  if entry.resource.type != 'gae_app':
    return None
  log_id = util.ExtractLogId(entry.logName)
  if log_id != 'appengine.googleapis.com/request_log':
    return None
  service, version = _ExtractServiceAndVersion(entry)
  def GetStr(key):
    return next((x.value.string_value for x in
                 entry.protoPayload.additionalProperties
                 if x.key == key), '-')
  def GetInt(key):
    return next((x.value.integer_value for x in
                 entry.protoPayload.additionalProperties
                 if x.key == key), '-')
  msg = ('"{method} {resource} {http_version}" {status}'
         .format(
             method=GetStr('method'),
             resource=GetStr('resource'),
             http_version=GetStr('httpVersion'),
             status=GetInt('status')))
  return '{service}[{version}]  {msg}'.format(service=service,
                                              version=version,
                                              msg=msg)


def _ExtractServiceAndVersion(entry):
  """Extract service and version from a App Engine log entry.

  Args:
    entry: An App Engine log entry.

  Returns:
    A 2-tuple of the form (service_id, version_id)
  """
  # TODO(user): If possible, extract instance ID too
  ad_prop = entry.resource.labels.additionalProperties
  service = next(x.value
                 for x in ad_prop
                 if x.key == 'module_id')
  version = next(x.value
                 for x in ad_prop
                 if x.key == 'version_id')
  return (service, version)


class LogPrinter(object):
  """Formats V2 API log entries to human readable text on a best effort basis.

  A LogPrinter consists of a collection of formatter functions which attempts
  to format specific log entries in a human readable form. The `Format` method
  safely returns a human readable string representation of a log entry, even if
  the provided formatters fails.

  The output format is `{timestamp} {log_text}`, where `timestamp` has a
  configurable but consistent format within a LogPrinter whereas `log_text` is
  emitted from one of its formatters (and truncated if necessary).

  See https://cloud.google.com/logging/docs/api/introduction_v2

  Attributes:
    time_format: See datetime.strftime()
    max_length: The maximum length of a formatted log entry after truncation.
  """

  def __init__(self, time_format='%Y-%m-%d %H:%M:%S', max_length=None):
    self.formatters = []
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
    # Regex in order to truncate precision to 6 digits because datetime.strptime
    # only handles microsecond precision
    timestamp = re.sub(r'(?P<micro>\d{6})\d*Z$', r'\g<micro>Z', entry.timestamp)
    time = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')

    out = '{timestamp} {log_text}'.format(
        timestamp=time.strftime(self.time_format),
        log_text=text)
    if self.max_length and len(out) > self.max_length:
      out = out[:self.max_length - 3] + '...'
    return out

  def RegisterFormatter(self, formatter):
    """Attach a log entry formatter function to the printer.

    Note that if multiple formatters are attached to the same printer, the first
    added formatter that successfully formats the entry will be used.

    Args:
      formatter: A formatter function which accepts a single argument, a log
          entry. The formatter must either return the formatted log entry as a
          string, or None if it is unable to format the log entry.
          The formatter is allowed to raise exceptions, which will be caught and
          ignored by the printer.
    """
    self.formatters.append(formatter)

  def _LogEntryToText(self, entry):
    """Use the formatters to convert a log entry to unprocessed text."""
    out = None
    for fn in self.formatters + [self._FallbackFormatter]:
      # pylint:disable=bare-except
      try:
        out = fn(entry)
        if out:
          break
      except KeyboardInterrupt as e:
        raise e
      except:
        pass
    if not out:
      log.debug('Could not format log entry: %s %s %s', entry.timestamp,
                entry.logName, entry.insertId)
      out = ('< UNREADABLE LOG ENTRY {0}. OPEN THE DEVELOPER CONSOLE TO '
             'INSPECT. >'.format(entry.insertId))
    return out

  def _FallbackFormatter(self, entry):
    # TODO(user): Is there better serialization for messages than str()?
    if entry.protoPayload:
      return str(entry.protoPayload)
    elif entry.jsonPayload:
      return str(entry.jsonPayload)
    else:
      return entry.textPayload

