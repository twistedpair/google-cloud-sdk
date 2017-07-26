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

"""This module holds exceptions raised by commands."""

from googlecloudsdk.api_lib.app import deploy_command_util
from googlecloudsdk.api_lib.app import yaml_parsing
from googlecloudsdk.core import log


DEPLOY_SERVICE_MESSAGE_TEMPLATE = u"""\
descriptor:      [{descriptor}]
source:          [{source}]
target project:  [{project}]
target service:  [{service}]
target version:  [{version}]
target url:      [{url}]

"""

DEPLOY_CONFIG_MESSAGE_TEMPLATE = u"""\
descriptor:      [{descriptor}]
type:            [{type}]
target project:  [{project}]

"""

CONFIG_TYPES = {
    yaml_parsing.ConfigYamlInfo.INDEX: 'datastore indexes',
    yaml_parsing.ConfigYamlInfo.CRON: 'cron jobs',
    yaml_parsing.ConfigYamlInfo.QUEUE: 'task queues',
    yaml_parsing.ConfigYamlInfo.DISPATCH: 'routing rules',
    yaml_parsing.ConfigYamlInfo.DOS: 'DoS blacklist',
}

PROMOTE_MESSAGE_TEMPLATE = u"""\
     (add --promote if you also want to make this service available from
     [{default_url}])
"""

RUNTIME_MISMATCH_MSG = (u"You've generated a Dockerfile that may be customized "
                        u'for your application.  To use this Dockerfile, '
                        u'the runtime field in [{0}] must be set to custom.')


def DisplayProposedDeployment(app, project, services, configs, version,
                              promote):
  """Prints the details of the proposed deployment.

  Args:
    app: Application resource for the current application (required if any
      services are deployed, otherwise ignored).
    project: The name of the current project.
    services: [deployables.Service], The services being deployed.
    configs: [yaml_parsing.ConfigYamlInfo], The configurations being updated.
    version: The version identifier of the application to be deployed.
    promote: Whether the newly deployed version will receive all traffic
      (this affects deployed URLs).

  Returns:
    dict (str->str), a mapping of service names to deployed service URLs

  This includes information on to-be-deployed services (including service name,
  version number, and deployed URLs) as well as configurations.
  """
  deployed_urls = {}
  if services:
    if app is None:
      raise TypeError('If services are deployed, must provide `app` parameter.')
    log.status.Print('Services to deploy:\n')
    for service in services:
      use_ssl = deploy_command_util.UseSsl(
          service.service_info.parsed.handlers)
      url = deploy_command_util.GetAppHostname(
          app=app, service=service.service_id,
          version=None if promote else version, use_ssl=use_ssl)
      deployed_urls[service.service_id] = url
      log.status.Print(DEPLOY_SERVICE_MESSAGE_TEMPLATE.format(
          project=project, service=service.service_id, version=version,
          descriptor=service.descriptor, source=service.source, url=url))
      if not promote:
        default_url = deploy_command_util.GetAppHostname(
            app=app, service=service.service_id, use_ssl=use_ssl)
        log.status.Print(PROMOTE_MESSAGE_TEMPLATE.format(
            default_url=default_url))

  if configs:
    DisplayProposedConfigDeployments(project, configs)

  return deployed_urls


def DisplayProposedConfigDeployments(project, configs):
  """Prints the details of the proposed config deployments.

  Args:
    project: The name of the current project.
    configs: [yaml_parsing.ConfigYamlInfo], The configurations being
      deployed.
  """
  log.status.Print('Configurations to update:\n')
  for c in configs:
    log.status.Print(DEPLOY_CONFIG_MESSAGE_TEMPLATE.format(
        project=project, type=CONFIG_TYPES[c.config], descriptor=c.file))
