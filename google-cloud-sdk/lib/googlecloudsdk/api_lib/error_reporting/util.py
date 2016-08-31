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

"""Crash Reporting for Cloud SDK."""

from googlecloudsdk.core import apis as core_apis
from googlecloudsdk.core import properties


class ErrorReporting(object):
  """Report errors to errorreporting."""
  _API_VERSION = 'v1beta1'
  _API_NAME = 'clouderrorreporting'

  def __init__(self):
    self.api_client = core_apis.GetClientInstance(
        self._API_NAME, self._API_VERSION)
    self.api_messages = core_apis.GetMessagesModule(
        self._API_NAME, self._API_VERSION)

  def ReportEvent(self, error_message, service, version=None, project=None):
    """Creates a new error event and sends to StackDriver Reporting API.

    Args:
      error_message: str, Crash details including stacktrace
      service: str, Name of service
      version: str, Service version, defaults to None
      project: str, Project to report errors to, defaults to current
    """
    if project is None:
      project = self._GetGcloudProject()

    project_name = self._MakeProjectName(project)

    service_context = self.api_messages.ServiceContext(
        service=service, version=version)
    error_event = self.api_messages.ReportedErrorEvent(
        serviceContext=service_context, message=error_message)

    self.api_client.projects_events.Report(
        self.api_messages.ClouderrorreportingProjectsEventsReportRequest(
            projectName=project_name,
            reportedErrorEvent=error_event))

  def _GetGcloudProject(self):
    """Gets the current project if project is not specified."""
    return properties.VALUES.core.project.Get(required=True)

  def _MakeProjectName(self, project):
    return 'projects/' + project
