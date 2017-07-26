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

from googlecloudsdk.core.resource import yaml_printer


class SessionCapturer(object):
  """Captures the session to file."""

  def __init__(self, stream, printer_class=yaml_printer.YamlPrinter):
    self._printer = printer_class(stream)

  def capture_http_request(self, uri, method, body, headers):
    self._printer.AddRecord({
        'request': {
            'uri': uri,
            'method': method,
            'headers': headers,
            'body': body
        }})

  def capture_http_response(self, headers, content):
    self._printer.AddRecord({
        'response': {
            'headers': headers,
            'content': content
        }})
