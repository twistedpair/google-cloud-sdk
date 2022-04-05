# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Code for making shared messages between commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


def GetSuccessMessageForSynchronousDeploy(service):
  """Returns a user message for a successful synchronous deploy.

  Args:
    service: googlecloudsdk.api_lib.run.service.Service, Deployed service for
      which to build a success message.
  """
  latest_ready = service.status.latestReadyRevisionName
  latest_percent_traffic = service.latest_percent_traffic
  msg = ('Service [{{bold}}{serv}{{reset}}] '
         'revision [{{bold}}{rev}{{reset}}] '
         'has been deployed and is serving '
         '{{bold}}{latest_percent_traffic}{{reset}} percent of traffic.')
  if latest_percent_traffic:
    msg += '\nService URL: {{bold}}{url}{{reset}}'
  latest_url = service.latest_url
  tag_url_message = ''
  if latest_url:
    tag_url_message = '\nThe revision can be reached directly at {}'.format(
        latest_url)
  return msg.format(
      serv=service.name,
      rev=latest_ready,
      url=service.domain,
      latest_percent_traffic=latest_percent_traffic) + tag_url_message


def GetStartDeployMessage(conn_context,
                          resource_ref,
                          operation='Deploying container to',
                          resource_kind_lower='service'):
  """Returns a user mesage for starting a deploy.

  Args:
    conn_context: connection_context.ConnectionInfo, Metadata for the run API
      client.
    resource_ref: protorpc.messages.Message, A resource reference object for the
      resource. See googlecloudsdk.core.resources.Registry.ParseResourceId for
      details.
    operation: str, what deploy action is being done.
    resource_kind_lower: str, resource kind being deployed, e.g. "service"
  """
  msg = ('{operation} {operator} {resource_kind} '
         '[{{bold}}{resource}{{reset}}] in {ns_label} [{{bold}}{ns}{{reset}}]')
  msg += conn_context.location_label

  return msg.format(
      operation=operation,
      operator=conn_context.operator,
      resource_kind=resource_kind_lower,
      ns_label=conn_context.ns_label,
      resource=resource_ref.Name(),
      ns=resource_ref.Parent().Name())


def GetRunJobMessage(release_track, job_name, repeat=False):
  """Returns a user message for how to run a job."""
  return ('\nTo execute this job{repeat}, use:\n'
          'gcloud{release_track} run jobs execute {job_name}'.format(
              repeat=' again' if repeat else '',
              release_track=(' {}'.format(release_track.prefix)
                             if release_track.prefix is not None else ''),
              job_name=job_name))


def GetExecutionCreatedMessage(release_track, execution):
  """Returns a user message with execution details when running a job."""
  msg = ('\nView details about this execution by running:\n'
         'gcloud{release_track} run jobs executions describe {execution_name}'
        ).format(
            release_track=(' {}'.format(release_track.prefix)
                           if release_track.prefix is not None else ''),
            execution_name=execution.name)
  if execution.status and execution.status.logUri:
    msg += '\n\nSee logs for this execution at: {}'.format(
        execution.status.logUri)
  return msg


def GetBuildEquivalentForSourceRunMessage(serv, pack, source):
  """Returns a user message for equivalent gcloud commands for source deploy.

  Args:
    serv: name of the service
    pack: the pack arguments used to build the service image
    source: the location of the source
  """
  build_flag = ''
  if pack:
    build_flag = '--pack image=[IMAGE]'
  else:
    build_flag = '--tag [IMAGE]'
  msg = ('This command is equivalent to running '
         '`gcloud builds submit {build_flag} {source}` and '
         '`gcloud run deploy {serv} --image [IMAGE]`\n')
  return msg.format(
      serv=serv,
      build_flag=build_flag,
      source=source)
