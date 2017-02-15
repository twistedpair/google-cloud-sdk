# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Source apis layer."""
import json
import os

from apitools.base.py import exceptions

from googlecloudsdk.core import apis
from googlecloudsdk.core import resources


class RepoCreationError(exceptions.Error):
  """Unable to create repo."""

  def __init__(self, message):
    super(RepoCreationError, self).__init__(message)


class RepoDeletionError(exceptions.Error):
  """Unable to delete repo."""

  def __init__(self, message):
    super(RepoDeletionError, self).__init__(message)


class RepoNoExistError(exceptions.Error):
  """Repo does not exist."""

  def __init__(self, message):
    super(RepoNoExistError, self).__init__(message)


# TODO(user): Avoid initializing this at import time.
messages = apis.GetMessagesModule('sourcerepo', 'v1')


def _NormalizeToSourceAPIPath(path):
  """Fix an OS-native path to conform to the Unix/Source API style.

  Args:
    path: (string) An OS-native path (e.g. "/foo/bar" on Unix or "foo\bar" on
      Windows.
  Returns:
    (string) The path converted to Unix/Source API style. '\' characters will
    be converted to '/' on Windows.
    TODO(user) Consider whether it makes sense to strip drive letters.
  """

  return path.replace(os.sep, '/')


class NoEndpointException(Exception):

  def __str__(self):
    return (
        'Source endpoint not initialized. Source.SetApiEndpoint must be '
        'called before using this module.')


class FileTooBigException(Exception):

  def __init__(self, name, size, max_size):
    super(FileTooBigException, self).__init__()
    self.name = name
    self.size = size
    self.max_size = max_size

  def __str__(self):
    return (
        'Could not write file "{0}" because it was too large '
        '({1} bytes). Max size is {2} bytes').format(
            self.name, self.size, self.max_size)


def _GetViolationsFromError(error_info):
  """Looks for violations descriptions in error message.

  Args:
    error_info: json containing error information.
  Returns:
    List of violations descriptions.
  """
  result = ''
  details = None
  try:
    if 'details' in error_info:
      details = error_info['details']
    for field in details:
      if 'fieldViolations' in field:
        violations = field['fieldViolations']
        for violation in violations:
          if 'description' in violation:
            result += violation['description'] + '\n'
  except (ValueError, TypeError):
    pass
  return result


# TODO(b/26202997): make this more general to be used by other library code.
def GetHttpErrorMessage(error):
  """Returns a human readable string representation from the http response.

  Args:
    error: HttpException representing the error response.

  Returns:
    A human readable string representation of the error.
  """
  status = error.response.status
  code = error.response.reason
  message = ''
  try:
    data = json.loads(error.content)
  except ValueError:
    data = error.content

  if 'error' in data:
    try:
      error_info = data['error']
      if 'message' in error_info:
        message = error_info['message']
      # If there is public message we use it instead; billing uses this.
      if 'details' in error_info:
        for d in error_info['details']:
          if d['@type'] == 'type.googleapis.com/google.rpc.LocalizedMessage':
            message = d['message']
      violations = _GetViolationsFromError(error_info)
      if violations:
        message += '\nProblems:\n' + violations
    except (ValueError, TypeError):
      message = data
  else:
    message = data
  return 'ResponseError: status=[{0}], code=[{1}], message=[{2}]'.format(
      status, code, message)


class Source(object):
  """Base class for sourcerepo api wrappers."""
  _client = None
  _resource_parser = None

  def _CheckClient(self):
    if not self._client:
      raise NoEndpointException()

  @classmethod
  def SetApiEndpoint(cls):
    cls._client = apis.GetClientInstance('sourcerepo', 'v1')

  @classmethod
  def SetResourceParser(cls, parser):
    cls._resource_parser = parser

  def GetIamPolicy(self, repo_resource):
    """Gets IAM policy for a repo.

    Args:
      repo_resource:  The repo resource with collection type
        sourcerepo.projects.repos
    Returns:
      (messages.Policy) The IAM policy.
    """
    request = messages.SourcerepoProjectsReposGetIamPolicyRequest(
        resource=repo_resource.RelativeName())
    return self._client.projects_repos.GetIamPolicy(request)

  def SetIamPolicy(self, repo_resource, policy):
    """Sets the IAM policy from a policy string.

    Args:
      repo_resource: The repo as a resource with colleciton type
        sourcerepo.projects.repos
      policy: (string) The file containing the new IAM policy.
    Returns:
      (messages.Policy) The IAM policy.
    """
    req = messages.SetIamPolicyRequest(policy=policy)
    request = messages.SourcerepoProjectsReposSetIamPolicyRequest(
        resource=repo_resource.RelativeName(), setIamPolicyRequest=req)
    return self._client.projects_repos.SetIamPolicy(request)

  def ListRepos(self, project_resource):
    """Returns list of repos."""
    request = messages.SourcerepoProjectsReposListRequest(
        name=project_resource.RelativeName())
    return self._client.projects_repos.List(request).repos

  def GetRepo(self, repo_resource):
    """Finds details on the named repo, if it exists.

    Args:
      repo_resource: (Resource) A resource representing the repo to create.
    Returns:
      (messages.Repo) The full definition of the new repo, as reported by
        the server.
      Returns None if the repo does not exist.
    """
    request = messages.SourcerepoProjectsReposGetRequest(
        name=repo_resource.RelativeName())
    try:
      return self._client.projects_repos.Get(request)
    except exceptions.HttpError as e:
      # If the repo does not exist, we get an HTTP 404
      if e.status_code != 404:
        raise e
      return None

  def CreateRepo(self, repo_resource):
    """Creates a repo.

    Args:
      repo_resource: (Resource) A resource representing the repo to create.
    Returns:
      (messages.Repo) The full definition of the new repo, as reported by
        the server.
    """
    parent = resources.REGISTRY.Create('sourcerepo.projects',
                                       projectsId=repo_resource.projectsId)
    request = messages.SourcerepoProjectsReposCreateRequest(
        parent=parent.RelativeName(),
        repo=messages.Repo(name=repo_resource.RelativeName()))
    return self._client.projects_repos.Create(request)

  def DeleteRepo(self, repo_resource):
    """Deletes a repo.

    Args:
      repo_resource: (Resource) A resource representing the repo to create.
    """
    request = messages.SourcerepoProjectsReposDeleteRequest(
        name=repo_resource.RelativeName())
    self._client.projects_repos.Delete(request)
