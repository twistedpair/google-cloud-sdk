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
"""Flags for Eventarc commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

_IAM_API_VERSION = 'v1'


def LocationAttributeConfig():
  """Builds an AttributeConfig for the location resource."""
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      fallthroughs=[
          deps.PropertyFallthrough(properties.FromString('eventarc/location'))
      ],
      help_text='The location for the Eventarc resource. Alternatively, set '
      'the [eventarc/location] property.')


def TriggerAttributeConfig():
  """Builds an AttributeConfig for the trigger resource."""
  return concepts.ResourceParameterAttributeConfig(name='trigger')


def ServiceAccountAttributeConfig():
  """Builds an AttributeConfig for the service account resource."""
  return concepts.ResourceParameterAttributeConfig(name='service-account')


def DestinationRunLocationAttributeConfig():
  """Builds an AttributeConfig for the Cloud Run location resource."""
  return concepts.ResourceParameterAttributeConfig(
      name='destination-run-location',
      fallthroughs=[
          # The first fallthrough gets the location from the trigger argument
          # itself, if it is fully specified by the user.
          deps.FullySpecifiedAnchorFallthrough(
              deps.ArgFallthrough('trigger'),
              resources.REGISTRY.GetCollectionInfo(
                  'eventarc.projects.locations.triggers'), 'locationsId'),
          deps.ArgFallthrough('location'),
          deps.PropertyFallthrough(properties.FromString('eventarc/location'))
      ],
      help_text='The location of the destination Cloud Run service. If not '
      'specified, the trigger\'s location will be used.')


def DestinationRunServiceAttributeConfig():
  """Builds an AttributeConfig for the Cloud Run service resource."""
  return concepts.ResourceParameterAttributeConfig(
      name='destination-run-service')


def AddLocationResourceArg(parser, group_help_text, required=False):
  """Adds a resource argument for an Eventarc location."""
  resource_spec = concepts.ResourceSpec(
      'eventarc.projects.locations',
      resource_name='location',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)
  concept_parser = concept_parsers.ConceptParser.ForResource(
      '--location', resource_spec, group_help_text, required=required)
  concept_parser.AddToParser(parser)


def AddTriggerResourceArg(parser, group_help_text, required=False):
  """Adds a resource argument for an Eventarc trigger."""
  resource_spec = concepts.ResourceSpec(
      'eventarc.projects.locations.triggers',
      resource_name='trigger',
      triggersId=TriggerAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)
  concept_parser = concept_parsers.ConceptParser.ForResource(
      'trigger', resource_spec, group_help_text, required=required)
  concept_parser.AddToParser(parser)


def AddServiceAccountResourceArg(parser, required=False):
  """Adds a resource argument for an IAM service account."""
  resource_spec = concepts.ResourceSpec(
      'iam.projects.serviceAccounts',
      resource_name='service account',
      api_version=_IAM_API_VERSION,
      serviceAccountsId=ServiceAccountAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)
  concept_parser = concept_parsers.ConceptParser.ForResource(
      '--service-account',
      resource_spec,
      'The IAM service account associated with the trigger, specified with an '
      'email address or a uniqueId. If not specified, the default compute '
      'service account will be used. Unless a full resource name is provided, '
      'the service account is assumed to be in the same project as the '
      'trigger.',
      required=required)
  concept_parser.AddToParser(parser)


def AddDestinationRunServiceResourceArg(parser, required=False):
  """Adds a resource argument for a destination Cloud Run service."""
  resource_spec = concepts.ResourceSpec(
      'run.projects.locations.services',
      resource_name='destination Cloud Run service',
      servicesId=DestinationRunServiceAttributeConfig(),
      locationsId=DestinationRunLocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)
  concept_parser = concept_parsers.ConceptParser.ForResource(
      '--destination-run-service',
      resource_spec,
      'The Cloud Run fully-managed service that receives the events for the '
      'trigger. The service must be in the same location as the trigger unless '
      'the trigger\'s location is `global`, in which case the service must be '
      'in a different location.',
      required=required)
  concept_parser.AddToParser(parser)


def AddMatchingCriteriaArg(parser, required=False):
  """Adds an argument for the trigger's matching criteria."""
  parser.add_argument(
      '--matching-criteria',
      action=arg_parsers.UpdateAction,
      type=arg_parsers.ArgDict(),
      required=required,
      help='The criteria by which events are filtered for the trigger, '
      'specified as a comma-separated list of CloudEvents attribute names and '
      'values. This flag can also be repeated to add more criteria to the '
      'list. Only events that match with this criteria will be sent to the '
      'destination. The criteria must include the `type` attribute, as well as '
      'any other attributes that are expected for the chosen type.',
      metavar='ATTRIBUTE=VALUE')


def AddDestinationRunPathArg(parser, required=False):
  """Adds an argument for the trigger's destination path on the service."""
  parser.add_argument(
      '--destination-run-path',
      required=required,
      help='The relative path on the destination Cloud Run service to which '
      'the events for the trigger should be sent. Examples: "/route", "route", '
      '"route/subroute".')
