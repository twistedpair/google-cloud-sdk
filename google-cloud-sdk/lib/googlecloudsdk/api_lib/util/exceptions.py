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
import logging
import string
import StringIO

from googlecloudsdk.api_lib.util import resource as resource_util
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.resource import resource_printer


class _JsonSortedDict(dict):
  """A dict with a sorted JSON string representation."""

  def __str__(self):
    return json.dumps(self, sort_keys=True)


class HttpErrorPayload(string.Formatter):
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
    <name>.content: The <name> attribute in the JSON content (synthesized in
      get_field()).

  Examples:
    Example payload.format(...) HttpException.error_format string:

    'Error: [{status_code}] {status_message}{url.line}'
    '{debugInfo.content.line.default}'

      Error: [404] Not found
      https://dotcom/foo/bar

      debugInfo:
      <content.debugInfo in default print format>
  """

  def __init__(self, http_error):
    self.api_name = ''
    self.api_version = ''
    self.content = {}
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

  def get_field(self, field_name, unused_args, unused_kwargs):
    r"""Returns the value of field_name for string.Formatter.format().

    Args:
      field_name: The format string field name to get in the form
        <name>(.<attr>)*. If the value for <name> is empty then the attributes
        are ignored. The attributes are:
          content - get <name> from the JSON payload content
          key - emit <name>=<value>
          value - print value of content.<name> in printer format output,
            by default the object {<name>: value} is printed
          line - emit a newline. There is a subtle difference between this and
            explicit "\n". "\n{name}" always prints the newline, "{name.line}"
            only prints newline if name has a non-null value.
          (default, flattened, json, yaml) - emit a newline and the value in
            this printer format
      unused_args: Ignored.
      unused_kwargs: Ignored.

    Returns:
      The value of field_name for string.Formatter.format().
    """
    attributes = field_name.split('.')
    name = attributes.pop(0)
    if attributes and attributes[0] == 'content':
      value = self.content.get(name)
      attributes.pop(0)
      if not attributes:
        attributes = ['default', 'line']
    else:
      value = self.__dict__.get(name, '')
    if not value:
      return '', name
    label = True
    parts = []
    for attr in attributes:
      if attr == 'line':
        parts.append('\n')
      elif attr == 'key':
        parts.append(name)
        parts.append('=')
        parts.append(unicode(value))
        value = None
      elif attr == 'value':
        label = False
      elif attr in ('default', 'flattened', 'json', 'yaml'):
        buf = StringIO.StringIO()
        buf.write('\n')
        if label:
          value = {name: value}
        resource_printer.Print(value, attr, out=buf, single=True)
        value = buf.getvalue()
        if value.endswith('\n'):
          value = value[:-1]
    if value:
      parts.append(unicode(value))
    return ''.join(parts), name

  def _ExtractResponseAndJsonContent(self, http_error):
    """Extracts the response and JSON content from the HttpError."""
    response = getattr(http_error, 'response', None)
    if response:
      self.status_code = int(response.get('status', 0))
      self.status_description = console_attr.DecodeFromInput(
          response.get('reason', ''))
    content = console_attr.DecodeFromInput(http_error.content)
    try:
      self.content = _JsonSortedDict(json.loads(content))
      self.error_info = _JsonSortedDict(self.content['error'])
      if not self.status_code:  # Could have been set above.
        self.status_code = int(self.error_info.get('code', 0))
      if not self.status_description:  # Could have been set above.
        self.status_description = self.error_info.get('status', '')
      self.status_message = self.error_info.get('message', '')
    except (KeyError, TypeError, ValueError):
      self.status_message = content

    except AttributeError:
      pass

  def _ExtractUrlResourceAndInstanceNames(self, http_error):
    """Extracts the url resource type and instance names from the HttpError."""
    self.url = http_error.url
    if not self.url:
      return

    try:
      name, version, resource_path = resource_util.SplitDefaultEndpointUrl(
          self.url)
    except resource_util.InvalidEndpointException:
      return

    if name:
      self.api_name = name
    if version:
      self.api_version = version

    try:
      ref = resources.REGISTRY.Parse(self.url)
      instance_name = ref.Name()
      # resource_name is the component just before the last occurrence of
      # instance_name in the URL. Using string instead of list ops here because
      # instance_name could contain '/'s.
      resource_name_index = resource_path.rfind('/' + instance_name)
      if resource_name_index < 0:
        return
      self.resource_name = resource_path[:resource_name_index].split('/')[-1]
    except resources.Error:
      # The uri parse failed. Do something sensible.
      resource_parts = resource_path.split('/')
      if not 1 < len(resource_parts) < 4:
        return
      self.resource_name = resource_parts[0]
      instance_name = resource_parts[1]

    self.instance_name = instance_name.split('?')[0]
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
    description = self._MakeDescription()
    if self.status_message:
      return u'{0}: {1}'.format(description, self.status_message)
    return description

  def _MakeDescription(self):
    """Makes description for error by checking which fields are filled in."""
    if self.status_code and self.resource_item and self.instance_name:
      if self.status_code == 403:
        return (u'You do not have permission to access {0} [{1}] (or it may '
                u'not exist)').format(
                    self.resource_item, self.instance_name)
      if self.status_code == 404:
        return u'{0} [{1}] not found'.format(
            self.resource_item.capitalize(), self.instance_name)
      if self.status_code == 409:
        return u'{0} [{1}] already exists'.format(
            self.resource_item.capitalize(), self.instance_name)

    description = self.status_description
    if description:
      if description.endswith('.'):
        description = description[:-1]
      return description
    # Example: 'HTTPError 403'
    return u'HTTPError {0}'.format(self.status_code)


class HttpException(core_exceptions.Error):
  """Transforms apitools HttpError to api_lib HttpException.

  Attributes:
    error: The original HttpError.
    error_format: .format() string on payload Attributes.
    payload: The HttpErrorPayload object.
  """

  def __init__(self, error, error_format=None):
    super(HttpException, self).__init__('')
    self.error = error
    self.error_format = error_format
    self.payload = HttpErrorPayload(error)

  def __str__(self):
    error_format = self.error_format
    if error_format is None:
      error_format = '{message}'
      if log.GetVerbosity() <= logging.DEBUG:
        error_format += '{debugInfo.content.line.default}'
    return self.payload.format(unicode(error_format))

  @property
  def message(self):
    return str(self)
