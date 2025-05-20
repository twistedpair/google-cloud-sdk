# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Utilities for Eventarc MessageBuses API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.eventarc import base
from googlecloudsdk.api_lib.eventarc import common
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources

NO_NA_FOR_NON_HTTP_ENDPOINTS_WARNING = """\
Specifying a network attachment when creating a pipeline for an Eventarc message
bus, Pub/Sub topic, or Workflows destination is a pre-GA feature only. An error
will result when support for this is removed.
"""


class NoFieldsSpecifiedError(exceptions.Error):
  """Error when no fields were specified for a Patch operation."""


class InvalidDestinationsArgumentError(exceptions.Error):
  """Error when the pipeline's destinations argument is invalid."""


def GetPipelineURI(resource):
  pipelines = resources.REGISTRY.ParseRelativeName(
      resource.name, collection='eventarc.projects.locations.pipelines'
  )
  return pipelines.SelfLink()


class PipelineClientV1(base.EventarcClientBase):
  """Pipeline Client for interaction with v1 of Eventarc Pipelines API."""

  def __init__(self):
    super(PipelineClientV1, self).__init__(
        common.API_NAME, common.API_VERSION_1, 'pipeline'
    )

    # Eventarc Client
    client = apis.GetClientInstance(common.API_NAME, common.API_VERSION_1)

    self._messages = client.MESSAGES_MODULE
    self._service = client.projects_locations_pipelines

  def Create(self, pipeline_ref, pipeline_message, dry_run=False):
    """Creates a Pipeline.

    Args:
      pipeline_ref: Resource, the Pipeline to create.
      pipeline_message: Pipeline, the pipeline message that holds pipeline's
        name, destinations, mediations, input payload format, logging config,
        retry policy, crypto key name, etc.
      dry_run: If set, the changes will not be committed, only validated

    Returns:
      A long-running operation for create.
    """
    create_req = self._messages.EventarcProjectsLocationsPipelinesCreateRequest(
        parent=pipeline_ref.Parent().RelativeName(),
        pipeline=pipeline_message,
        pipelineId=pipeline_ref.Name(),
        validateOnly=dry_run,
    )
    return self._service.Create(create_req)

  def List(self, location_ref, limit, page_size):
    """List available pipelines in location.

    Args:
      location_ref: Resource, the location to list Pipelines in.
      limit: int or None, the total number of results to return.
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results).

    Returns:
      A generator of Pipelines in the location.
    """
    list_req = self._messages.EventarcProjectsLocationsPipelinesListRequest(
        parent=location_ref.RelativeName(), pageSize=page_size
    )
    return list_pager.YieldFromList(
        service=self._service,
        request=list_req,
        field='pipelines',
        limit=limit,
        batch_size=page_size,
        batch_size_attribute='pageSize',
    )

  def Get(self, pipeline_ref):
    """Gets the requested Pipeline.

    Args:
      pipeline_ref: Resource, the Pipeline to get.

    Returns:
      The Pipeline message.
    """
    get_req = self._messages.EventarcProjectsLocationsPipelinesGetRequest(
        name=pipeline_ref.RelativeName()
    )
    return self._service.Get(get_req)

  def Patch(self, pipeline_ref, pipeline_message, update_mask):
    """Updates the specified Pipeline.

    Args:
      pipeline_ref: Resource, the Pipeline to update.
      pipeline_message: Pipeline, the pipeline message that holds pipeline's
        name, destinations, mediations, input payload format, logging config,
        retry policy, crypto key name, etc.
      update_mask: str, a comma-separated list of Pipeline fields to update.

    Returns:
      A long-running operation for update.
    """
    patch_req = self._messages.EventarcProjectsLocationsPipelinesPatchRequest(
        name=pipeline_ref.RelativeName(),
        pipeline=pipeline_message,
        updateMask=update_mask,
    )
    return self._service.Patch(patch_req)

  def Delete(self, pipeline_ref):
    """Deletes the specified Pipeline.

    Args:
      pipeline_ref: Resource, the Pipeline to delete.

    Returns:
      A long-running operation for delete.
    """
    delete_req = self._messages.EventarcProjectsLocationsPipelinesDeleteRequest(
        name=pipeline_ref.RelativeName()
    )
    return self._service.Delete(delete_req)

  def BuildPipeline(
      self,
      pipeline_ref,
      destinations,
      input_payload_format_json,
      input_payload_format_avro_schema_definition,
      input_payload_format_protobuf_schema_definition,
      mediations,
      logging_config,
      max_retry_attempts,
      min_retry_delay,
      max_retry_delay,
      crypto_key_name,
      labels,
  ):
    return self._messages.Pipeline(
        name=pipeline_ref.RelativeName(),
        destinations=self._BuildDestinations(pipeline_ref, destinations),
        inputPayloadFormat=self._BuildInputPayloadFormat(
            input_payload_format_json,
            input_payload_format_avro_schema_definition,
            input_payload_format_protobuf_schema_definition,
        ),
        mediations=self._BuildMediations(mediations),
        loggingConfig=self._BuildLoggingConfig(logging_config),
        retryPolicy=self._BuildRetryPolicy(
            max_retry_attempts, min_retry_delay, max_retry_delay
        ),
        cryptoKeyName=crypto_key_name,
        labels=labels,
    )

  def BuildUpdateMask(
      self,
      destinations,
      input_payload_format_json,
      input_payload_format_avro_schema_definition,
      input_payload_format_protobuf_schema_definition,
      mediations,
      logging_config,
      max_retry_attempts,
      min_retry_delay,
      max_retry_delay,
      crypto_key,
      clear_crypto_key,
      labels,
  ):
    """Builds an update mask for updating a pipeline.

    Args:
      destinations: bool, whether to update the destinations.
      input_payload_format_json: bool, whether to update the
        input_payload_format_json.
      input_payload_format_avro_schema_definition: bool, whether to update the
        input_payload_format_avro_schema_definition.
      input_payload_format_protobuf_schema_definition: bool, whether to update
        the input_payload_format_protobuf_schema_definition.
      mediations: bool, whether to update the mediations.
      logging_config: bool, whether to update the logging_config.
      max_retry_attempts: bool, whether to update the max_retry_attempts.
      min_retry_delay: bool, whether to update the min_retry_delay.
      max_retry_delay: bool, whether to update the max_retry_delay.
      crypto_key: bool, whether to update the crypto_key.
      clear_crypto_key: bool, whether to clear the crypto_key.
      labels: bool, whether to update the labels.

    Returns:
      The update mask as a string.


    Raises:
      NoFieldsSpecifiedError: No fields are being updated.
    """
    update_mask = []
    if destinations:
      update_mask.append('destinations')
    if (
        input_payload_format_json
        or input_payload_format_avro_schema_definition
        or input_payload_format_protobuf_schema_definition
    ):
      update_mask.append('inputPayloadFormat')
    if mediations:
      update_mask.append('mediations')
    if logging_config:
      update_mask.append('loggingConfig')
    if (
        max_retry_attempts
        or max_retry_attempts
        or min_retry_delay
        or max_retry_delay
    ):
      update_mask.append('retryPolicy')
    if crypto_key or clear_crypto_key:
      update_mask.append('cryptoKeyName')
    if labels:
      update_mask.append('labels')

    if not update_mask:
      raise NoFieldsSpecifiedError('Must specify at least one field to update.')
    return ','.join(update_mask)

  def LabelsValueClass(self):
    return self._messages.Pipeline.LabelsValue

  def _BuildDestinations(self, pipeline_ref, destinations):
    if destinations is None:
      return []
    return [self._BuildDestination(pipeline_ref, d) for d in destinations]

  def _BuildDestination(self, pipeline_ref, destination):
    http_endpoint = self._BuildDestinationHttpEndpoint(destination)
    workflow = self._BuildDestinationWorkflow(pipeline_ref, destination)
    message_bus = self._BuildDestinationMessageBus(pipeline_ref, destination)
    pubsub_topic = self._BuildDestinationPubsubTopic(pipeline_ref, destination)
    if (http_endpoint is not None) + (workflow is not None) + (
        message_bus is not None
    ) + (pubsub_topic is not None) != 1:
      raise InvalidDestinationsArgumentError(
          'Exactly one of http_endpoint_uri, workflow, message_bus, or'
          ' pubsub_topic must be set'
      )
    if destination.get(
        'http_endpoint_message_binding_template'
    ) is not None and (workflow or message_bus or pubsub_topic):
      raise InvalidDestinationsArgumentError(
          'http_endpoint_message_binding_template cannot be set when workflow,'
          ' message_bus, or pubsub_topic is set'
      )
    if destination.get('http_endpoint_uri') and destination.get('project'):
      raise InvalidDestinationsArgumentError(
          'project cannot be set when http_endpoint_uri is set'
      )
    if destination.get('http_endpoint_uri') and destination.get('location'):
      raise InvalidDestinationsArgumentError(
          'location cannot be set when http_endpoint_uri is set'
      )
    return self._messages.GoogleCloudEventarcV1PipelineDestination(
        httpEndpoint=http_endpoint,
        workflow=workflow,
        messageBus=message_bus,
        topic=pubsub_topic,
        networkConfig=self._BuildDestinationNetworkConfig(
            pipeline_ref, destination
        ),
        authenticationConfig=self._BuildDestinationAuthenticationConfig(
            destination
        ),
        outputPayloadFormat=self._BuildDestinationOutputPayloadFormat(
            destination
        ),
    )

  def _BuildDestinationHttpEndpoint(self, destination):
    if destination.get('http_endpoint_uri') is None:
      return None
    return self._messages.GoogleCloudEventarcV1PipelineDestinationHttpEndpoint(
        uri=destination.get('http_endpoint_uri'),
        messageBindingTemplate=destination.get(
            'http_endpoint_message_binding_template'
        ),
    )

  def _BuildDestinationWorkflow(self, pipeline_ref, destination):
    if destination.get('workflow') is None:
      return None
    project = destination.get('project') or pipeline_ref.projectsId
    location = destination.get('location') or pipeline_ref.locationsId
    return f'projects/{project}/locations/{location}/workflows/{destination.get("workflow")}'

  def _BuildDestinationMessageBus(self, pipeline_ref, destination):
    if destination.get('message_bus') is None:
      return None
    project = destination.get('project') or pipeline_ref.projectsId
    location = destination.get('location') or pipeline_ref.locationsId
    return f'projects/{project}/locations/{location}/messageBuses/{destination.get("message_bus")}'

  def _BuildDestinationPubsubTopic(self, pipeline_ref, destination):
    if destination.get('pubsub_topic') is None:
      return None
    project = destination.get('project') or pipeline_ref.projectsId
    return f'projects/{project}/topics/{destination.get("pubsub_topic")}'

  def _BuildDestinationNetworkConfig(self, pipeline_ref, destination):
    if destination.get('http_endpoint_uri') is not None:
      if destination.get('network_attachment') is None:
        raise InvalidDestinationsArgumentError('network_attachment must be set')

      return self._messages.GoogleCloudEventarcV1PipelineDestinationNetworkConfig(
          networkAttachment=f'projects/{pipeline_ref.projectsId}/regions/{pipeline_ref.locationsId}/networkAttachments/{destination.get("network_attachment")}',
      )

    # Workflows, Pub/Sub topic and Message Bus destinations do not require a
    # network attachment.
    if destination.get('network_attachment') is None:
      return None

    # TODO(b/410045292): Remove once network attachments are not supported.
    # Network attachments are optional for non-HTTP destinations
    log.warning(NO_NA_FOR_NON_HTTP_ENDPOINTS_WARNING)
    return self._messages.GoogleCloudEventarcV1PipelineDestinationNetworkConfig(
        networkAttachment=f'projects/{pipeline_ref.projectsId}/regions/{pipeline_ref.locationsId}/networkAttachments/{destination.get("network_attachment")}',
    )

  def _BuildDestinationAuthenticationConfig(self, destination):
    google_oidc = self._BuildDestinationAuthenticationGoogleOidc(destination)
    oauth_token = self._BuildDestinationAuthenticationOauthToken(destination)
    if (google_oidc is not None) + (oauth_token is not None) > 1:
      raise InvalidDestinationsArgumentError(
          'At most one of google_oidc_authentication_service_account or'
          ' oauth_token_authentication_service_account can be set'
      )
    if destination.get('oauth_token_authentication_scope'):
      if google_oidc:
        raise InvalidDestinationsArgumentError(
            'oauth_token_authentication_scope cannot be set when'
            ' google_oidc_authentication_service_account is set'
        )
      if oauth_token is None:
        raise InvalidDestinationsArgumentError(
            'oauth_token_authentication_scope cannot be set when'
            ' oauth_token_authentication_service_account is not set'
        )
    if destination.get('google_oidc_authentication_audience'):
      if oauth_token:
        raise InvalidDestinationsArgumentError(
            'google_oidc_authentication_audience cannot be set when'
            ' oauth_token_authentication_service_account is set'
        )
      if google_oidc is None:
        raise InvalidDestinationsArgumentError(
            'google_oidc_authentication_audience cannot be set when'
            ' google_oidc_authentication_service_account is not set'
        )
    if google_oidc is None and oauth_token is None:
      return None
    return self._messages.GoogleCloudEventarcV1PipelineDestinationAuthenticationConfig(
        googleOidc=google_oidc,
        oauthToken=oauth_token,
    )

  def _BuildDestinationAuthenticationGoogleOidc(self, destination):
    if destination.get('google_oidc_authentication_service_account') is None:
      return None
    return self._messages.GoogleCloudEventarcV1PipelineDestinationAuthenticationConfigOidcToken(
        serviceAccount=destination.get(
            'google_oidc_authentication_service_account'
        ),
        audience=destination.get('google_oidc_authentication_audience'),
    )

  def _BuildDestinationAuthenticationOauthToken(self, destination):
    if destination.get('oauth_token_authentication_service_account') is None:
      return None
    return self._messages.GoogleCloudEventarcV1PipelineDestinationAuthenticationConfigOAuthToken(
        serviceAccount=destination.get(
            'oauth_token_authentication_service_account'
        ),
        scope=destination.get('oauth_token_authentication_scope'),
    )

  def _BuildDestinationOutputPayloadFormat(self, destination):
    json = self._BuildDestinationOutputPayloadFormatJsonFormat(destination)
    avro = self._BuildDestinationOutputPayloadFormatAvroFormat(destination)
    protobuf = self._BuildDestinationOutputPayloadFormatProtobufFormat(
        destination
    )
    if (json is not None) + (avro is not None) + (protobuf is not None) > 1:
      raise InvalidDestinationsArgumentError(
          'At most one of output_payload_format_json,'
          ' output_payload_format_avro_schema_definition, or'
          ' output_payload_format_protobuf_schema_definition can be set'
      )
    if json is None and avro is None and protobuf is None:
      return None
    return self._messages.GoogleCloudEventarcV1PipelineMessagePayloadFormat(
        json=json,
        avro=avro,
        protobuf=protobuf,
    )

  def _BuildDestinationOutputPayloadFormatAvroFormat(self, destination):
    if destination.get('output_payload_format_avro_schema_definition') is None:
      return None
    return self._messages.GoogleCloudEventarcV1PipelineMessagePayloadFormatAvroFormat(
        schemaDefinition=destination.get(
            'output_payload_format_avro_schema_definition'
        )
    )

  def _BuildDestinationOutputPayloadFormatProtobufFormat(self, destination):
    if (
        destination.get('output_payload_format_protobuf_schema_definition')
        is None
    ):
      return None
    return self._messages.GoogleCloudEventarcV1PipelineMessagePayloadFormatProtobufFormat(
        schemaDefinition=destination.get(
            'output_payload_format_protobuf_schema_definition'
        )
    )

  def _BuildDestinationOutputPayloadFormatJsonFormat(self, destination):
    if 'output_payload_format_json' not in destination:
      return None
    return (
        self._messages.GoogleCloudEventarcV1PipelineMessagePayloadFormatJsonFormat()
    )

  def _BuildInputPayloadFormat(
      self, json, avro_schema_definition, protobuf_schema_definition
  ):
    if (
        json is None
        and avro_schema_definition is None
        and protobuf_schema_definition is None
    ):
      return None
    return self._messages.GoogleCloudEventarcV1PipelineMessagePayloadFormat(
        json=self._BuildInputPayloadFormatJsonFormat(json),
        avro=self._BuildInputPayloadFormatAvroFormat(avro_schema_definition),
        protobuf=self._BuildInputPayloadFormatProtobufFormat(
            protobuf_schema_definition
        ),
    )

  def _BuildInputPayloadFormatAvroFormat(self, schema_definition):
    if schema_definition is None:
      return None
    return self._messages.GoogleCloudEventarcV1PipelineMessagePayloadFormatAvroFormat(
        schemaDefinition=schema_definition
    )

  def _BuildInputPayloadFormatProtobufFormat(self, schema_definition):
    if schema_definition is None:
      return None
    return self._messages.GoogleCloudEventarcV1PipelineMessagePayloadFormatProtobufFormat(
        schemaDefinition=schema_definition
    )

  def _BuildInputPayloadFormatJsonFormat(self, json):
    if json is None:
      return None
    return (
        self._messages.GoogleCloudEventarcV1PipelineMessagePayloadFormatJsonFormat()
    )

  def _BuildMediations(self, mediations):
    if mediations is None:
      return []
    return [
        self._messages.GoogleCloudEventarcV1PipelineMediation(
            transformation=self._messages.GoogleCloudEventarcV1PipelineMediationTransformation(
                transformationTemplate=m.get('transformation_template'),
            ),
        )
        for m in mediations
    ]

  def _BuildLoggingConfig(self, logging_config):
    if logging_config is None:
      return None
    return self._messages.LoggingConfig(
        logSeverity=self._messages.LoggingConfig.LogSeverityValueValuesEnum(
            logging_config
        ),
    )

  def _BuildRetryPolicy(
      self, max_retry_attempts, min_retry_delay, max_retry_delay
  ):
    if (
        max_retry_attempts is None
        and min_retry_delay is None
        and max_retry_delay is None
    ):
      return None
    return self._messages.GoogleCloudEventarcV1PipelineRetryPolicy(
        maxAttempts=max_retry_attempts,
        minRetryDelay=min_retry_delay,
        maxRetryDelay=max_retry_delay,
    )
