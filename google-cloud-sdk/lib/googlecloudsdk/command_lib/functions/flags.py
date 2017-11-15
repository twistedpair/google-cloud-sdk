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

"""Helpers for flags in commands working with Google Cloud Functions."""

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.util import completers
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


API = 'cloudfunctions'
API_VERSION = 'v1'
LOCATIONS_COLLECTION = API + '.projects.locations'

SEVERITIES = ['DEBUG', 'INFO', 'ERROR']


def AddMinLogLevelFlag(parser):
  min_log_arg = base.ChoiceArgument(
      '--min-log-level',
      choices=[x.lower() for x in SEVERITIES],
      help_str='Minimum level of logs to be fetched.'
  )
  min_log_arg.AddToParser(parser)


def GetLocationsUri(resource):
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName(API, API_VERSION)
  ref = registry.Parse(
      resource.name,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection=LOCATIONS_COLLECTION)
  return ref.SelfLink()


class LocationsCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(LocationsCompleter, self).__init__(
        collection=LOCATIONS_COLLECTION,
        list_command='alpha functions regions list --uri',
        **kwargs)


def AddRegionFlag(parser):
  parser.add_argument(
      '--region',
      help='The region in which the function will run.',
      completer=LocationsCompleter,
      action=actions.StoreProperty(properties.VALUES.functions.region))


def AddDeprecatedRegionFlag(parser):
  parser.add_argument(
      '--region',
      help='The region from which functions will be listed.',
      completer=LocationsCompleter,
      action=actions.DeprecationAction(
          '--region',
          warn='The {flag_name} option is deprecated; use --regions instead.',
          removed=False,
          action=actions.StoreProperty(properties.VALUES.functions.region)),
  )
