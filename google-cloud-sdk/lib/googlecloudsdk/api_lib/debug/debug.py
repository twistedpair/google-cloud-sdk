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

"""Debug apis layer."""

from googlecloudsdk.api_lib.debug import errors
from googlecloudsdk.api_lib.projects import util as project_util
from googlecloudsdk.core import apis
from googlecloudsdk.core import log

# Names for default module and version. In App Engine, the default module and
# version don't report explicit names to the debugger, so use these strings
# instead when displaying the target name. Note that this code assumes there
# will not be a non-default version or module explicitly named 'default', since
# that would result in a naming conflict between the actual default and the
# one named 'default'.
DEFAULT_MODULE = 'default'
DEFAULT_VERSION = 'default'


class DebugObject(object):
  """Base class for debug api wrappers."""
  _debug_client = None
  _debug_messages = None
  _resource_client = None
  _resource_messages = None
  _project_number_cache = {}
  _project_id_cache = {}

  def _CheckClient(self):
    if (not self._debug_client or not self._debug_messages or
        not self._resource_client or not self._resource_messages):
      raise errors.NoEndpointError()

  @classmethod
  def InitializeApiClients(cls, http):
    cls._debug_client = apis.GetClientInstance('debug', 'v2', http)
    cls._debug_messages = apis.GetMessagesModule('debug', 'v2')
    cls._resource_client = apis.GetClientInstance('projects', 'v1beta1', http)
    cls._resource_messages = apis.GetMessagesModule('projects', 'v1beta1')

  @classmethod
  def GetProjectNumber(cls, project_id):
    """Retrieves the project number given a project ID.

    Args:
      project_id: The ID of the project.
    Returns:
      Integer project number.
    """
    if project_id in cls._project_number_cache:
      return cls._project_number_cache[project_id]
    # Convert errors in the client API to something meaningful.
    @project_util.HandleHttpError
    def GetProject(message):
      return cls._resource_client.projects.Get(message)
    project = GetProject(
        cls._resource_messages.CloudresourcemanagerProjectsGetRequest(
            projectId=project_id))
    cls._project_number_cache[project.projectId] = project.projectNumber
    cls._project_id_cache[project.projectNumber] = project.projectId
    log.debug('Project {0} has ID {1}'.format(
        project.projectId, project.projectNumber))
    return project.projectNumber

  @classmethod
  def GetProjectId(cls, project_number):
    """Retrieves the project ID given a project number.

    Args:
      project_number: The unique number of the project.
    Returns:
      Project ID string or None if the project ID is not known.
    """
    if project_number in cls._project_id_cache:
      return cls._project_id_cache[project_number]
    # Treat the number as an ID to populate the cache. They're interchangeable
    # in lookup.
    cls.GetProjectNumber(project_number)
    return cls._project_id_cache.get(project_number, None)


class Debugger(DebugObject):
  """Abstracts Cloud Debugger service for a project."""

  def __init__(self, project_id):
    self._CheckClient()
    self._project_id = project_id
    self._project_number = str(self.GetProjectNumber(project_id))

  @errors.HandleHttpError
  def ListDebuggees(self, include_inactive=False):
    """Lists all debug targets registered with the debug service.

    Args:
      include_inactive: If true, also include debuggees that are not currently
        running.
    Returns:
      [Debuggee] A list of debuggees.
    """
    request = self._debug_messages.ClouddebuggerDebuggerDebuggeesListRequest(
        project=self._project_number, includeInactive=include_inactive)
    response = self._debug_client.debugger_debuggees.List(request)
    return [Debuggee(debuggee) for debuggee in response.debuggees]


class Debuggee(DebugObject):
  """Represents a single debuggee."""

  def __init__(self, message):
    self.project_number = message.project
    self.project_id = (self.GetProjectId(message.project) or message.project)
    self.agent_version = message.agentVersion
    self.description = message.description
    self.ext_source_contexts = message.extSourceContexts
    self.debuggee_id = message.id
    self.is_disabled = message.isDisabled
    self.is_inactive = message.isInactive
    self.source_contexts = message.sourceContexts
    self.status = message.status
    self.uniquifier = message.uniquifier
    self.labels = {}
    if message.labels:
      for l in message.labels.additionalProperties:
        self.labels[l.key] = l.value

  def __eq__(self, other):
    return (isinstance(other, self.__class__) and
            self.debuggee_id == other.debuggee_id)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __repr__(self):
    return '<Project {0}, id={1}, labels={2}>'.format(
        self.project_id, self.debuggee_id, self.labels)

  @property
  def name(self):
    module = self.labels.get('module', None)
    version = self.labels.get('version', None)
    if module or version:
      return (module or DEFAULT_MODULE) + '-' + (version or DEFAULT_VERSION)
    return self.debuggee_id
