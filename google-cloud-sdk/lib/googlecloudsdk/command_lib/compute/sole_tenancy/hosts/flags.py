# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Flags and helpers for the compute routes commands."""

from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags

DEFAULT_LIST_FORMAT = """\
    table(
      name,
      zone.basename(),
      instances.len():label=INSTANCES,
      status
    )"""


class HostsCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(HostsCompleter, self).__init__(
        collection='compute.hosts',
        api_version='alpha',
        list_command='alpha compute sole-tenancy hosts list --uri',
        **kwargs)


class HostTypesCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(HostTypesCompleter, self).__init__(
        collection='compute.hostTypes',
        api_version='alpha',
        list_command='alpha compute sole-tenancy host-types list --uri',
        **kwargs)


def MakeHostArg(plural=False):
  return compute_flags.ResourceArgument(
      resource_name='host',
      completer=HostsCompleter,
      plural=plural,
      zonal_collection='compute.hosts',
      zone_explanation=compute_flags.ZONE_PROPERTY_EXPLANATION)
