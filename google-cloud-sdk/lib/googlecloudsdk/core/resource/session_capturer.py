# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Session Dumper."""

import copy
import io
import json
import StringIO
import sys

from googlecloudsdk.core import log
from googlecloudsdk.core.resource import yaml_printer


class _StreamCapturer(io.IOBase):
  """A file-like object that captures all the information wrote to stream."""

  def __init__(self, real_stream):
    self._real_stream = real_stream
    self._capturing_stream = StringIO.StringIO()

  def write(self, *args, **kwargs):
    self._capturing_stream.write(*args, **kwargs)
    self._real_stream.write(*args, **kwargs)

  def writelines(self, *args, **kwargs):
    self._capturing_stream.writelines(*args, **kwargs)
    self._real_stream.writelines(*args, **kwargs)

  def GetValue(self):
    return self._capturing_stream.getvalue()

  def isatty(self):
    return False

  def flush(self):
    self._capturing_stream.flush()
    self._real_stream.flush()


class SessionCapturer(object):
  """Captures the session to file."""
  capturer = None  # is SessionCapturer if session is being captured

  def __init__(self, capture_streams=True):
    self._records = []
    if capture_streams:
      self._streams = (_StreamCapturer(sys.stdout),
                       _StreamCapturer(sys.stderr),)
      sys.stdout, sys.stderr = self._streams  # pylint: disable=unpacking-non-sequence
      log.Reset(*self._streams)
    else:
      self._streams = None

  def CaptureHttpRequest(self, uri, method, body, headers):
    self._records.append({
        'request': {
            'uri': uri,
            'method': method,
            'body': body,
            'headers': self._FilterHeaders(headers)
        }})

  def CaptureHttpResponse(self, response, content):
    self._records.append({
        'response': {
            'response': self._FilterHeaders(response),
            'content': self._ToList(content)
        }})

  def CaptureProperties(self, all_values):
    values = copy.deepcopy(all_values)
    for k in ('capture_session_file', 'account'):
      if values['core'].has_key(k):
        values['core'].pop(k)
    self._records.append({
        'properties': values
    })

  def Print(self, stream, printer_class=yaml_printer.YamlPrinter):
    self._Finalize()
    printer = printer_class(stream)
    for record in self._records:
      printer.AddRecord(record)

  def _Finalize(self):
    if self._streams is not None:
      for stream in self._streams:
        stream.flush()
      self._records.append({
          'output': {
              'stdout': self._streams[0].GetValue(),
              'stderr': self._streams[1].GetValue()
          }
      })

  def _ToList(self, response):
    """Transforms a response to a batch request into a list.

    The list is more human-readable than plain response as it contains
    recognized json dicts.

    Args:
      response: str, The response to be transformed.

    Returns:
      list, The result of transformation.
    """

    # Check if the whole response is json
    try:
      return [{'json': json.loads(response)}]
    except ValueError:
      pass

    result = []
    while True:
      json_content_idx = response.find('Content-Type: application/json;')
      if json_content_idx == -1:
        result.append(response)
        break
      json_start_idx = response.find(
          '\r\n\r\n{', json_content_idx) + len('\r\n\r\n')
      json_end_idx = response.find('}\n\r\n', json_start_idx) + 1
      if json_end_idx <= json_start_idx:
        result.append(response)
        break
      try:
        parts = [response[:json_start_idx],
                 {'json': json.loads(response[json_start_idx:json_end_idx])}]
      except ValueError:
        parts = [response[:json_end_idx]]
      result += parts
      response = response[json_end_idx:]
    return result

  def _FilterHeaders(self, headers):
    return {
        k: v for k, v in headers.iteritems() if self._KeepHeader(k)
    }

  def _KeepHeader(self, header):
    if header.startswith('x-google'):
      return False
    if header in ['user-agent', 'Authorization']:
      return False
    return True
