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
"""Utilities for cloud resources."""

from googlecloudsdk.core import exceptions


class CollectionInfo(object):
  """Holds information about a resource collection.

  Attributes:
      api_name: str, name of the api of resources parsed by this parser.
      api_version: str, version id for this api.
      path: str, Atomic URI template for this resource.
      flat_paths: {name->path}, Named detailed URI templates for this resource.
      params: list(str), description of parameters in the path.
      request_type: str, name of apitools generated type for Get request.
      name: str, collection name for this resource without leading api_name.
      base_url: str, URL for service providing these resources.
  """

  def __init__(self, api_name, api_version, base_url, name,
               request_type, path, flat_paths, params):
    self.api_name = api_name
    self.api_version = api_version
    self.base_url = base_url
    self.name = name
    self.request_type = request_type
    self.path = path
    self.flat_paths = flat_paths
    self.params = params

  @property
  def full_name(self):
    return self.api_name + '.'  + self.name

  def __cmp__(self, other):
    return cmp((self.api_name, self.api_version, self.name),
               (other.api_name, other.api_version, other.name))

  def __str__(self):
    return self.full_name


class InvalidEndpointException(exceptions.Error):
  """Exception for when an API endpoint is malformed."""

  def __init__(self, url):
    super(InvalidEndpointException, self).__init__(
        "URL does not start with 'http://' or 'https://' [{0}]".format(url))


def SplitDefaultEndpointUrl(url):
  """Returns api_name, api_version, resource_path tuple for a default api url.

  Supports four formats:
  http(s)://www.googleapis.com/api/version/resource-path,
  http(s)://www-googleapis-staging.sandbox.google.com/api/version/resource-path,
  http(s)://api.googleapis.com/version/resource-path, and
  http(s)://someotherdoman/api/version/resource-path.

  If there is an api endpoint override defined that maches the url,
  that api name will be returned.

  Args:
    url: str, The resource url.

  Returns:
    (str, str, str): The API name, version, resource_path
  """
  tokens = _StripUrl(url).split('/')
  domain = tokens[0]
  resource_path = ''
  if ('googleapis' not in domain
      or domain.startswith('www.') or domain.startswith('www-')):
    if len(tokens) > 1:
      api_name = tokens[1]
    else:
      api_name = None
    if len(tokens) > 2:
      version = tokens[2]
    else:
      version = None
    resource_path = '/'.join(tokens[3:])
  else:
    api_name = tokens[0].split('.')[0]
    if len(tokens) > 1:
      version = tokens[1]
      resource_path = '/'.join(tokens[2:])
    else:
      version = None
  return api_name, version, resource_path


def _StripUrl(url):
  """Strip a http: or https: prefix, then strip leading and trailing slashes."""
  if url.startswith('https://') or url.startswith('http://'):
    return url[url.index(':') + 1:].strip('/')
  raise InvalidEndpointException(url)
