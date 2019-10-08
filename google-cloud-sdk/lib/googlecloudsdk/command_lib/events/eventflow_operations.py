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

from apitools.base.py import exceptions as api_exceptions
from googlecloudsdk.api_lib.events import custom_resource_definition
from googlecloudsdk.api_lib.events import metric_names
from googlecloudsdk.api_lib.events import trigger
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import apis_internal
from googlecloudsdk.command_lib.events import exceptions
from googlecloudsdk.core import metrics


_EVENT_SOURCES_LABEL_SELECTOR = 'eventing.knative.dev/source=true'

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

  def ListSourceCustomResourceDefinitions(self):
    """Returns a list of CRDs for event sources."""
    messages = self._crd_client.MESSAGES_MODULE
    request = messages.RunCustomresourcedefinitionsListRequest(
        labelSelector=_EVENT_SOURCES_LABEL_SELECTOR)
    with metrics.RecordDuration(metric_names.LIST_SOURCE_CRDS):
      response = self._crd_client.customresourcedefinitions.List(request)
    return [
        custom_resource_definition.SourceCustomResourceDefinition(
            item, messages) for item in response.items
    ]
