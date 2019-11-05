# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Allows you to write surfaces in terms of logical Eventflow operations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import contextlib
import functools
import random

from apitools.base.py import exceptions as api_exceptions
from googlecloudsdk.api_lib.events import custom_resource_definition
from googlecloudsdk.api_lib.events import metric_names
from googlecloudsdk.api_lib.events import source
from googlecloudsdk.api_lib.events import trigger
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import apis_internal
from googlecloudsdk.command_lib.events import exceptions
from googlecloudsdk.command_lib.events import stages
from googlecloudsdk.command_lib.events import util
from googlecloudsdk.command_lib.run import serverless_operations
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.apis import registry
from googlecloudsdk.core import metrics


_EVENT_SOURCES_LABEL_SELECTOR = 'duck.knative.dev/source=true'

_CRD_CLIENT_VERSION = 'v1beta1'


@contextlib.contextmanager
def Connect(conn_context):
  """Provide a EventflowOperations instance to use.

  If we're using the GKE Serverless Add-on, connect to the relevant cluster.
  Otherwise, connect to the right region of GSE.

  Arguments:
    conn_context: a context manager that yields a ConnectionInfo and manages a
      dynamic context that makes connecting to serverless possible.

  Yields:
    A EventflowOperations instance.
  """

  # The One Platform client is required for making requests against
  # endpoints that do not supported Kubernetes-style resource naming
  # conventions. The One Platform client must be initialized outside of a
  # connection context so that it does not pick up the api_endpoint_overrides
  # values from the connection context.
  op_client = apis.GetClientInstance(
      conn_context.api_name,
      conn_context.api_version)

  with conn_context as conn_info:
    # pylint: disable=protected-access
    client = apis_internal._GetClientInstance(
        conn_info.api_name,
        conn_info.api_version,
        # Only check response if not connecting to GKE
        check_response_func=apis.CheckResponseForApiEnablement()
        if conn_context.supports_one_platform else None,
        http_client=conn_context.HttpClient())
    # This client is only used to get CRDs because the api group they are
    # under uses different versioning in k8s
    crd_client = apis_internal._GetClientInstance(
        conn_context.api_name,
        _CRD_CLIENT_VERSION,
        http_client=conn_context.HttpClient())
    # pylint: enable=protected-access
    yield EventflowOperations(
        client,
        conn_info.region,
        crd_client,
        op_client)


# TODO(b/141626230): Remove this and use regular ConditionPoller
class UnfailingConditionPoller(serverless_operations.ConditionPoller):
  """Condition poller that never fails and is only done on success.

  Knative Eventing does not use the Ready == False condition to indicate
  failure. Instead, only Ready == True can be relied upon as a terminal state
  and all other statuses (False, Unknown) simply mean not currently successful,
  but provide no indication if this is a temporary or permanent state.

  This condition poller never fails a stage for that reason, and therefore
  never done until successful.
  """

  def IsDone(self, conditions):
    """Overrides.

    Args:
      conditions: A condition.Conditions object.

    Returns:
      A bool indicating whether `conditions` is ready.
    """
    if conditions is None:
      return False
    return conditions.IsReady()

  def Poll(self, unused_ref):
    """Overrides.

    Args:
      unused_ref: A string representing the operation reference. Unused and may
        be None.

    Returns:
      A condition.Conditions object or None if there's no conditions on the
        resource or if the conditions are not fresh (the generation on the
        resource doesn't match the observedGeneration)
    """
    conditions = self.GetConditions()

    if conditions is None or not conditions.IsFresh():
      return None

    conditions_message = conditions.DescriptiveMessage()
    if conditions_message:
      self._tracker.UpdateHeaderMessage(conditions_message)

    self._PollTerminalSubconditions(conditions, conditions_message)

    if conditions.IsReady():
      self._tracker.UpdateHeaderMessage(self._ready_message)
      # TODO(b/120679874): Should not have to manually call Tick()
      self._tracker.Tick()

    return conditions

  def _PossiblyFailStage(self, condition, message):
    """Stages are never marked as failed."""


