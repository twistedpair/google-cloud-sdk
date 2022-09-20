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
"""Printer for formatting the 'gcloud run intergrations list' command.

The integrations list command returns a dict with a single key.
The value is a list of dicts where each entry will be formatted as a row in the
resulting table that will be displayed to the user.

input:
  record: {
    'output': [
        {'name': 'integration1', 'type': 'redis', '
        services': 'svc1,svc2', 'latestDeployment': FAILED},
        {'name': 'integration2', 'type': 'redis', '
        services': 'svc3,svc4', 'latestDeployment': SUCCESS},
    ]
  }

output:
    INTEGRATION     TYPE       SERVICE
  X integration1    redis      svc1,svc2
  ✔ integration2    redis      svc3,svc4
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.command_lib.run.integrations import deployment_states
from googlecloudsdk.command_lib.run.integrations.formatters import base_formatter
from googlecloudsdk.core.resource import custom_printer_base as cp

PRINTER_FORMAT = 'IntegrationsList'
RECORD_KEY = 'OUTPUT'


class Row(object):
  """Represents the fields that will be used in the output of the table.

  Having a single class that has the expected values here is better than passing
  around a dict as the keys could mispelled or changed in one place.
  """

  def __init__(self, integration_name, integration_type,
               services, latest_deployment_status):
    self.integration_name = integration_name
    self.integration_type = integration_type
    self.services = services
    self.latest_deployment_status = latest_deployment_status

  def __eq__(self, other):
    return (self.integration_name == other.integration_name and
            self.integration_type == other.integration_type and
            self.services == other.services and
            self.latest_deployment_status == other.latest_deployment_status
           )


# TODO(b/217741829): Limit outputted services to 3.
class IntegrationListPrinter(cp.CustomPrinterBase):
  """Prints the integrations list output in a custom human readable format."""

  def Transform(self, record):
    """Transforms the given record into a structured table.

    Args:
      record: dict, has a single key. Values are list[dict] where each record
        in the list will be a separate row in the output.

    Returns:
      Formatted table that is displayed on output to the console.
    """
    rows = record[RECORD_KEY]
    rows = [(_GetSymbolFromDeploymentStatus(row.latest_deployment_status),
             row.integration_name, row.integration_type, row.services)
            for row in rows
           ]

    # the empty column is for the latest deployment status.
    cols = [('', 'INTEGRATION', 'TYPE', 'SERVICE')]
    return cp.Table(cols + rows)


def _GetSymbolFromDeploymentStatus(status):
  """Gets a symbol based on the latest deployment status.

  If a deployment cannot be found or the deployment is not in a 'SUCCEEDED',
  'FAILED', or 'IN_PROGRESS' state, then it should be reported as 'FAILED'.

  This would be true for integrations where the deployment never kicked off
  due to a failure.

  Args:
    status: The latest deployment status.

  Returns:
    str, the symbol to be placed in front of the integration name.
  """
  status_to_symbol = {
      deployment_states.SUCCEEDED:
          base_formatter.GetSymbol(base_formatter.SUCCESS),
      deployment_states.FAILED:
          base_formatter.GetSymbol(base_formatter.FAILED),
      deployment_states.IN_PROGRESS:
          base_formatter.GetSymbol(base_formatter.UPDATING),
  }

  return status_to_symbol.get(status,
                              base_formatter.GetSymbol(
                                  base_formatter.FAILED
                                  )
                              )
