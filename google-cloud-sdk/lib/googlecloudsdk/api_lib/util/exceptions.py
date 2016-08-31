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

"""A module that converts API exceptions to core exceptions."""

import json

from googlecloudsdk.core import apis
from googlecloudsdk.core import exceptions as core_exceptions


class _JsonSortedDict(dict):
  """A dict with a sorted JSON string representation."""

  def __str__(self):
    return json.dumps(self, sort_keys=True)


class HttpErrorPayload(object):
  """Converts apitools HttpError payload to an object.

  Attributes:
    api_name: The url api name.
    api_version: The url version.
    content: The dumped JSON content.
    error_info: content['error'].
    instance_name: The url instance name.
    message: The human readable error message.
    resource_name: The url resource name.
    status_code: The HTTP status code number.
    status_description: The status_code description.
    status_message: Context specific status message.
    url: The HTTP url.
  """

  def __init__(self, http_error):
    self.api_name = ''
    self.api_version = ''
    self.error_info = None
    self.instance_name = ''
    self.resource_item = ''
    self.resource_name = ''
    self.resource_version = ''
    self.status_code = 0
    self.status_description = ''
    self.status_message = ''
    self.url = ''
    if isinstance(http_error, basestring):
      self.message = http_error
    else:
      self._ExtractResponseAndJsonContent(http_error)
      self._ExtractUrlResourceAndInstanceNames(http_error)
      self.message = self._MakeGenericMessage()

  def _ExtractResponseAndJsonContent(self, http_error):
    """Extracts the response and JSON content from the HttpError."""
    response = getattr(http_error, 'response', None)
    if response:
      self.status_code = int(response.get('status', 0))
      self.status_description = response.get('reason', '')
    try:
      self.content = _JsonSortedDict(json.loads(http_error.content))
      self.error_info = _JsonSortedDict(self.content['error'])
      if not self.status_code:  # Could have been set above.
        self.status_code = int(self.error_info.get('code', 0))
      if not self.status_description:  # Could have been set above.
        self.status_description = self.error_info.get('status', '')
      self.status_message = self.error_info.get('message', '')
    except (KeyError, TypeError, ValueError):
      self.status_message = http_error.content

    except AttributeError:
      pass

  def _ExtractUrlResourceAndInstanceNames(self, http_error):
    """Extracts the url resource type and instance names from the HttpError."""
    self.url = http_error.url
    if not self.url:
      return

    try:
      (name, version, resource_path) = apis.SplitDefaultEndpointUrl(self.url)
    except apis.InvalidEndpointException:
      return
    if name:
      self.api_name = name
    if version:
      self.api_version = version
    if not resource_path:
      return

    resource_parts = resource_path.split('/', 2)
    self.resource_name = resource_parts[0]
    if len(resource_parts) > 1:
      self.instance_name = resource_parts[1]
    if self.resource_name.endswith('s'):
      # Singular form for formatting message text. This will result in:
      #   Project [foo] already exists.
      # instead of
      #   Projects [foo] already exists.
      self.resource_item = self.resource_name[:-1]
    else:
      self.resource_item = self.resource_name

  def _MakeGenericMessage(self):
    """Makes a generic human readable message from the HttpError."""
    if self.status_code and self.resource_item and self.instance_name:
      if self.status_code == 403:
        return 'You do not have permission to access {0} [{1}].'.format(
            self.resource_item, self.instance_name)
      if self.status_code == 404:
        return '{0} [{1}] not found.'.format(
            self.resource_item.capitalize(), self.instance_name)
      if self.status_code == 409:
        return '{0} [{1}] already exists.'.format(
            self.resource_item.capitalize(), self.instance_name)

    description = self.status_description
    if description.endswith('.'):
      description = description[:-1]
    if not description and not self.status_message:
      # Example: 'HTTPError 403'
      return 'HTTPError {0}'.format(self.status_code)
    if not description or not self.status_message:
      # Example: 'PERMISSION_DENIED' or 'You do not have permission to access X'
      return '{0}'.format(self.status_message or self.status_description)
    # Example: 'PERMISSION_DENIED: You do not have permission to access X'
    return '{0}: {1}'.format(description, self.status_message)


class HttpException(core_exceptions.Error):
  """Transforms apitools HttpError to api_lib HttpException.

  Attributes:
    error: The original HttpError.
    error_format: .format() string on payload Attributes.
    payload: The HttpErrorPayload object.
  """

  def __init__(self, error, error_format='{message}'):
    super(HttpException, self).__init__('')
    self.error = error
    self.error_format = error_format
    self.payload = HttpErrorPayload(error)

  def __str__(self):
    return self.error_format.format(**self.payload.__dict__)

  @property
  def message(self):
    return str(self)
