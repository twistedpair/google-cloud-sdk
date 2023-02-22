# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Job-specific printer."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from frozendict import frozendict
from googlecloudsdk.command_lib.run.integrations import deployment_states
from googlecloudsdk.command_lib.run.integrations.formatters import cloudsql_formatter
from googlecloudsdk.command_lib.run.integrations.formatters import domain_routing_formatter
from googlecloudsdk.command_lib.run.integrations.formatters import fallback_formatter
from googlecloudsdk.command_lib.run.integrations.formatters import redis_formatter
from googlecloudsdk.command_lib.run.integrations.formatters import states
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.resource import custom_printer_base as cp

INTEGRATION_PRINTER_FORMAT = 'integration'

_FALLBACK_FORMATTER = fallback_formatter.FallbackFormatter()
_INTEGRATION_FORMATTER_MAPS = frozendict({
    'custom-domains': domain_routing_formatter.DomainRoutingFormatter(),
    'redis': redis_formatter.RedisFormatter(),
    'cloudsql': cloudsql_formatter.CloudSQLFormatter(),
})


class Record(object):
  """Record holds data that is passed around to printers for formatting.

  Attributes:
    name: str, name of the integration
    region: str, GCP region for the integration.
    integration_type: str, type of the integration, for example: redis,
      custom-domains, or cloudsql.
    config: dict, resource config for the given integration.
    status: dict, application status for the given integration.
    latest_deployment:
      str, canonical deployment name for the latest deployment for the given
      integration.
  """

  def __init__(self, name, region, integration_type, config, status,
               latest_deployment):
    self.name = name
    self.region = region
    self.integration_type = integration_type
    self.config = config if config is not None else {}
    self.status = status if status is not None else {}
    self.latest_deployment = latest_deployment


class IntegrationPrinter(cp.CustomPrinterBase):
  """Prints the run Integration in a custom human-readable format."""

  def Transform(self, record):
    """Transform an integration into the output structure of marker classes."""
    formatter = GetFormatter(record.integration_type)
    config_block = formatter.TransformConfig(record)
    component_block = (
        formatter.TransformComponentStatus(record)
        if record.status
        else 'Status not available')

    lines = [
        self.Header(record),
        ' ',
        self._DeploymentProgress(record.latest_deployment,
                                 formatter),
        config_block,
        ' ',
        cp.Labeled([
            cp.Lines([
                'Integration Components',
                component_block
            ])
        ]),
    ]

    call_to_action = formatter.CallToAction(record)
    if call_to_action:
      lines.append(' ')
      lines.append(call_to_action)

    return cp.Lines(lines)

  def Header(self, record):
    """Print the header of the integration.

    Args:
      record: dict, the integration.

    Returns:
      The printed output.
    """
    con = console_attr.GetConsoleAttr()
    formatter = GetFormatter(record.integration_type)
    resource_state = record.status.get('state', states.UNKNOWN)
    symbol = formatter.StatusSymbolAndColor(resource_state)
    return con.Emphasize('{} Integration status: {} in region {}'.format(
        symbol, record.name, record.region))

  def _DeploymentProgress(self, deployment, formatter):
    """Returns a message denoting the deployment progress.

    If there is no ongoing deployment and the deployment was successful, then
    this will be empty.

    Currently this only shows something if the latest deployment was a failure.
    In the future this will be updated to show more granular statuses as the
    deployment is ongoing.

    Args:
      deployment:  The deployment object
      formatter: The specific formatter used for the integration type.

    Returns:
      str, The message denoting the most recent deployment's progress (failure).
    """
    if deployment is None:
      return ''

    state = str(deployment.status.state)

    if state == deployment_states.FAILED:
      reason = deployment.status.errorMessage
      symbol = formatter.StatusSymbolAndColor(states.FAILED)
      return '{} Latest deployment: FAILED - {}\n'.format(symbol, reason)

    return ''


def GetFormatter(integration_type):
  """Returns the formatter for the given integration type.

  Args:
    integration_type: string, the integration type.

  Returns:
    A formatter object.
  """
  return _INTEGRATION_FORMATTER_MAPS.get(integration_type,
                                         _FALLBACK_FORMATTER)
