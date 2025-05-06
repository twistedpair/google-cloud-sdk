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
"""Utilities for Eventarc KafkaSources API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import uuid

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.eventarc import base
from googlecloudsdk.api_lib.eventarc import common
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import resources


class NoFieldsSpecifiedError(exceptions.Error):
  """Error when no fields were specified for a Patch operation."""


class InvalidNetworkConfigArgumentError(exceptions.Error):
  """Error when the Kafka Source's network configuration arguments are invalid."""


class InvalidDestinationArgumentError(exceptions.Error):
  """Error when the Kafka Source's destination argument is invalid."""


class InvalidAuthenticationMethodArgumentError(exceptions.Error):
  """Error when the Kafka Source's authentication arguments are invalid."""


class InvalidBrokerUrisArgumentError(exceptions.Error):
  """Error when the Kafka Source's bootstrap_servers argument is invalid."""


class InvalidTopicsArgumentError(exceptions.Error):
  """Error when the Kafka Source's topics argument is invalid."""


class InvalidInitialOffsetArgumentError(exceptions.Error):
  """Error when the Kafka Source's initial offset argument is invalid."""


def GetKafkaSourceURI(resource):
  kafka_sources = resources.REGISTRY.ParseRelativeName(
      resource.name, collection='eventarc.projects.locations.kafkaSources'
  )
  return kafka_sources.SelfLink()


