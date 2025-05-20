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

import googlecloudsdk
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core import properties

_IAM_API_VERSION = 'v1'


def LocationAttributeConfig(allow_aggregation=False, allow_global=True):
  """Builds an AttributeConfig for the location resource."""
  fallthroughs_list = [
      deps.PropertyFallthrough(properties.FromString('eventarc/location'))
  ]

  help_text = 'The location for the Eventarc {resource}, which should be '
  if allow_global:
    help_text += "either ``global'' or "
  help_text += (
      'one of the supported regions. Alternatively, set the [eventarc/location]'
      ' property.'
  )

  if allow_aggregation:
    fallthroughs_list.append(
        deps.Fallthrough(
            googlecloudsdk.command_lib.eventarc.flags.SetLocation,
            "use '-' location to aggregate results for all Eventarc locations",
        )
    )
  return concepts.ResourceParameterAttributeConfig(
      name='location', fallthroughs=fallthroughs_list, help_text=help_text
  )


def SetLocation():
  return '-'


def TriggerAttributeConfig():
  """Builds an AttributeConfig for the trigger resource."""
  return concepts.ResourceParameterAttributeConfig(name='trigger')


def ChannelAttributeConfig():
  """Builds an AttributeConfig for the channel resource."""
  return concepts.ResourceParameterAttributeConfig(name='channel')


def ChannelConnectionAttributeConfig():
  """Builds an AttributeConfig for the channel connection resource."""
  return concepts.ResourceParameterAttributeConfig(name='channel-connection')


def ProviderAttributeConfig():
  """Builds an AttributeConfig for the provider resource."""
  return concepts.ResourceParameterAttributeConfig(name='provider')


def TransportTopicAttributeConfig():
  """Builds an AttributeConfig for the transport topic resource."""
  return concepts.ResourceParameterAttributeConfig(name='transport-topic')


def MessageBusAttributeConfig():
  """Builds an AttributeConfig for the message bus resource."""
  return concepts.ResourceParameterAttributeConfig(name='message-bus')


def GoogleApiSourceAttributeConfig():
  """Builds an AttributeConfig for the Google API source resource."""
  return concepts.ResourceParameterAttributeConfig(name='google-api-source')


def EnrollmentAttributeConfig():
  """Builds an AttributeConfig for the enrollment resource."""
  return concepts.ResourceParameterAttributeConfig(name='enrollment')


def PipelineAttributeConfig():
  """Builds an AttributeConfig for the pipeline resource."""
  return concepts.ResourceParameterAttributeConfig(name='pipeline')


def KafkaSourceAttributeConfig():
  """Builds an AttributeConfig for the Kafka source resource."""
  return concepts.ResourceParameterAttributeConfig(name='kafka-source')