class EventflowOperations(object):
  """Client used by Eventflow to communicate with the actual API."""

  def __init__(self, client, region, crd_client, op_client):
    """Inits EventflowOperations with given API clients.

    Args:
      client: The API client for interacting with Kubernetes Cloud Run APIs.
      region: str, The region of the control plane if operating against
        hosted Cloud Run, else None.
      crd_client: The API client for querying for CRDs. Or None if interacting
        with managed Cloud Run.
      op_client: The API client for interacting with One Platform APIs. Or
        None if interacting with Cloud Run on GKE.
    """
    self._client = client
    self._crd_client = crd_client
    self._op_client = op_client
    self._region = region

  @property
  def client(self):
    return self._client

  @property
  def messages(self):
    return self._client.MESSAGES_MODULE

  def GetTrigger(self, trigger_ref):
    """Returns the referenced trigger."""
    request = self.messages.RunNamespacesTriggersGetRequest(
        name=trigger_ref.RelativeName())
    try:
      with metrics.RecordDuration(metric_names.GET_TRIGGER):
        response = self._client.namespaces_triggers.Get(request)
    except api_exceptions.HttpNotFoundError:
      return None
    return trigger.Trigger(response, self.messages)

  def CreateTrigger(self, trigger_ref, source_obj, event_type, target_service,
                    broker):
    """Create a trigger that sends events to the target service.

    Args:
      trigger_ref: googlecloudsdk.core.resources.Resource, trigger resource.
      source_obj: source.Source. The source object to be created after the
        trigger.
      event_type: custom_resource_definition.EventTypeDefinition, the event
        type the source will filter by.
      target_service: str, name of the Cloud Run service to subscribe.
      broker: str, name of the broker to act as a sink for the source.

    Returns:
      trigger.Trigger of the created trigger.
    """
    trigger_obj = trigger.Trigger.New(self._client, trigger_ref.Parent().Name())
    trigger_obj.name = trigger_ref.Name()
    trigger_obj.dependency = source_obj
    # TODO(b/141617597): Set to str(random.random()) without prepended string
    trigger_obj.filter_attributes[
        trigger.SOURCE_TRIGGER_LINK_FIELD] = 'link{}'.format(random.random())
    trigger_obj.filter_attributes[
        trigger.EVENT_TYPE_FIELD] = event_type.type
    trigger_obj.subscriber = target_service
    trigger_obj.broker = broker

    request = self.messages.RunNamespacesTriggersCreateRequest(
        trigger=trigger_obj.Message(),
        parent=trigger_ref.Parent().RelativeName())
    with metrics.RecordDuration(metric_names.CREATE_TRIGGER):
      try:
        response = self._client.namespaces_triggers.Create(request)
      except api_exceptions.HttpConflictError:
        raise exceptions.TriggerCreationError(
            'Trigger [{}] already exists.'.format(trigger_obj.name))

    return trigger.Trigger(response, self.messages)

  def ListTriggers(self, namespace_ref):
    """Returns a list of existing triggers in the given namespace."""
    request = self.messages.RunNamespacesTriggersListRequest(
        parent=namespace_ref.RelativeName())
    with metrics.RecordDuration(metric_names.LIST_TRIGGERS):
      response = self._client.namespaces_triggers.List(request)
    return [trigger.Trigger(item, self.messages) for item in response.items]

  def DeleteTrigger(self, trigger_ref):
    """Deletes the referenced trigger."""
    request = self.messages.RunNamespacesTriggersDeleteRequest(
        name=trigger_ref.RelativeName())
    try:
      with metrics.RecordDuration(metric_names.DELETE_TRIGGER):
        self._client.namespaces_triggers.Delete(request)
    except api_exceptions.HttpNotFoundError:
      raise exceptions.TriggerNotFound(
          'Trigger [{}] not found.'.format(trigger_ref.Name()))

  def _FindSourceMethod(self, source_crd, method_name):
    """Returns the given method for the given source kind.

    Because every source has its own methods for rpc requests, this helper is
    used to get the underlying methods for a request against a given source
    type. Preferred usage of this private message is via the public
    methods: self.Source{Method_name}Method.

    Args:
      source_crd: custom_resource_definition.SourceCustomResourceDefinition,
        source CRD of the type we want to make a request against.
      method_name: str, the method name (e.g. "get", "create", "list", etc.)

    Returns:
      registry.APIMethod, holds information for the requested method.
    """
    return registry.GetMethod(
        util.SOURCE_COLLECTION_NAME.format(
            plural_kind=source_crd.source_kind_plural), method_name)

  def SourceCreateMethod(self, source_crd):
    """Returns the request method for a Create request of this source."""
    return self._FindSourceMethod(source_crd, 'create')

  def SourceGetMethod(self, source_crd):
    """Returns the request method for a Get request of this source."""
    return self._FindSourceMethod(source_crd, 'get')

  def GetSource(self, source_ref, source_crd):
    """Returns the referenced source."""
    request_method = self.SourceGetMethod(source_crd)
    request_message_type = request_method.GetRequestType()
    request = request_message_type(name=source_ref.RelativeName())
    try:
      response = request_method.Call(request, client=self._client)
    except api_exceptions.HttpNotFoundError:
      return None
    return source.Source(response, self.messages, source_crd.source_kind)

  def CreateSource(self, source_obj, source_crd, owner_trigger, namespace_ref,
                   broker, parameters):
    """Create an source with the specified event type and owner trigger.

    Args:
      source_obj: source.Source. The source object being created.
      source_crd: custom_resource_definition.SourceCRD, the source crd for the
        source to create
      owner_trigger: trigger.Trigger, trigger to associate as an owner of the
        source.
      namespace_ref: googlecloudsdk.core.resources.Resource, namespace resource.
      broker: str, name of the broker to act as a sink.
      parameters: dict, additional parameters to set on the source spec.

    Returns:
      source.Source of the created source.
    """
    source_obj.ce_overrides[trigger.SOURCE_TRIGGER_LINK_FIELD] = (
        owner_trigger.filter_attributes[trigger.SOURCE_TRIGGER_LINK_FIELD])
    source_obj.owners.append(
        self.messages.OwnerReference(
            apiVersion=owner_trigger.apiVersion,
            kind=owner_trigger.kind,
            name=owner_trigger.name,
            uid=owner_trigger.uid,
            controller=True))
    source_obj.sink = broker
    arg_utils.ParseStaticFieldsIntoMessage(source_obj.spec, parameters)

    request_method = self.SourceCreateMethod(source_crd)
    request_message_type = request_method.GetRequestType()
    request = request_message_type(**{
        request_method.request_field: source_obj.Message(),
        'parent': namespace_ref.RelativeName()})
    with metrics.RecordDuration(metric_names.CREATE_SOURCE):
      try:
        response = request_method.Call(request, client=self._client)
      except api_exceptions.HttpConflictError:
        raise exceptions.SourceCreationError(
            'Source [{}] already exists.'.format(source_obj.name))

    return source.Source(response, self.messages, source_crd.source_kind)

  def CreateTriggerAndSource(self, trigger_obj, trigger_ref, namespace_ref,
                             source_obj, event_type, parameters, broker,
                             target_service, tracker):
    """Create a linked trigger and source pair.

    Trigger and source are linked via a dependency annotation on the trigger
    as well as the opaque knsourcetrigger field in the trigger filter and the
    source override.

    If the passed trigger_obj is not None, then a new trigger is not created,
    only a source.

    Args:
      trigger_obj: trigger.Trigger, the existing trigger or None if no trigger
        already exists.
      trigger_ref: googlecloudsdk.core.resources.Resource, trigger resource.
      namespace_ref: googlecloudsdk.core.resources.Resource, namespace resource.
      source_obj: source.Source. The source object being created.
      event_type: custom_resource_definition.EventTypeDefinition, the event
        type the source will filter by.
      parameters: dict, additional parameters to set on the source spec.
      broker: str, name of the broker to act as a sink for the source.
      target_service: str, name of the Cloud Run service to subscribe to the
        trigger.
      tracker: progress_tracker.StagedProgressTracker to update as the trigger
        is created and becomes ready.
    """
    # Create trigger if it doesn't already exist
    if trigger_obj is None:
      trigger_obj = self.CreateTrigger(trigger_ref, source_obj, event_type,
                                       target_service, broker)

    # Create source
    self.CreateSource(source_obj, event_type.crd, trigger_obj, namespace_ref,
                      broker, parameters)

    # Wait for source to be Ready == True
    source_ref = util.GetSourceRef(
        source_obj.name, source_obj.namespace, event_type.crd)
    source_getter = functools.partial(
        self.GetSource, source_ref, event_type.crd)
    poller = UnfailingConditionPoller(source_getter, tracker,
                                      stages.TriggerSourceDependencies())
    util.WaitForCondition(poller, exceptions.SourceCreationError)
    # Manually complete the stage indicating source readiness because we can't
    # track a terminal (Ready) condition in the ConditionPoller.
    tracker.CompleteStage(stages.SOURCE_READY)

    # Wait for trigger to be Ready == True
    trigger_getter = functools.partial(self.GetTrigger, trigger_ref)
    poller = UnfailingConditionPoller(trigger_getter, tracker,
                                      stages.TriggerSourceDependencies())
    util.WaitForCondition(poller, exceptions.TriggerCreationError)

  def ListSourceCustomResourceDefinitions(self):
    """Returns a list of CRDs for event sources."""
    messages = self._crd_client.MESSAGES_MODULE
    request = messages.RunCustomresourcedefinitionsListRequest(
        labelSelector=_EVENT_SOURCES_LABEL_SELECTOR)
    with metrics.RecordDuration(metric_names.LIST_SOURCE_CRDS):
      response = self._crd_client.customresourcedefinitions.List(request)
    source_crds = [
        custom_resource_definition.SourceCustomResourceDefinition(
            item, messages) for item in response.items
    ]
    # Only include CRDs for source kinds that are defined in the api.
    return [s for s in source_crds if hasattr(self.messages, s.source_kind)]