class KafkaSourceClientV1(base.EventarcClientBase):
  """Kafka Source Client for interaction with v1 of Eventarc Kafka Sources API."""

  def __init__(self):
    super(KafkaSourceClientV1, self).__init__(
        common.API_NAME, common.API_VERSION_1, 'kafkaSource'
    )

    # Eventarc Client
    client = apis.GetClientInstance(common.API_NAME, common.API_VERSION_1)

    self._messages = client.MESSAGES_MODULE
    self._service = client.projects_locations_kafkaSources

  def Create(self, kafka_source_ref, kafka_source_message, dry_run=False):
    """Creates a Kafka Source.

    Args:
      kafka_source_ref: Resource, the Kafka Source to create.
      kafka_source_message: Kafka Source, the Kafka Source message that holds
        Kafka source's name, destinations, mediations, input payload format,
        logging config, retry policy, crypto key name, etc.
      dry_run: If set, the changes will not be committed, only validated

    Returns:
      A long-running operation for create.
    """
    create_req = (
        self._messages.EventarcProjectsLocationsKafkaSourcesCreateRequest(
            parent=kafka_source_ref.Parent().RelativeName(),
            kafkaSource=kafka_source_message,
            kafkaSourceId=kafka_source_ref.Name(),
            validateOnly=dry_run,
        )
    )
    return self._service.Create(create_req)

  def List(self, location_ref, limit, page_size):
    """List available Kafka Sources in location.

    Args:
      location_ref: Resource, the location to list Kafka Sources in.
      limit: int or None, the total number of results to return.
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results).

    Returns:
      A generator of Kafka Sources in the location.
    """
    list_req = self._messages.EventarcProjectsLocationsKafkaSourcesListRequest(
        parent=location_ref.RelativeName(), pageSize=page_size
    )
    return list_pager.YieldFromList(
        service=self._service,
        request=list_req,
        field='kafkaSources',
        limit=limit,
        batch_size=page_size,
        batch_size_attribute='pageSize',
    )

  def Get(self, kafka_source_ref):
    """Gets the requested Kafka Source.

    Args:
      kafka_source_ref: Resource, the Kafka Source to get.

    Returns:
      The Kafka Source message.
    """
    get_req = self._messages.EventarcProjectsLocationsKafkaSourcesGetRequest(
        name=kafka_source_ref.RelativeName()
    )
    return self._service.Get(get_req)

  def Patch(self, kafka_source_ref, kafka_source_message, update_mask):
    """Updates the specified Kafka Source.

    Args:
      kafka_source_ref: Resource, the Kafka Source to update.
      kafka_source_message: Kafka Source, the Kafka Source message that holds
        Kafka Source's name, destinations, mediations, input payload format,
        logging config, retry policy, crypto key name, etc.
      update_mask: str, a comma-separated list of Kafka Source fields to update.

    Returns:
      A long-running operation for update.
    """
    patch_req = (
        self._messages.EventarcProjectsLocationsKafkaSourcesPatchRequest(
            name=kafka_source_ref.RelativeName(),
            kafka_source=kafka_source_message,
            updateMask=update_mask,
        )
    )
    return self._service.Patch(patch_req)

  def Delete(self, kafka_source_ref):
    """Deletes the specified Kafka Source.

    Args:
      kafka_source_ref: Resource, the Kafka Source to delete.

    Returns:
      A long-running operation for delete.
    """
    delete_req = (
        self._messages.EventarcProjectsLocationsKafkaSourcesDeleteRequest(
            name=kafka_source_ref.RelativeName()
        )
    )
    return self._service.Delete(delete_req)

  def BuildKafkaSource(
      self,
      kafka_source_ref,
      bootstrap_servers,
      consumer_group_id,
      topics,
      sasl_mechanism,
      sasl_username,
      sasl_password,
      tls_client_certificate,
      tls_client_key,
      network_attachment,
      message_bus,
      initial_offset,
      logging_config,
      labels,
  ):
    return self._messages.KafkaSource(
        name=kafka_source_ref.RelativeName(),
        brokerUris=self._BuildBrokerUris(bootstrap_servers),
        consumerGroupId=self._BuildConsumerGroupID(consumer_group_id),
        topics=self._BuildTopics(topics),
        authenticationConfig=self._BuildAuthenticationConfig(
            sasl_mechanism,
            sasl_username,
            sasl_password,
            tls_client_certificate,
            tls_client_key,
        ),
        networkConfig=self._BuildNetworkConfig(
            kafka_source_ref, network_attachment
        ),
        destination=self._BuildDestination(kafka_source_ref, message_bus),
        initialOffset=self._BuildInitialOffset(initial_offset),
        loggingConfig=self._BuildLoggingConfig(logging_config),
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
    """Builds an update mask for updating a Kafka Source.

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
    return self._messages.KafkaSource.LabelsValue

  def _BuildBrokerUris(self, bootstrap_servers):
    if bootstrap_servers is None:
      raise InvalidBrokerUrisArgumentError(
          'Must specify at least one bootstrap server.'
      )
    return list(bootstrap_servers)

  def _BuildTopics(self, topics):
    if topics is None:
      raise InvalidTopicsArgumentError('Must specify at least one topic.')
    return list(topics)

  def _BuildDestination(self, kafka_source_ref, message_bus):
    if message_bus is None:
      raise InvalidDestinationArgumentError('message_bus must be set')
    return f'projects/{kafka_source_ref.projectsId}/locations/{kafka_source_ref.locationsId}/messageBuses/{message_bus}'

  def _BuildNetworkConfig(self, kafka_source_ref, network_attachment):
    if network_attachment is None:
      raise InvalidNetworkConfigArgumentError('network_attachment must be set')
    return self._messages.NetworkConfig(
        networkAttachment=f'projects/{kafka_source_ref.projectsId}/regions/{kafka_source_ref.locationsId}/networkAttachments/{network_attachment}',
    )

  def _BuildConsumerGroupID(self, consumer_group_id):
    if consumer_group_id is None:
      return f'eventarc-{uuid.uuid4()}'
    return consumer_group_id

  def _BuildInitialOffset(self, initial_offset):
    if initial_offset is None:
      return 'newest'
    if initial_offset != 'newest' and initial_offset != 'oldest':
      raise InvalidInitialOffsetArgumentError(
          'initial_offset must be one of newest or oldest'
      )
    return initial_offset

  def _BuildAuthenticationConfig(
      self,
      sasl_mechanism,
      sasl_username,
      sasl_password,
      tls_client_certificate,
      tls_client_key,
  ):
    num_args_sasl = (
        (sasl_mechanism is not None)
        + (sasl_username is not None)
        + (sasl_password is not None)
    )
    num_args_mtls = (tls_client_certificate is not None) + (
        tls_client_key is not None
    )
    if num_args_sasl > 0 and num_args_mtls > 0:
      raise InvalidAuthenticationMethodArgumentError(
          'Exactly one of the following authentication methods must be set:\n'
          '  - SASL Authentication (--sasl-mechanism, --sasl-username,'
          ' --sasl-password)\n'
          '  - TLS Authentication (--tls-client-certificate,'
          ' --tls-client-key)'
      )
    if num_args_sasl > 0:
      if num_args_sasl != 3:
        raise InvalidAuthenticationMethodArgumentError(
            'When using SASL Authentication, all three arguments'
            ' sasl_mechanism, sasl_username, and sasl_password must be set'
        )
      return self._messages.AuthenticationConfig(
          saslAuth=self._messages.SaslAuthConfig(
              mechanism=self._ConvertSaslMechanismToEnum(sasl_mechanism),
              usernameSecret=sasl_username,
              passwordSecret=sasl_password,
          ),
          mutualTlsAuth=None,
      )
    if num_args_mtls > 0:
      if num_args_mtls != 2:
        raise InvalidAuthenticationMethodArgumentError(
            'When using TLS Authentication, both tls_client_certificate and'
            ' tls_client_key must be set'
        )
      return self._messages.AuthenticationConfig(
          saslAuth=None,
          mutualTlsAuth=self._messages.MutualTlsAuthConfig(
              secretManagerResources=self._messages.MutualTlsSecrets(
                  clientCertificate=tls_client_certificate,
                  clientKey=tls_client_key,
              )
          ),
      )
    raise InvalidAuthenticationMethodArgumentError(
        'Exactly one of the following authentication methods must be set:\n'
        '  - SASL Authentication (--sasl-mechanism, --sasl-username,'
        ' --sasl-password)\n'
        '  - TLS Authentication (--tls-client-certificate,'
        ' --tls-client-key)'
    )

  def _BuildLoggingConfig(self, logging_config):
    if logging_config is None:
      return None
    return self._messages.LoggingConfig(
        logSeverity=self._messages.LoggingConfig.LogSeverityValueValuesEnum(
            logging_config
        ),
    )

  def _ConvertSaslMechanismToEnum(self, mechanism):
    """Convert human-readable mechanism to enum."""
    if mechanism == 'PLAIN':
      return self._messages.SaslAuthConfig.MechanismValueValuesEnum('PLAIN')
    if mechanism == 'SCRAM-SHA-256':
      return self._messages.SaslAuthConfig.MechanismValueValuesEnum('SHA_256')
    if mechanism == 'SCRAM-SHA-512':
      return self._messages.SaslAuthConfig.MechanismValueValuesEnum('SHA_512')
    raise InvalidAuthenticationMethodArgumentError(
        'sasl_mechanism must be one of PLAIN, SCRAM_SHA_256, or'
        ' SCRAM_SHA_512'
    )