def TriggerResourceSpec():
  """Builds a ResourceSpec for trigger resource."""
  return concepts.ResourceSpec(
      'eventarc.projects.locations.triggers',
      resource_name='trigger',
      triggersId=TriggerAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def ChannelResourceSpec():
  """Builds a ResourceSpec for channel resource."""
  return concepts.ResourceSpec(
      'eventarc.projects.locations.channels',
      resource_name='channel',
      channelsId=ChannelAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def ChannelConnectionResourceSpec():
  """Builds a ResourceSpec for channel connection resource."""
  return concepts.ResourceSpec(
      'eventarc.projects.locations.channelConnections',
      resource_name='channel connection',
      channelConnectionsId=ChannelConnectionAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def ProviderResourceSpec():
  """Builds a ResourceSpec for event provider."""
  return concepts.ResourceSpec(
      'eventarc.projects.locations.providers',
      resource_name='provider',
      providersId=ProviderAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def MessageBusResourceSpec():
  """Builds a ResourceSpec for message bus."""
  return concepts.ResourceSpec(
      'eventarc.projects.locations.messageBuses',
      resource_name='message bus',
      messageBusesId=MessageBusAttributeConfig(),
      locationsId=LocationAttributeConfig(allow_global=False),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def GoogleApiSourceResourceSpec():
  """Builds a ResourceSpec for Google API source."""
  return concepts.ResourceSpec(
      'eventarc.projects.locations.googleApiSources',
      resource_name='Google API source',
      googleApiSourcesId=GoogleApiSourceAttributeConfig(),
      locationsId=LocationAttributeConfig(allow_global=False),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def EnrollmentResourceSpec():
  """Builds a ResourceSpec for enrollment."""
  return concepts.ResourceSpec(
      'eventarc.projects.locations.enrollments',
      resource_name='enrollment',
      enrollmentsId=EnrollmentAttributeConfig(),
      locationsId=LocationAttributeConfig(allow_global=False),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def PipelineResourceSpec(resource_name='pipeline'):
  """Builds a ResourceSpec for destination."""
  return concepts.ResourceSpec(
      'eventarc.projects.locations.pipelines',
      resource_name=resource_name,
      pipelinesId=PipelineAttributeConfig(),
      locationsId=LocationAttributeConfig(allow_global=False),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def KafkaSourceResourceSpec():
  """Builds a ResourceSpec for destination."""
  return concepts.ResourceSpec(
      'eventarc.projects.locations.kafkaSources',
      resource_name='kafka source',
      kafkaSourcesId=KafkaSourceAttributeConfig(),
      locationsId=LocationAttributeConfig(allow_global=False),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def AddTransportTopicResourceArg(parser, required=False):
  """Adds a resource argument for a customer-provided transport topic."""
  resource_spec = concepts.ResourceSpec(
      'pubsub.projects.topics',
      resource_name='Pub/Sub topic',
      topicsId=TransportTopicAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )
  concept_parser = concept_parsers.ConceptParser.ForResource(
      '--transport-topic',
      resource_spec,
      "The Cloud Pub/Sub topic to use for the trigger's transport "
      'intermediary. This feature is currently only available for triggers '
      "of event type ``google.cloud.pubsub.topic.v1.messagePublished''. "
      'The topic must be in the same project as the trigger. '
      'If not specified, a transport topic will be created.',
      required=required,
  )
  concept_parser.AddToParser(parser)


def AddLocationResourceArg(
    parser, group_help_text, required=False, allow_aggregation=False
):
  """Adds a resource argument for an Eventarc location."""
  resource_spec = concepts.ResourceSpec(
      'eventarc.projects.locations',
      resource_name='location',
      locationsId=LocationAttributeConfig(allow_aggregation=allow_aggregation),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )
  concept_parser = concept_parsers.ConceptParser.ForResource(
      '--location', resource_spec, group_help_text, required=required
  )
  concept_parser.AddToParser(parser)


def AddProjectResourceArg(parser):
  """Adds a resource argument for a project."""
  resource_spec = concepts.ResourceSpec(
      'eventarc.projects',
      resource_name='project',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )
  concept_parser = concept_parsers.ConceptParser.ForResource(
      '--project',
      resource_spec,
      'Project ID of the Google Cloud project for the {resource}.',
      required=True,
  )
  concept_parser.AddToParser(parser)


def AddTriggerResourceArg(parser, group_help_text, required=False):
  """Adds a resource argument for an Eventarc trigger."""
  concept_parsers.ConceptParser.ForResource(
      'trigger', TriggerResourceSpec(), group_help_text, required=required
  ).AddToParser(parser)


def AddCreateTrigerResourceArgs(parser, release_track):
  """Adds trigger and channel arguments to for trigger creation."""
  if release_track == base.ReleaseTrack.GA:
    concept_parsers.ConceptParser(
        [
            presentation_specs.ResourcePresentationSpec(
                'trigger',
                TriggerResourceSpec(),
                'The trigger to create.',
                required=True,
            ),
            presentation_specs.ResourcePresentationSpec(
                '--channel',
                ChannelResourceSpec(),
                'The channel to use in the trigger. The channel is needed only'
                ' if trigger is created for a third-party provider.',
                flag_name_overrides={'location': ''},
            ),
        ],
        # This configures the fallthrough from the channel 's location to
        # the primary flag for the trigger's location.
        command_level_fallthroughs={'--channel.location': ['trigger.location']},
    ).AddToParser(parser)
  else:
    AddTriggerResourceArg(parser, 'The trigger to create.', required=True)


def AddChannelResourceArg(parser, group_help_text, required=False):
  """Adds a resource argument for an Eventarc channel."""
  concept_parsers.ConceptParser.ForResource(
      'channel', ChannelResourceSpec(), group_help_text, required=required
  ).AddToParser(parser)


def AddChannelConnectionResourceArg(parser, group_help_text):
  """Adds a resource argument for an Eventarc channel connection."""
  concept_parsers.ConceptParser.ForResource(
      'channel_connection',
      ChannelConnectionResourceSpec(),
      group_help_text,
      required=True,
  ).AddToParser(parser)


def AddProviderResourceArg(parser, group_help_text, required=False):
  """Adds a resource argument for an Eventarc provider."""
  concept_parsers.ConceptParser.ForResource(
      'provider', ProviderResourceSpec(), group_help_text, required=required
  ).AddToParser(parser)


def AddMessageBusResourceArg(parser, group_help_text, required=False):
  """Adds a resource argument for an Eventarc MessageBus."""
  concept_parsers.ConceptParser.ForResource(
      'message_bus',
      MessageBusResourceSpec(),
      group_help_text,
      required=required,
  ).AddToParser(parser)


def AddGoogleApiSourceResourceArg(parser, group_help_text, required=False):
  """Adds a resource argument for an Eventarc GoogleApiSource."""
  concept_parsers.ConceptParser.ForResource(
      'google_api_source',
      GoogleApiSourceResourceSpec(),
      group_help_text,
      required=required,
  ).AddToParser(parser)


def AddCreateGoogleApiSourceResourceArgs(parser):
  """Adds resource arguments for creating an Eventarc GoogleApiSource."""
  _AddGoogleApiSourceResourceArgs(
      parser,
      google_api_source_help_text='The Google API source to create.',
      destination_required=True,
  )


def AddUpdateGoogleApiSourceResourceArgs(parser):
  """Adds resource arguments for updating an Eventarc GoogleApiSource."""
  _AddGoogleApiSourceResourceArgs(
      parser,
      google_api_source_help_text='The Google API source to update.',
      destination_required=False,
  )


def _AddGoogleApiSourceResourceArgs(
    parser, google_api_source_help_text, destination_required=False
):
  concept_parsers.ConceptParser(
      [
          presentation_specs.ResourcePresentationSpec(
              'google_api_source',
              GoogleApiSourceResourceSpec(),
              google_api_source_help_text,
              required=True,
          ),
          presentation_specs.ResourcePresentationSpec(
              '--destination-message-bus',
              MessageBusResourceSpec(),
              'The destination message bus of the Google API source.',
              required=destination_required,
              flag_name_overrides={
                  'location': '',
                  'project': '--destination-message-bus-project',
              },
          ),
      ],
      command_level_fallthroughs={
          '--destination-message-bus.location': ['google_api_source.location']
      },
  ).AddToParser(parser)


def AddEnrollmentResourceArg(parser, group_help_text, required=False):
  """Adds a resource argument for an Eventarc Enrollment."""
  concept_parsers.ConceptParser.ForResource(
      'enrollment',
      EnrollmentResourceSpec(),
      group_help_text,
      required=required,
  ).AddToParser(parser)


def AddCreateEnrollmentResourceArgs(parser):
  """Adds a resource argument for an Eventarc Enrollment."""
  destination_group = parser.add_mutually_exclusive_group(required=True)
  concept_parsers.ConceptParser(
      [
          presentation_specs.ResourcePresentationSpec(
              'enrollment',
              EnrollmentResourceSpec(),
              'The enrollment to create.',
              required=True,
          ),
          presentation_specs.ResourcePresentationSpec(
              '--message-bus',
              MessageBusResourceSpec(),
              'The message bus to which the enrollment attaches.',
              required=True,
              flag_name_overrides={
                  'location': '',
                  'project': '--message-bus-project',
              },
          ),
          presentation_specs.ResourcePresentationSpec(
              '--destination-pipeline',
              PipelineResourceSpec(resource_name='destination pipeline'),
              'The destination pipeline of the enrollment.',
              group=destination_group,
              flag_name_overrides={'location': ''},
          ),
      ],
      # This configures the fallthrough from the message bus' location and the
      # pipeline's location to the primary flag for the enrollment's location.
      command_level_fallthroughs={
          '--message-bus.location': ['enrollment.location'],
          '--destination-pipeline.location': ['enrollment.location'],
      },
  ).AddToParser(parser)


def AddUpdateEnrollmentResourceArgs(parser):
  """Adds resource arguments for updating an Eventarc Enrollment."""
  destination_group = parser.add_mutually_exclusive_group()
  concept_parsers.ConceptParser(
      [
          presentation_specs.ResourcePresentationSpec(
              'enrollment',
              EnrollmentResourceSpec(),
              'The enrollment to update.',
              required=True,
          ),
          presentation_specs.ResourcePresentationSpec(
              '--destination-pipeline',
              PipelineResourceSpec(),
              'The destination pipeline of the enrollment.',
              group=destination_group,
              flag_name_overrides={'location': ''},
          ),
      ],
      # This configures the fallthrough from the pipeline's location to the
      # primary flag for the enrollment's location.
      command_level_fallthroughs={
          '--destination-pipeline.location': ['enrollment.location'],
      },
  ).AddToParser(parser)


def AddPipelineResourceArg(parser, group_help_text, required=False):
  """Adds a resource argument for an Eventarc pipeline."""
  concept_parsers.ConceptParser.ForResource(
      'pipeline',
      PipelineResourceSpec(),
      group_help_text,
      required=required,
  ).AddToParser(parser)


def AddKafkaSourceResourceArg(parser, group_help_text, required=False):
  """Adds a resource argument for an Eventarc Kafka source."""
  concept_parsers.ConceptParser.ForResource(
      'kafka_source',
      KafkaSourceResourceSpec(),
      group_help_text,
      required=required,
  ).AddToParser(parser)


def AddProviderNameArg(parser):
  """Adds an argument for an Eventarc provider name."""
  parser.add_argument(
      '--name',
      required=False,
      help=(
          'A provider name (e.g. `storage.googleapis.com`) List results will be'
          ' filtered on this provider. Only exact match of the provider name is'
          ' supported.'
      ),
  )


def AddMessageBusPublishingArgs(parser):
  """Adds arguments for publishing to an Eventarc message bus."""
  payload_group = parser.add_mutually_exclusive_group(required=True)
  protobuf_payload_group = payload_group.add_group()
  AddEventPublishingArgs(protobuf_payload_group)
  payload_group.add_argument(
      '--json-message',
      help='A JSON message to publish to the message bus.',
  )
  payload_group.add_argument(
      '--avro-message',
      help='An Avro message to publish to the message bus.',
  )


def AddEventPublishingArgs(parser):
  """Adds arguments for publishing a Cloud Event to Eventarc resources."""
  parser.add_argument(
      '--event-id',
      required=True,
      help='An event id. The id of a published event.',
  )

  parser.add_argument(
      '--event-type',
      required=True,
      help='An event type. The event type of a published event.',
  )

  parser.add_argument(
      '--event-source',
      required=True,
      help='An event source. The event source of a published event.',
  )

  parser.add_argument(
      '--event-data',
      required=True,
      help='An event data. The event data of a published event.',
  )

  parser.add_argument(
      '--event-attributes',
      action=arg_parsers.UpdateAction,
      type=arg_parsers.ArgDict(),
      metavar='ATTRIBUTE=VALUE',
      help=(
          'Event attributes. The event attributes of a published event.'
          'This flag can be repeated to add more attributes.'
      ),
  )


def AddServiceAccountArg(parser, required=False):
  """Adds an argument for the trigger's service account."""
  parser.add_argument(
      '--service-account',
      required=required,
      help='The IAM service account email associated with the trigger.',
  )


def AddEventFiltersArg(parser, release_track, required=False):
  """Adds an argument for the trigger's event filters."""
  if release_track == base.ReleaseTrack.GA:
    flag = '--event-filters'
    help_text = (
        "The trigger's list of filters that apply to CloudEvents attributes. "
        'This flag can be repeated to add more filters to the list. Only '
        'events that match all these filters will be sent to the destination. '
        "The filters must include the ``type'' attribute, as well as any other "
        'attributes that are expected for the chosen type.'
    )
  else:
    flag = '--matching-criteria'
    help_text = (
        'The criteria by which events are filtered for the trigger, specified '
        'as a comma-separated list of CloudEvents attribute names and values. '
        'This flag can also be repeated to add more criteria to the list. Only '
        'events that match with this criteria will be sent to the destination. '
        "The criteria must include the ``type'' attribute, as well as any "
        'other attributes that are expected for the chosen type.'
    )
  parser.add_argument(
      flag,
      action=arg_parsers.UpdateAction,
      type=arg_parsers.ArgDict(),
      required=required,
      help=help_text,
      metavar='ATTRIBUTE=VALUE',
  )


def AddEventFiltersPathPatternArg(
    parser, release_track, required=False, hidden=False
):
  """Adds an argument for the trigger's event filters in path pattern format."""
  if release_track == base.ReleaseTrack.GA:
    parser.add_argument(
        '--event-filters-path-pattern',
        action=arg_parsers.UpdateAction,
        type=arg_parsers.ArgDict(),
        hidden=hidden,
        required=required,
        help=(
            "The trigger's list of filters in path pattern format that apply to"
            ' CloudEvent attributes. This flag can be repeated to add more'
            ' filters to the list. Only events that match all these filters'
            ' will be sent to the destination. Currently, path pattern format'
            ' is only available for the resourceName attribute for Cloud Audit'
            ' Log events.'
        ),
        metavar='ATTRIBUTE=PATH_PATTERN',
    )


def AddEventDataContentTypeArg(
    parser, release_track, required=False, hidden=False
):
  """Adds an argument for the trigger's event data content type."""
  if release_track == base.ReleaseTrack.GA:
    parser.add_argument(
        '--event-data-content-type',
        hidden=hidden,
        required=required,
        help=(
            'Depending on the event provider, you can specify the encoding of'
            ' the event data payload that will be delivered to your'
            " destination, to either be encoded in ``application/json'' or"
            " ``application/protobuf''. The default encoding is"
            " ``application/json''."
            ' Note that for custom sources or third-party providers, or for'
            ' direct events from Cloud Pub/Sub, this formatting option is not'
            ' supported.'
        ),
    )


def GetEventFiltersArg(args, release_track):
  """Gets the event filters from the arguments."""
  if release_track == base.ReleaseTrack.GA:
    return args.event_filters
  else:
    return args.matching_criteria


def GetEventFiltersPathPatternArg(args, release_track):
  """Gets the event filters with path pattern from the arguments."""
  if release_track == base.ReleaseTrack.GA:
    return args.event_filters_path_pattern
  return None


def GetEventDataContentTypeArg(args, release_track):
  """Gets the event data content type from the arguments."""
  if release_track == base.ReleaseTrack.GA:
    return args.event_data_content_type
  return None


def GetChannelArg(args, release_track):
  """Gets the channel from the arguments."""
  if release_track == base.ReleaseTrack.GA:
    return args.CONCEPTS.channel.Parse()
  return None


def AddCreateDestinationArgs(parser, release_track, required=False):
  """Adds arguments related to trigger's destination for create operations."""
  dest_group = parser.add_mutually_exclusive_group(
      required=required,
      help=(
          'Flags for specifying the destination to which events should be sent.'
      ),
  )
  _AddCreateCloudRunDestinationArgs(dest_group, release_track)
  if release_track == base.ReleaseTrack.GA:
    _AddCreateGKEDestinationArgs(dest_group)
    _AddCreateWorkflowDestinationArgs(dest_group)
    _AddCreateFunctionDestinationArgs(dest_group, hidden=True)
    _AddCreateHTTPEndpointDestinationArgs(dest_group)


def _AddCreateCloudRunDestinationArgs(parser, release_track, required=False):
  """Adds arguments related to trigger's Cloud Run fully-managed resource destination for create operations."""
  run_group = parser.add_group(
      required=required,
      help=(
          'Flags for specifying a Cloud Run fully-managed resource destination.'
      ),
  )
  resource_group = run_group.add_mutually_exclusive_group(required=True)
  AddDestinationRunServiceArg(resource_group)
  # When this is not True and only the service flag is in the mutually exclusive
  # group, it will appear the same as if it was directly in the base run_group.
  if release_track == base.ReleaseTrack.GA:
    AddDestinationRunJobArg(resource_group)
  AddDestinationRunPathArg(run_group)
  AddDestinationRunRegionArg(run_group)


def _AddCreateGKEDestinationArgs(parser, required=False, hidden=False):
  """Adds arguments related to trigger's GKE service destination for create operations."""
  gke_group = parser.add_group(
      required=required,
      hidden=hidden,
      help='Flags for specifying a GKE service destination.',
  )
  _AddDestinationGKEClusterArg(gke_group, required=True)
  _AddDestinationGKELocationArg(gke_group)
  _AddDestinationGKENamespaceArg(gke_group)
  _AddDestinationGKEServiceArg(gke_group, required=True)
  _AddDestinationGKEPathArg(gke_group)


def _AddCreateWorkflowDestinationArgs(parser, required=False, hidden=False):
  """Adds arguments related to trigger's Workflows destination for create operations."""
  workflow_group = parser.add_group(
      required=required,
      hidden=hidden,
      help='Flags for specifying a Cloud Workflows destination.',
  )
  _AddDestinationWorkflowArg(workflow_group, required=True)
  _AddDestinationWorkflowLocationArg(workflow_group)


def _AddCreateHTTPEndpointDestinationArgs(parser, required=False, hidden=False):
  """Adds arguments related to trigger's HTTP Endpoint destination for create operations."""
  http_endpoint_group = parser.add_group(
      required=required,
      hidden=hidden,
      help='Flags for specifying a HTTP Endpoint destination.',
  )
  _AddDestinationHTTPEndpointUriArg(http_endpoint_group, required=True)
  _AddCreateNetworkConfigDestinationArgs(http_endpoint_group)


def _AddCreateNetworkConfigDestinationArgs(
    parser, required=False, hidden=False
):
  """Adds arguments related to trigger's Network Config destination for create operations."""
  network_config_group = parser.add_group(
      required=required,
      hidden=hidden,
      help='Flags for specifying a Network Config for the destination.',
  )
  _AddNetworkAttachmentArg(network_config_group, required=True)


def _AddCreateFunctionDestinationArgs(parser, required=False, hidden=False):
  """Adds arguments related to trigger's Function destination for create operation."""
  function_group = parser.add_group(
      required=required,
      hidden=hidden,
      help='Flags for specifying a Function destination.',
  )
  _AddDestinationFunctionArg(function_group, required=True)
  _AddDestinationFunctionLocationArg(function_group)


def AddUpdateDestinationArgs(parser, release_track, required=False):
  """Adds arguments related to trigger's destination for update operations."""
  dest_group = parser.add_mutually_exclusive_group(
      required=required,
      help='Flags for updating the destination to which events should be sent.',
  )
  _AddUpdateCloudRunDestinationArgs(dest_group, release_track)
  if release_track == base.ReleaseTrack.GA:
    _AddUpdateGKEDestinationArgs(dest_group)
    _AddUpdateWorkflowDestinationArgs(dest_group)
    _AddUpdateFunctionDestinationArgs(dest_group, hidden=True)


def _AddUpdateCloudRunDestinationArgs(parser, release_track, required=False):
  """Adds arguments related to trigger's Cloud Run fully-managed resource destination for update operations."""
  run_group = parser.add_group(
      required=required,
      help='Flags for updating a Cloud Run fully-managed resource destination.',
  )
  resource_group = run_group.add_mutually_exclusive_group()
  AddDestinationRunServiceArg(resource_group)
  # When this is not True and only the service flag is in the mutually exclusive
  # group, it will appear the same as if it was directly in the base run_group.
  if release_track == base.ReleaseTrack.GA:
    AddDestinationRunJobArg(resource_group)
  AddDestinationRunRegionArg(run_group)
  destination_run_path_group = run_group.add_mutually_exclusive_group()
  AddDestinationRunPathArg(destination_run_path_group)
  AddClearDestinationRunPathArg(destination_run_path_group)


def _AddUpdateGKEDestinationArgs(parser, required=False, hidden=False):
  """Adds arguments related to trigger's GKE service destination for update operations."""
  gke_group = parser.add_group(
      required=required,
      hidden=hidden,
      help='Flags for updating a GKE service destination.',
  )
  _AddDestinationGKENamespaceArg(gke_group)
  _AddDestinationGKEServiceArg(gke_group)
  destination_gke_path_group = gke_group.add_mutually_exclusive_group()
  _AddDestinationGKEPathArg(destination_gke_path_group)
  _AddClearDestinationGKEPathArg(destination_gke_path_group)


def _AddUpdateWorkflowDestinationArgs(parser, required=False, hidden=False):
  """Adds arguments related to trigger's Workflow destination for update operations."""
  workflow_group = parser.add_group(
      required=required,
      hidden=hidden,
      help='Flags for updating a Cloud Workflows destination.',
  )
  _AddDestinationWorkflowArg(workflow_group)
  _AddDestinationWorkflowLocationArg(workflow_group)


def _AddUpdateFunctionDestinationArgs(parser, required=False, hidden=False):
  """Adds arguments related to trigger's Function destination for update operations."""
  function_group = parser.add_group(
      required=required,
      hidden=hidden,
      help='Flags for updating a Function destination.',
  )
  _AddDestinationFunctionArg(function_group)
  _AddDestinationFunctionLocationArg(function_group)


def AddDestinationRunServiceArg(parser):
  """Adds an argument for the trigger's destination Cloud Run service."""
  parser.add_argument(
      '--destination-run-service',
      help=(
          'Name of the Cloud Run fully-managed service that receives the events'
          ' for the trigger. The service must be in the same project as the'
          ' trigger.'
      ),
  )


def AddDestinationRunJobArg(parser):
  """Adds an argument for the trigger's destination Cloud Run job."""
  parser.add_argument(
      '--destination-run-job',
      hidden=True,
      help=(
          'Name of the Cloud Run fully-managed job that receives the '
          'events for the trigger. The job must be in the same project as the '
          'trigger.'
      ),
  )


def AddDestinationRunPathArg(parser, required=False):
  """Adds an argument for the trigger's destination path on the Cloud Run service."""
  parser.add_argument(
      '--destination-run-path',
      required=required,
      help=(
          'Relative path on the destination Cloud Run service to which '
          "the events for the trigger should be sent. Examples: ``/route'', "
          "``route'', ``route/subroute''."
      ),
  )


def AddDestinationRunRegionArg(parser, required=False):
  """Adds an argument for the trigger's destination Cloud Run service's region."""
  parser.add_argument(
      '--destination-run-region',
      required=required,
      help=(
          'Region in which the destination Cloud Run service can be found. If'
          ' not specified, it is assumed that the service is in the same region'
          ' as the trigger.'
      ),
  )


def _AddDestinationGKEClusterArg(parser, required=False):
  """Adds an argument for the trigger's destination GKE service's cluster."""
  parser.add_argument(
      '--destination-gke-cluster',
      required=required,
      help=(
          'Name of the GKE cluster that the destination GKE service is '
          'running in.  The cluster must be in the same project as the trigger.'
      ),
  )


def _AddDestinationGKELocationArg(parser, required=False):
  """Adds an argument for the trigger's destination GKE service's location."""
  parser.add_argument(
      '--destination-gke-location',
      required=required,
      help=(
          'Location of the GKE cluster that the destination GKE service is'
          ' running in. If not specified, it is assumed that the cluster is a'
          ' regional cluster and is in the same region as the trigger.'
      ),
  )


def _AddDestinationGKENamespaceArg(parser, required=False):
  """Adds an argument for the trigger's destination GKE service's namespace."""
  parser.add_argument(
      '--destination-gke-namespace',
      required=required,
      help=(
          'Namespace that the destination GKE service is running in. If '
          "not specified, the ``default'' namespace is used."
      ),
  )


def _AddDestinationGKEServiceArg(parser, required=False):
  """Adds an argument for the trigger's destination GKE service's name."""
  parser.add_argument(
      '--destination-gke-service',
      required=required,
      help=(
          'Name of the destination GKE service that receives the events '
          'for the trigger.'
      ),
  )


def _AddDestinationGKEPathArg(parser, required=False):
  """Adds an argument for the trigger's destination GKE service's name."""
  parser.add_argument(
      '--destination-gke-path',
      required=required,
      help=(
          'Relative path on the destination GKE service to which '
          "the events for the trigger should be sent. Examples: ``/route'', "
          "``route'', ``route/subroute''."
      ),
  )


def _AddDestinationWorkflowArg(parser, required=False):
  """Adds an argument for the trigger's destination Workflow."""
  parser.add_argument(
      '--destination-workflow',
      required=required,
      help=(
          'ID of the workflow that receives the events for the trigger. '
          'The workflow must be in the same project as the trigger.'
      ),
  )


def _AddDestinationWorkflowLocationArg(parser, required=False):
  """Adds an argument for the trigger's destination Workflow location."""
  parser.add_argument(
      '--destination-workflow-location',
      required=required,
      help=(
          'Location that the destination workflow is running in. '
          'If not specified, it is assumed that the workflow is in the same '
          'location as the trigger.'
      ),
  )


def _AddDestinationFunctionArg(parser, required=False):
  """Adds an argument for the trigger's destination Function."""
  parser.add_argument(
      '--destination-function',
      required=required,
      help=(
          'ID of the Function that receives the events for the trigger. '
          'The Function must be in the same project as the trigger.'
      ),
  )


def _AddDestinationFunctionLocationArg(parser, required=False):
  """Adds an argument for the trigger's destination Function location."""
  parser.add_argument(
      '--destination-function-location',
      required=required,
      help=(
          'Location that the destination Function is running in. '
          'If not specified, it is assumed that the Function is in the same '
          'location as the trigger.'
      ),
  )


def _AddDestinationHTTPEndpointUriArg(parser, required=False):
  """Adds an argument for the trigger's HTTP endpoint destination URI."""
  parser.add_argument(
      '--destination-http-endpoint-uri',
      required=required,
      help='URI that the destination HTTP Endpoint is connecting to.',
  )


def _AddNetworkAttachmentArg(parser, required=False):
  """Adds an argument for the trigger's destination service account."""
  parser.add_argument(
      '--network-attachment',
      required=required,
      help=(
          'The network attachment associated with the trigger that allows'
          ' access to the destination VPC.'
      ),
  )


def AddClearServiceAccountArg(parser):
  parser.add_argument(
      '--clear-service-account',
      action='store_true',
      help='Clear the IAM service account associated with the trigger.',
  )


def AddClearDestinationRunPathArg(parser):
  """Adds an argument for clearing the trigger's Cloud Run destination path."""
  parser.add_argument(
      '--clear-destination-run-path',
      action='store_true',
      help=(
          'Clear the relative path on the destination Cloud Run service to '
          'which the events for the trigger should be sent.'
      ),
  )


def _AddClearDestinationGKEPathArg(parser):
  """Adds an argument for clearing the trigger's GKE destination path."""
  parser.add_argument(
      '--clear-destination-gke-path',
      action='store_true',
      help=(
          'Clear the relative path on the destination GKE service to which '
          'the events for the trigger should be sent.'
      ),
  )


def AddTypePositionalArg(parser, help_text):
  """Adds a positional argument for the event type."""
  parser.add_argument('type', help=help_text)


def AddTypeArg(parser, required=False):
  """Adds an argument for the event type."""
  parser.add_argument('--type', required=required, help='The event type.')


def AddServiceNameArg(parser, required=False):
  """Adds an argument for the value of the serviceName CloudEvents attribute."""
  parser.add_argument(
      '--service-name',
      required=required,
      help='The value of the serviceName CloudEvents attribute.',
  )


def AddCreateChannelArg(parser):
  concept_parsers.ConceptParser(
      [
          presentation_specs.ResourcePresentationSpec(
              'channel',
              ChannelResourceSpec(),
              'Channel to create.',
              required=True,
          ),
          presentation_specs.ResourcePresentationSpec(
              '--provider',
              ProviderResourceSpec(),
              'Provider to use for the channel.',
              flag_name_overrides={'location': ''},
          ),
      ],
      # This configures the fallthrough from the provider's location to the
      # primary flag for the channel's location
      command_level_fallthroughs={'--provider.location': ['channel.location']},
  ).AddToParser(parser)


def AddCryptoKeyArg(parser, required=False, hidden=False, with_clear=True):
  """Adds an argument for the crypto key used for CMEK."""
  policy_group = parser
  if with_clear:
    policy_group = parser.add_mutually_exclusive_group(hidden=hidden)
    AddClearCryptoNameArg(policy_group, required, hidden)
  policy_group.add_argument(
      '--crypto-key',
      required=required,
      hidden=hidden,
      help=(
          'Fully qualified name of the crypto key to use for '
          'customer-managed encryption. If this is unspecified, Google-managed '
          'keys will be used for encryption.'
      ),
  )


def AddClearCryptoNameArg(parser, required=False, hidden=False):
  """Adds an argument for the crypto key used for CMEK."""
  parser.add_argument(
      '--clear-crypto-key',
      required=required,
      hidden=hidden,
      default=False,
      action='store_true',
      help=(
          'Remove the previously configured crypto key. The channel will'
          ' continue to be encrypted using Google-managed keys.'
      ),
  )


def AddCelMatchArg(parser, required=False):
  """Adds an argument for the cel match expression."""
  parser.add_argument(
      '--cel-match',
      required=required,
      help='The cel match expression for the enrollment.',
  )


def AddLoggingConfigArg(parser, help_text):
  """Adds an argument for the logging config of the resource."""
  parser.add_argument(
      '--logging-config',
      choices=[
          'NONE',
          'DEBUG',
          'INFO',
          'NOTICE',
          'WARNING',
          'ERROR',
          'CRITICAL',
          'ALERT',
          'EMERGENCY',
      ],
      required=False,
      help=help_text,
  )


def AddPipelineDestinationsArg(parser, required=False):
  """Adds an argument for the pipeline's HTTP endpoint destination."""
  help_text = """
The pipeline's destinations. This flag can be repeated to add more destinations
to the list. Currently, only one destination is supported per pipeline. A
destination is specified in a dict format. For more
information, see
[Create an enrollment to receive events](https://cloud.google.com/eventarc/advanced/docs/receive-events/create-enrollment).

Note: Exactly one of the `http_endpoint_uri`,
`workflow`, `message_bus`, or `pubsub_topic` keys must be set.

Valid keys are:

*http_endpoint_uri*::: The URI of the HTTP endpoint. The value must be a RFC2396
URI string. Only HTTPS protocol is supported. The host can be either a static IP
addressable from the VPC specified by the network config, or an internal DNS
hostname of the service resolvable via Cloud DNS. For example:

    $ gcloud eventarc pipelines create example-pipeline --destinations=http_endpoint_uri='https://example.com',network_attachment=example-network-attachment

*http_endpoint_message_binding_template*::: The CEL expression used to construct
a new HTTP request to be sent to the final destination. It can be optionally
specified alongside with `http_endpoint_uri`. It represents a configuration used
to bind a message to the final HTTP request that will be sent to the destination.
If a binding is not specified, by default the message is treated as a CloudEvent
and is mapped to the HTTP request according to the CloudEvent HTTP Protocol
Binding Binary Content Mode. The pipeline converts the data field of the message
to the format provided in `output_payload_format` and maps it to the body field
of the result. It also sets the corresponding Content-Type header to the
`output_payload_format` type. If the `output_payload_format` is unspecified,
then the pipeline will treat the data field of the message as opaque binary data
and attach it to the request body as bytes. In this case, the Content-Type
header will be set to the value of the datacontenttype attribute set on the
incoming CloudEvent message if present, or the `application/octet-stream` MIME
type otherwise. The pipeline expects that the content of the message will adhere
to the standard CloudEvent format. If not then the outgoing message request may
fail with a persistent error.

Note: When `http_endpoint_uri` is not set,
`http_endpoint_message_binding_template` can't be set.

The result of the CEL expression must be a map of key-value pairs such that:

1. If a map named `headers` exists on the result of the expression, then its
key-value pairs are directly mapped to the HTTP request headers. The headers
values are constructed from the corresponding value type's canonical
representation. If the `headers` field does not exist, then the resulting HTTP
request will not contain headers.

2. If a field named `body` exists on the result of the expression, then its
value is directly mapped to the body of the request. If the value of the `body`
field is of type bytes or string, then it is used as the HTTP request body
as-is withouth any conversion. If the `body` field is of any other type, then
it is converted to a JSON string. If the `body` field does not exist, then the
resulting HTTP request will not contain a body.

3. Any other fields in the resulting expression will be ignored.

The CEL expression may access the incoming CloudEvent message in its definition,
as follows:

1. The `data` field of the incoming CloudEvent message can be accessed using
the `message.data` value.

2. Each attribute of the incoming CloudEvent message can be accessed using the
`message.<key>` value, where <key> is the name of the attribute.

Headers added to the request by previous filters in the chain can be accessed in
the CEL expression using the `headers` variable. The `headers` variable defines
a map of key-value pairs corresponding to the HTTP headers added by previous
mediation steps and not the headers present on the original incoming request.
For example, the following CEL expression can be used to construct a
headers-only HTTP request by adding an additional header to the headers added by
previous mediations in the pipeline:

  ```
  {"headers": headers.merge({"new-header-key": "new-header-value"})}
  ```

Additionally, the following CEL extension functions can be used in this CEL
expression:

* `toBase64Url`: map.toBase64Url() -> string
  - Converts a CelValue to a base64url encoded string.

* `toJsonString`: map.toJsonString() -> string
  - Converts a CelValue to a JSON string.

* `merge`: map1.merge(map2) -> map3
  - Merges the passed CEL map with the existing CEL map the function is
    applied to. If the same key exists in both maps, or if the key's value is
    type map, then both maps are merged; Otherwise, the value from the passed
    map is used.

* `toMap`: list(map).toMap() -> map
  - Converts a CEL list of CEL maps to a single CEL map.

* `toDestinationPayloadFormat`: message.data.toDestinationPayloadFormat() -> string or bytes
  - Converts the message data to the destination payload format specified in
    `output_payload_format`. This function is meant to be applied to the
    message.data field. If the destination payload format is not set, the
    function will return the message data unchanged.

* `toCloudEventJsonWithPayloadFormat`: message.toCloudEventJsonWithPayloadFormat() -> map
  - Converts a message to the corresponding structure of JSON format for
    CloudEvents. This function applies toDestinationPayloadFormat() to the
    message data. It also sets the corresponding datacontenttype of the
    CloudEvent, as indicated by the `output_payload_format` field. If
    `output_payload_format` is not set, it will use the existing
    datacontenttype on the CloudEvent if present; Otherwise, it leaves the
    datacontenttype unset. This function expects that the content of the
    message will adhere to the standard CloudEvent format. If it doesn't then
    this function will fail. The result is a CEL map that corresponds to the
    JSON representation of the CloudEvent. To convert that data to a JSON
    string it can be chained with the toJsonString() function.

For example:

      $ gcloud eventarc pipelines create example-pipeline --destinations=http_endpoint_uri='https://example.com',http_endpoint_message_binding_template='{"headers": {"new-header-key": "new-header-value"}}',network_attachment=example-network-attachment

*workflow*::: The destination Workflow ID. For example:

    $ gcloud eventarc pipelines create example-pipeline --destinations=workflow=my-workflow

*message_bus*::: The destination Message Bus ID. For example:

    $ gcloud eventarc pipelines create example-pipeline --destinations=message_bus=my-message-bus

*pubsub_topic*::: The destination Pub/Sub topic ID. For example:

    $ gcloud eventarc pipelines create example-pipeline --destinations=pubsub_topic=my-topic

*project*::: The project ID of the destination resource. If `project` is not set,
then the project ID of the pipeline is used. For example:

    $ gcloud eventarc pipelines create example-pipeline --destinations=project=example-project,workflow=my-workflow

Note: When `http_endpoint_uri` is set, `project` can't be set.

*location*::: The location of the destination resource. If `location` is not set,
then the location of the pipeline is used. For example:

    $ gcloud eventarc pipelines create example-pipeline --destinations=location=us-east1,workflow=my-workflow,network_attachment=example-network-attachment

Note: When `http_endpoint_uri` is set, `location` can't be set.

*network_attachment*::: The ID of the network attachment that allows access to
the consumer VPC. For example:

    $ gcloud eventarc pipelines create example-pipeline --destinations=network_attachment=my-network-attachment,http_endpoint_uri='https://example.com'

Note: A network attachment must be specified for a pipeline when `http_endpoint_uri` is set.

*google_oidc_authentication_service_account*::: The service account email used
to generate the OIDC token. The token can be used to invoke Cloud Run and Cloud
Run functions destinations or HTTP endpoints that support Google OIDC. Note that
the principal who calls this API must have `iam.serviceAccounts.actAs`
permission on the service account. For more information, see
[Service accounts overview](https://cloud.google.com/iam/docs/understanding-service-accounts).
For example:

    $ gcloud eventarc pipelines create example-pipeline --destinations=http_endpoint_uri='https://example.com',network_attachment=example-network-attachment,google_oidc_authentication_service_account=example-service-account@example-project.gserviceaccount.iam.com

*google_oidc_authentication_audience*::: The audience claim which identifies the
recipient that the JWT is intended for. If unspecified, the destination URI will
be used. For example:

    $ gcloud eventarc pipelines create example-pipeline --destinations=http_endpoint_uri='https://example.com',network_attachment=example-network-attachment,google_oidc_authentication_service_account=example-service-account@example-project.gserviceaccount.iam.com,google_oidc_authentication_audience='https://example.com'

Note: `google_oidc_authentication_audience` can only be set if
`google_oidc_authentication_service_account` is set.

*oauth_token_authentication_service_account*::: The service account email used
to generate the OAuth token. OAuth authorization should generally only be used
when calling Google APIs hosted on *.googleapis.com. Note that the principal who
calls this API must have iam.serviceAccounts.actAs permission in the service
account. For more information, see
[Service accounts overview](https://cloud.google.com/iam/docs/understanding-service-accounts).
For example:

    $ gcloud eventarc pipelines create example-pipeline --destinations=http_endpoint_uri='https://example.com',network_attachment=example-network-attachment,oauth_token_authentication_service_account=example-service-account@example-project.gserviceaccount.iam.com

*oauth_token_authentication_scope*::: The scope used to generate the OAuth token.
  If unspecified, "https://www.googleapis.com/auth/cloud-platform" will be used.
  For example:

    $ gcloud eventarc pipelines create example-pipeline --destinations=http_endpoint_uri='https://example.com',network_attachment=example-network-attachment,oauth_token_authentication_service_account=example-service-account@example-project.gserviceaccount.iam.com,oauth_token_authentication_scope=https://www.googleapis.com/auth/cloud-platform

Note: At most one of `google_oidc_authentication_service_account` or
`oauth_token_authentication_service_account` can be set; and
`oauth_token_authentication_scope` can only be set if
`oauth_token_authentication_service_account` is set.

*output_payload_format_json*::: Indicates that the output payload format is JSON.
For example:

    $ gcloud eventarc pipelines create example-pipeline --destinations=http_endpoint_uri='https://example.com',network_attachment=example-network-attachment,output_payload_format_json= --input-payload-format-json=

Note: JSON schemas are not supported. Any value specified by this key is ignored.

*output_payload_format_avro_schema_definition*::: The schema definition of the
Avro output payload format. For example:

    $ gcloud eventarc pipelines create example-pipeline --destinations=http_endpoint_uri='https://example.com',network_attachment=example-network-attachment,output_payload_format_avro_schema_definition='{"type": "record", "name": "my_record", "fields": [{"name": "field1", "type": "string"}]}' --input-payload-format-avro-schema-definition='{"type": "record", "name": "my_record", "fields": [{"name": "field1", "type": "string"}]}'

*output_payload_format_protobuf_schema_definition*::: The schema definition of
the Protobuf output payload format. For example:

    $ gcloud eventarc pipelines create example-pipeline --destinations=http_endpoint_uri='https://example.com',network_attachment=example-network-attachment,output_payload_format_protobuf_schema_definition='syntax = "proto3"; message Location { string home_address = 1; }' --input-payload-format-protobuf-schema-definition='syntax = "proto3"; message Location { string home_address = 1; }'

Note: If none of the `input_payload_format_json`,
`input_payload_format_avro_schema_definition`, or
`input_payload_format_protobuf_schema_definition` is set, then the message data
is treated as an opaque binary and no output format can be set on the pipeline
through the `output_payload_format_json`,
`output_payload_format_avro_schema_definition`, or
`output_payload_format_protobuf_schema_definition` field. Any mediations on the
pipeline that involve access to the data field will fail as persistent errors.
  """
  parser.add_argument(
      '--destinations',
      type=arg_parsers.ArgList(
          element_type=arg_parsers.ArgDict(
              spec={
                  'http_endpoint_uri': str,
                  'http_endpoint_message_binding_template': str,
                  'workflow': str,
                  'message_bus': str,
                  'pubsub_topic': str,
                  'project': str,
                  'location': str,
                  'network_attachment': str,
                  'google_oidc_authentication_service_account': str,
                  'google_oidc_authentication_audience': str,
                  'oauth_token_authentication_service_account': str,
                  'oauth_token_authentication_scope': str,
                  'output_payload_format_json': None,
                  'output_payload_format_avro_schema_definition': str,
                  'output_payload_format_protobuf_schema_definition': str,
              },
              allow_key_only=True,
              includes_json=True,
          ),
          min_length=1,
          custom_delim_char='|',
      ),
      action=arg_parsers.UpdateAction,
      required=required,
      help=help_text,
      metavar='[http_endpoint_uri=URI],[http_endpoint_message_binding_template=HTTP_ENDPOINT_MESSAGE_BINDING_TEMPLATE],[workflow=WORKFLOW],[message_bus=MESSAGE_BUS],[pubsub_topic=PUBSUB_TOPIC],[project=PROJECT],[location=LOCATION],[network_attachment=NETWORK_ATTACHMENT],[google_oidc_authentication_service_account=GOOGLE_OIDC_AUTHENTICATION_SERVICE_ACCOUNT],[google_oidc_authentication_audience=GOOGLE_OIDC_AUTHENTICATION_AUDIENCE],[oauth_token_authentication_service_account=OAUTH_TOKEN_AUTHENTICATION_SERVICE_ACCOUNT],[oauth_token_authentication_scope=OAUTH_TOKEN_AUTHENTICATION_SCOPE],[output_payload_format_json=OUTPUT_PAYLOAD_FORMAT_JSON],[output_payload_format_avro_schema_definition=OUTPUT_PAYLOAD_FORMAT_AVRO_SCHEMA_DEFINITION],[output_payload_format_protobuf_schema_definition=OUTPUT_PAYLOAD_FORMAT_PROTOBUF_SCHEMA_DEFINITION]',
  )


def AddMediationsArg(parser):
  """Adds an argument for the pipeline's mediations."""
  help_text = """
The different ways to modify the pipeline.
Currently, only one mediation is supported per pipeline.

A mediation is specified in a dict format. Currently, the only valid choice is `transformation_template`.

This is the template to apply to transform messages.

For complex transformations, shell parameter processing may fail to parse the CEL expressions.
Please see `gcloud topic flags-file` for how to use  https://cloud.google.com/sdk/gcloud/reference/topic/flags-file feature of gcloud to pass in CEL expressions.

Examples:

  $ gcloud eventarc pipelines create example-pipeline --mediations=transformation_template='message.removeFields(["data.credit_card_number","data.ssn"])'
  """
  parser.add_argument(
      '--mediations',
      type=arg_parsers.ArgList(
          element_type=arg_parsers.ArgDict(
              spec={
                  'transformation_template': str,
              },
              includes_json=True,
          ),
          custom_delim_char='|',
      ),
      help=help_text,
      metavar='transformation_template=TRANSFORMATION_TEMPLATE',
  )


def AddInputPayloadFormatArgs(parser):
  """Adds arguments for the pipeline's input payload format."""
  input_payload_format_group = parser.add_mutually_exclusive_group()
  input_payload_format_group.add_argument(
      '--input-payload-format-json',
      help=(
          "The pipeline's input payload format is JSON. If this is set, then"
          ' any messages not matching this format will be treated as persistent'
          ' errors.'
      ),
  )
  input_payload_format_group.add_argument(
      '--input-payload-format-avro-schema-definition',
      help=(
          "The pipeline's input payload Avro schema definition. If this is set,"
          ' then any messages not matching this format will be treated as'
          ' persistent errors.'
      ),
  )
  input_payload_format_group.add_argument(
      '--input-payload-format-protobuf-schema-definition',
      help=(
          "The pipeline's input payload Protobuf schema definition. If this is"
          ' set, then any messages not matching this format will be treated as'
          ' persistent errors.'
      ),
  )


def AddRetryPolicyArgs(parser):
  """Adds arguments for the pipeline's retry policy."""
  retry_policy_group = parser.add_group(help="""
The retry policy configuration for the pipeline.
The pipeline exponentially backs off if the destination is non-responsive or returns a retryable error code.
The backoff starts with a 1 second delay and doubles the delay after each failed attempt. The delay is capped at 60 seconds.
If the max-retry-delay and min-retry-delay are set to the same value, then the duration between retries is constant.
""")
  retry_policy_group.add_argument(
      '--max-retry-attempts',
      type=int,
      help=(
          'The maximum number of retry attempts. If not set, the default value'
          ' is 5.'
      ),
  )
  retry_policy_group.add_argument(
      '--min-retry-delay',
      help=(
          'The minimum retry delay in seconds. If not set, the default value'
          ' is 1.'
      ),
  )
  retry_policy_group.add_argument(
      '--max-retry-delay',
      help=(
          'The maximum retry delay in seconds. If not set, the default value'
          ' is 60.'
      ),
  )


def AddKafkaSourceBootstrapServersArg(parser, required=False):
  """Adds an argument for the Kafka Source's bootstrap server URIs."""
  help_text = """
The Kafka bootstrap server URIs, in the format <hostname>:<port>
This flag can be repeated to add more URIs to the list, or comma-separated.
At least one URI must be specified.

Examples:

  $ gcloud eventarc kafka-sources create example-kafka-source --bootstrap-servers='broker-1.private:9092,broker-2.private:9092'
"""
  parser.add_argument(
      '--bootstrap-servers',
      metavar='BOOTSTRAP_SERVER',
      type=arg_parsers.ArgList(min_length=1, element_type=str),
      required=required,
      help=help_text,
  )


def AddKafkaSourceTopicArg(parser, required=False):
  """Adds an argument for the Kafka Source's topic."""
  help_text = """
  The Kafka topic(s) to subscribe to. At least one topic must be specified.
  Examples:

  $ gcloud eventarc kafka-sources create example-kafka-source --topics='topic1,topic2'
  """
  parser.add_argument(
      '--topics',
      metavar='KAFKA_TOPIC',
      type=arg_parsers.ArgList(min_length=1, element_type=str),
      required=required,
      help=help_text,
  )


def AddKafkaSourceConsumerGroupIDArg(parser, required=False):
  """Adds an argument for the Kafka Source's Consumer Group ID."""
  help_text = """
  The Kafka consumer group ID. If not specified, a random UUID will be generated.
  This consumer group ID is used by the Kafka cluster to record the current read
  offsets of any topics subscribed.
  Examples:

  $ gcloud eventarc kafka-sources create example-kafka-source --consumer-group-id='my-consumer-group'
  """
  parser.add_argument(
      '--consumer-group-id',
      type=str,
      required=required,
      help=help_text,
  )


def AddCreateKafkaSourceResourceArgs(parser):
  """Adds a resource argument for the Kafka Source's Message Bus."""
  help_text = """
  The message bus to which the Kafka source will send events.
  Examples:

  $ gcloud eventarc kafka-sources create example-kafka-source --message-bus=my-message-bus
  """
  concept_parsers.ConceptParser(
      [
          presentation_specs.ResourcePresentationSpec(
              'kafka_source',
              KafkaSourceResourceSpec(),
              'The Kafka source to create.',
              required=True,
          ),
          presentation_specs.ResourcePresentationSpec(
              '--message-bus',
              MessageBusResourceSpec(),
              help_text,
              required=True,
              flag_name_overrides={
                  'location': '',
                  'project': '--message-bus-project',
              },
          ),
      ],
      # This configures the fallthrough from the message bus' location to the
      # primary flag for the Kafka sources's location.
      command_level_fallthroughs={
          '--message-bus.location': ['kafka_source.location'],
      },
  ).AddToParser(parser)


def AddKafkaSourceInitialOffsetArg(parser, required=False):
  """Adds an argument for the Kafka Source's initial offset."""
  help_text = """
  The initial offset for the Kafka Source. If not specified, the default value is 'newest'.
  Examples:
  $ gcloud eventarc kafka-sources create example-kafka-source --initial-offset=oldest
  """
  parser.add_argument(
      '--initial-offset',
      type=str,
      choices=['newest', 'oldest'],
      required=required,
      help=help_text,
  )


def AddKafkaSourceAuthGroup(parser, required=False):
  """Adds an argument group for the Kafka Source's authentication."""
  auth_group = parser.add_mutually_exclusive_group(
      required=required,
      help=(
          'Flags for specifying the authentication method to use with the Kafka'
          ' broker.'
      ),
  )
  sasl_group = auth_group.add_group(
      mutex=False,
      help='Flags for specifying SASL authentication with the Kafka broker.',
  )
  _AddKafkaSourceSASLMechanismArg(sasl_group, required=True)
  _AddKafkaSourceSASLUsernameArg(sasl_group, required=True)
  _AddKafkaSourceSASLPasswordArg(sasl_group, required=True)
  tls_group = auth_group.add_group(
      hidden=True,
      mutex=False,
      help=(
          'Flags for specifying mutual TLS authentication with the Kafka'
          ' broker.'
      ),
  )
  _AddKafkaSourceTLSClientCertificateArg(tls_group, required=True)
  _AddKafkaSourceTLSClientKeyArg(tls_group, required=True)


def _AddKafkaSourceSASLMechanismArg(parser, required=False):
  """Adds an argument for the Kafka Source's SASL mechanism."""
  help_text = """
  The SASL mechanism to use for authentication with the Kafka broker.
  This flag cannot be set if --tls-client-certificate is set (using mutual TLS for authentication).
  Examples:
  $ gcloud eventarc kafka-sources create example-kafka-source --sasl-mechanism=plain
  """
  parser.add_argument(
      '--sasl-mechanism',
      type=str,
      choices=['PLAIN', 'SCRAM-SHA-256', 'SCRAM-SHA-512'],
      required=required,
      help=help_text,
  )


def _AddKafkaSourceSASLUsernameArg(parser, required=False):
  """Adds an argument for the Kafka Source's SASL username."""
  help_text = """
  The SASL username to use for authentication with the Kafka broker.
  This flag is required if --sasl-mechanism is set.
  Examples:
  $ gcloud eventarc kafka-sources create example-kafka-source --sasl-username='projects/123/secrets/my-username/versions/1'
  """
  parser.add_argument(
      '--sasl-username',
      type=str,
      required=required,
      help=help_text,
  )


def _AddKafkaSourceSASLPasswordArg(parser, required=False):
  """Adds an argument for the Kafka Source's SASL password."""
  help_text = """
  The SASL password to use for authentication with the Kafka broker.
  This flag is required if --sasl-mechanism is set.
  Examples:
  $ gcloud eventarc kafka-sources create example-kafka-source --sasl-password='projects/123/secrets/my-secret/versions/1'
  """
  parser.add_argument(
      '--sasl-password',
      type=str,
      required=required,
      help=help_text,
  )


def _AddKafkaSourceTLSClientCertificateArg(parser, required=False):
  """Adds an argument for the Kafka Source's mutual TLS Client Certificate."""
  help_text = """
  The mutual TLS Client Certificate to use for authentication with the Kafka broker.
  This option cannot be set if --sasl-mechanism is set.
  Examples:
  $ gcloud eventarc kafka-sources create example-kafka-source --tls-client-certificate='projects/123/secrets/my-certificate/versions/1'
  """
  parser.add_argument(
      '--tls-client-certificate',
      type=str,
      required=required,
      help=help_text,
  )


def _AddKafkaSourceTLSClientKeyArg(parser, required=False):
  """Adds an argument for the Kafka Source's mutual TLS Client Key."""
  help_text = """
  The mutual TLS Client Key to use for authentication with the Kafka broker.
  This option is required if --tls-client-certificate is set.
  Examples:
  $ gcloud eventarc kafka-sources create example-kafka-source --tls-client-key='projects/123/secrets/my-key/versions/1'
  """
  parser.add_argument(
      '--tls-client-key',
      type=str,
      required=required,
      help=help_text,
  )


def AddKafkaSourceNetworkAttachmentArg(parser, required=False):
  """Adds an argument for the Kafka sources's ingress network attachment."""
  parser.add_argument(
      '--network-attachment',
      required=required,
      help=(
          'The network attachment associated with the Kafka source that allows'
          ' access to the ingress VPC.'
      ),
  )


def AddLabelsArg(parser, help_text):
  """Adds arguments for resources' labels."""
  parser.add_argument(
      '--labels',
      help=help_text,
      type=arg_parsers.ArgDict(),
      metavar='KEY=VALUE',
  )
