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
"""App Engine specific formatters and helper methods for LogPrinter.

See: api_lib/logging/log_printer.py
"""


def FormatAppEntry(entry):
  """App Engine formatter for `LogPrinter`.

  Args:
    entry: A log entry message emitted from the V2 API client.

  Returns:
    A string representing the entry or None if there was no text payload.
  """
  # TODO(user): Output others than text here too?
  if not entry.textPayload:
    return None
  service, version = _ExtractServiceAndVersion(entry)
  return '{service}[{version}]  {msg}'.format(service=service,
                                              version=version,
                                              msg=entry.textPayload)


def _ExtractServiceAndVersion(entry):
  """Extract service and version from a App Engine log entry.

  Args:
    entry: An App Engine log entry.

  Returns:
    A 2-tuple of the form (service_id, version_id)

  Raises:
    AttributeError: If at least one of the keys do not exist.
  """
  # TODO(user): If possible, extract instance ID too
  ad_prop = entry.labels.additionalProperties
  service = next(x.value
                 for x in ad_prop
                 if x.key == 'appengine.googleapis.com/module_id')
  version = next(x.value
                 for x in ad_prop
                 if x.key == 'appengine.googleapis.com/version_id')
  return (service, version)
