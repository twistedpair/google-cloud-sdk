# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""Contains shared methods for printing k8s object in a human-readable way."""
import textwrap

from googlecloudsdk.command_lib.run import resource_name_conversion
from googlecloudsdk.command_lib.run.v2 import conditions
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.resource import custom_printer_base as cp
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import condition as condition_objects
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import vendor_settings


_CONDITION_SUCCEEDED_VALUE = (
    condition_objects.Condition.State.CONDITION_SUCCEEDED.value
)


def _PickSymbol(best, alt, encoding):
  """Choose the best symbol (if it's in this encoding) or an alternate."""
  try:
    best.encode(encoding)
    return best
  except UnicodeError:
    return alt


def ReadySymbolAndColor(record):
  """Return a tuple of ready_symbol and display color for this object."""
  encoding = console_attr.GetConsoleAttr().GetEncoding()
  terminal_condition = conditions.GetTerminalCondition(record)
  if terminal_condition is None:
    return (
        _PickSymbol('\N{HORIZONTAL ELLIPSIS}', '.', encoding),
        'yellow',
    )
  elif conditions.IsConditionReady(terminal_condition):
    return _PickSymbol('\N{HEAVY CHECK MARK}', '+', encoding), 'green'
  else:
    return 'X', 'red'


def FormatReadyMessage(record):
  """Returns the record's status condition Ready (or equivalent) message."""
  terminal_condition = conditions.GetTerminalCondition(record)
  if terminal_condition and terminal_condition.message:
    symbol, color = ReadySymbolAndColor(record)
    return console_attr.GetConsoleAttr().Colorize(
        textwrap.fill('{} {}'.format(symbol, terminal_condition.message), 100),
        color,
    )
  elif terminal_condition is None:
    return console_attr.GetConsoleAttr().Colorize(
        'Error getting status information', 'red'
    )
  else:
    return ''


def LastUpdatedMessage(record):
  if not record.terminal_condition:
    return 'Unknown update information'
  modifier = record.last_modifier or '?'
  last_transition_time = '?'
  if record.terminal_condition.last_transition_time:
    last_transition_time = record.terminal_condition.last_transition_time
  return 'Last updated on {} by {}'.format(last_transition_time, modifier)


def BuildHeader(record, is_multi_region=False, is_child_resource=False):
  """Returns a display header for a resource."""
  con = console_attr.GetConsoleAttr()
  status = con.Colorize(*ReadySymbolAndColor(record))
  if is_child_resource:
    _, region, _, _, resource_kind, name = (
        resource_name_conversion.GetInfoFromFullChildName(record.name)
    )
  else:
    _, region, resource_kind, name = (
        resource_name_conversion.GetInfoFromFullName(record.name)
    )
  place = ('regions ' if is_multi_region else 'region ') + region
  kind = ('Multi-Region ' if is_multi_region else '') + resource_kind
  return con.Emphasize('{} {} {} in {}'.format(status, kind, name, place))


def GetVpcNetwork(record):
  """Returns the VPC Network setting.

  Either the values of the vpc-access-connector and vpc-access-egress, or the
  values of the network and subnetwork in network-interfaces annotation and
  vpc-access-egress.

  Args:
    record:
      googlecloudsdk.generated_clients.gapic_clients.run_v2.types.vendor_settings.VpcAccess.
  """

  def _GetEgress(egress):
    if egress == vendor_settings.VpcAccess.VpcEgress.ALL_TRAFFIC:
      return 'all-traffic'
    elif egress == vendor_settings.VpcAccess.VpcEgress.PRIVATE_RANGES_ONLY:
      return 'private-ranges-only'
    return ''

  connector = record.connector
  if connector:
    return cp.Labeled([
        ('Connector', connector),
        (
            'Egress',
            _GetEgress(record.egress),
        ),
    ])
  # Direct VPC case if annoation exists.
  if not record.network_interfaces:
    return ''
  try:
    network_interface = record.network_interfaces[0]
    return cp.Labeled([
        (
            'Network',
            network_interface.network if network_interface.network else '',
        ),
        (
            'Subnet',
            network_interface.subnetwork
            if network_interface.subnetwork
            else '',
        ),
        (
            'Egress',
            _GetEgress(record.egress),
        ),
    ])
  except Exception:  # pylint: disable=broad-except
    return ''


