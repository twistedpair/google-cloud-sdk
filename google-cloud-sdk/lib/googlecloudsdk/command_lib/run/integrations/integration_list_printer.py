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
"""Represents the rows of the the 'gcloud run integrations list' command.

The client.ListIntegrations output is formatted into the Row class listed below,
which allows for formatted output to the console.  The list command registers
a table that references the field names in the Row class.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.command_lib.run.integrations.formatters import base
from googlecloudsdk.generated_clients.apis.runapps.v1alpha1 import runapps_v1alpha1_messages
import six

StateValueValuesEnum = (
    runapps_v1alpha1_messages.ResourceStatus.StateValueValuesEnum
)


class Row(object):
  """Represents the fields that will be used in the output of the table.

  Having a single class that has the expected values here is better than passing
  around a dict as the keys could mispelled or changed in one place.
  """

  def __init__(
      self,
      integration_name,
      integration_type,
      services,
      latest_resource_status,
      region: str,
  ):
    self.integration_name = integration_name
    self.integration_type = integration_type
    self.services = services
    self.latest_resource_status = latest_resource_status
    self.region = region
    self.formatted_latest_resource_status = _GetSymbolFromResourceStatus(
        latest_resource_status
    )

  def __eq__(self, other):
    return (
        self.integration_name == other.integration_name
        and self.integration_type == other.integration_type
        and self.services == other.services
        and self.latest_resource_status == other.latest_resource_status
        and self.region == other.region
    )


def _GetSymbolFromResourceStatus(status):
  """Gets a symbol based on the latest resource status.

  If a resource cannot be found or the deployment is not in a well defined state
  the default status is 'FAILED'.

  This would be true for integrations where the deployment never kicked off
  due to a failure.

  Args:
    status: The latest resource status.

  Returns:
    str, the symbol to be placed in front of the integration name.
  """

  if status == StateValueValuesEnum.ACTIVE:
    symbol = base.GetSymbol(base.SUCCESS)
  elif status == StateValueValuesEnum.FAILED:
    symbol = base.GetSymbol(base.FAILED)
  elif status == StateValueValuesEnum.UPDATING:
    symbol = base.GetSymbol(base.UPDATING)
  elif status == StateValueValuesEnum.NOT_READY:
    symbol = base.GetSymbol(base.DEFAULT)
  elif status == StateValueValuesEnum.NOT_DEPLOYED:
    symbol = base.GetSymbol(base.DEFAULT)
  else:
    symbol = base.GetSymbol(base.FAILED)

  return six.text_type(symbol)
