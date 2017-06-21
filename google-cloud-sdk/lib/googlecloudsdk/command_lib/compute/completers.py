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

"""Compute resource completers shared with command_lib...flags modules.

Surface specific completers may be found in their respective command_lib...flags
modules.
"""

import os

from googlecloudsdk.command_lib.resource_manager import completers as resource_manager_completers
from googlecloudsdk.command_lib.util import completers
from googlecloudsdk.command_lib.util import parameter_info_lib
from googlecloudsdk.core import exceptions


class Error(exceptions.Error):
  """Exceptions for this module."""


class TestParametersRequired(Error):
  """Test parameters must be exported in _ARGCOMPLETE_TEST."""


# resource param project aggregators


class ResourceParamCompleter(completers.ResourceParamCompleter):

  def ParameterInfo(self, parsed_args, argument):
    return parameter_info_lib.ParameterInfoByConvention(
        parsed_args,
        argument,
        self.collection,
        updaters={
            'project': (resource_manager_completers.ProjectCompleter, True),
        },
    )


# common parameter completers


class RegionCompleter(ResourceParamCompleter):
  """The region completer."""

  def __init__(self, **kwargs):
    super(RegionCompleter, self).__init__(
        collection='compute.regions',
        list_command='compute regions list --uri',
        param='region',
        timeout=8*60*60,
        **kwargs)


class ZoneCompleter(ResourceParamCompleter):
  """The zone completer."""

  def __init__(self, **kwargs):
    super(ZoneCompleter, self).__init__(
        collection='compute.zones',
        list_command='compute zones list --uri',
        param='zone',
        timeout=8*60*60,
        **kwargs)


# completers by parameter name convention


COMPLETERS_BY_CONVENTION = {
    'project': (resource_manager_completers.ProjectCompleter, True),
    'region': (RegionCompleter, False),
    'zone': (ZoneCompleter, False),
}


# list command project aggregators


class ListCommandCompleter(completers.ListCommandCompleter):

  def ParameterInfo(self, parsed_args, argument):
    return parameter_info_lib.ParameterInfoByConvention(
        parsed_args,
        argument,
        self.collection,
        updaters=COMPLETERS_BY_CONVENTION,
    )


class GlobalListCommandCompleter(ListCommandCompleter):
  """A global resource list command completer."""

  def ParameterInfo(self, parsed_args, argument):
    return parameter_info_lib.ParameterInfoByConvention(
        parsed_args,
        argument,
        self.collection,
        additional_params=['global'],
        updaters=COMPLETERS_BY_CONVENTION,
    )


# cross-surface resource completers


class InstanceCompleter(completers.ResourceSearchCompleter):

  def __init__(self, **kwargs):
    super(InstanceCompleter, self).__init__(
        collection='compute.instances',
        timeout=1*60*60,
        **kwargs)


# manual test completer


class TestCompleter(ListCommandCompleter):
  """A completer that checks env var _ARGCOMPLETE_TEST for completer info.

  For testing list command completers.

  The env var is a comma separated list of name=value items:
    collection=COLLECTION
      The collection name.
    list_command=COMMAND
      The gcloud list command string with gcloud omitted.
  """

  def __init__(self, **kwargs):
    test_parameters = os.environ.get('_ARGCOMPLETE_TEST', 'parameters=bad')
    kwargs = dict(kwargs)
    for pair in test_parameters.split(','):
      name, value = pair.split('=')
      kwargs[name] = value
    if 'collection' not in kwargs or 'list_command' not in kwargs:
      raise TestParametersRequired(
          'Specify test completer parameters in the _ARGCOMPLETE_TEST '
          'environment variable. It is a comma-separated list of name=value '
          'test parameters and must contain at least '
          '"collection=COLLECTION,list_command=LIST COMMAND" parameters.')
    super(TestCompleter, self).__init__(**kwargs)