def GetNameFromDict(resource):
  """Extracts short name from a resource.

  Args:
    resource: dict representing a Cloud Run v2 resource.

  Returns:
    Short name of the resource.
  """
  _, _, _, name = resource_name_conversion.GetInfoFromFullName(
      resource.get('name')
  )
  return name


def GetChildNameFromDict(resource):
  """Extracts short name from a resource.

  Args:
    resource: dict representing a Cloud Run v2 child resource.

  Returns:
    Short name of the resource.
  """
  _, _, _, _, _, name = resource_name_conversion.GetInfoFromFullChildName(
      resource.get('name')
  )
  return name


def GetRegionFromDict(resource):
  """Extracts region from a resource.

  Args:
    resource: dict representing a Cloud Run v2 resource.

  Returns:
    Region of the resource.
  """
  _, region, _, _ = resource_name_conversion.GetInfoFromFullName(
      resource.get('name')
  )
  return region


def GetParentFromDict(resource):
  """Extracts region from a child resource.

  Args:
    resource: dict representing a Cloud Run v2 child resource.

  Returns:
    Region of the resource.
  """
  _, _, _, parent, _, _ = resource_name_conversion.GetInfoFromFullChildName(
      resource.get('name')
  )
  return parent


def GetLastTransitionTimeFromDict(resource):
  """Extracts last transition time from a resource.

  Args:
    resource: dict representing a Cloud Run v2 resource.

  Returns:
    Last transition time of the resource if it exists, otherwise None.
  """
  if resource.get('terminal_condition'):
    result = resource.get('terminal_condition').get('last_transition_time')
    if result:
      return result
  return None


def _GetConditionFromDict(resource, condition_type):
  """Returns the condition matching the given type from a resource."""
  for condition in resource.get('conditions'):
    if condition.get('type_') == condition_type:
      return condition
  return None


def _GetReadyConditionFromDict(resource):
  """Returns the ready condition of a resource."""
  if resource.get('terminal_condition'):
    return resource.get('terminal_condition')
  return _GetConditionFromDict(resource, 'Ready')


def GetReadySymbolFromDict(resource):
  """Return a ready_symbol for a resource.

  Args:
    resource: dict representing a Cloud Run v2 resource.

  Returns:
    A string representing the symbol for the resource ready state.
  """
  encoding = console_attr.GetConsoleAttr().GetEncoding()
  ready_condition = _GetReadyConditionFromDict(resource)
  if ready_condition is None:
    return _PickSymbol('\N{HORIZONTAL ELLIPSIS}', '.', encoding)
  elif ready_condition.get('state') == _CONDITION_SUCCEEDED_VALUE:
    return _PickSymbol('\N{HEAVY CHECK MARK}', '+', encoding)
  else:
    return 'X'


def GetActiveStateFromDict(resource):
  """Return active state for a resource.

  Args:
    resource: dict representing a Cloud Run v2 resource.

  Returns:
    True if the resource is active, false otherwise.
  """
  active_condition = _GetConditionFromDict(resource, 'Active')
  if active_condition:
    return active_condition.get('state') == _CONDITION_SUCCEEDED_VALUE
  return False


def GetCMEK(cmek_key: str) -> str:
  """Returns the CMEK name from a full CMEK key name.

  Args:
    cmek_key: The full CMEK key name.

  Returns:
    The CMEK name.
  """
  if not cmek_key:
    return ''
  cmek_name = cmek_key.split('/')[-1]
  return cmek_name
