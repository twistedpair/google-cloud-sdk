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

# pylint: disable=raise-missing-from
"""Allows you to write surfaces in terms of logical Serverless operations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import contextlib
import copy
import dataclasses
import functools
import json
import random
import string
from typing import List

from apitools.base.py import encoding
from apitools.base.py import exceptions as api_exceptions
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.run import condition as run_condition
from googlecloudsdk.api_lib.run import configuration
from googlecloudsdk.api_lib.run import domain_mapping
from googlecloudsdk.api_lib.run import execution
from googlecloudsdk.api_lib.run import global_methods
from googlecloudsdk.api_lib.run import job
from googlecloudsdk.api_lib.run import metric_names
from googlecloudsdk.api_lib.run import revision
from googlecloudsdk.api_lib.run import route
from googlecloudsdk.api_lib.run import service
from googlecloudsdk.api_lib.run import task
from googlecloudsdk.api_lib.run import worker_pool as worker_pool_lib
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import apis_internal
from googlecloudsdk.api_lib.util import exceptions as api_lib_exceptions
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.run import config_changes as config_changes_mod
from googlecloudsdk.command_lib.run import exceptions as serverless_exceptions
from googlecloudsdk.command_lib.run import messages_util
from googlecloudsdk.command_lib.run import name_generator
from googlecloudsdk.command_lib.run import op_pollers
from googlecloudsdk.command_lib.run import resource_name_conversion
from googlecloudsdk.command_lib.run import stages
from googlecloudsdk.command_lib.run.sourcedeploys import deployer
from googlecloudsdk.command_lib.run.sourcedeploys import sources
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.universe_descriptor import universe_descriptor
from googlecloudsdk.core.util import retry
import six


DEFAULT_ENDPOINT_VERSION = 'v1'

_NONCE_LENGTH = 10

ALLOW_UNAUTH_POLICY_BINDING_MEMBER = 'allUsers'
ALLOW_UNAUTH_POLICY_BINDING_ROLE = 'roles/run.invoker'

NEEDED_IAM_PERMISSIONS = ['run.services.setIamPolicy']

FAKE_IMAGE_DIGEST = (
    'sha256:fd2fdc0ac4a07f8d96ebe538566331e9da0f4bea069fb88de981cd8054b8cabc'
)


class UnknownAPIError(exceptions.Error):
  pass


@contextlib.contextmanager
def Connect(conn_context, already_activated_service=False):
  """Provide a ServerlessOperations instance to use.

  If we're using the GKE Serverless Add-on, connect to the relevant cluster.
  Otherwise, connect to the right region of GSE.

  Arguments:
    conn_context: a context manager that yields a ConnectionInfo and manages a
      dynamic context that makes connecting to serverless possible.
    already_activated_service: bool that should be true if we already checked if
      the run.googleapis.com service was enabled. If this is true, we skip
      prompting the user to enable the service because they should have already
      been prompted if the API wasn't activated.

  Yields:
    A ServerlessOperations instance.
  """

  # The One Platform client is required for making requests against
  # endpoints that do not supported Kubernetes-style resource naming
  # conventions. The One Platform client must be initialized outside of a
  # connection context so that it does not pick up the api_endpoint_overrides
  # values from the connection context.
  # pylint: disable=protected-access
  op_client = apis.GetClientInstance(
      conn_context.api_name,
      conn_context.api_version,
      skip_activation_prompt=already_activated_service,
  )
  # pylint: enable=protected-access

  with conn_context as conn_info:
    response_func = (
        apis.CheckResponse(already_activated_service)
        if conn_context.supports_one_platform
        else None
    )
    # pylint: disable=protected-access
    client = apis_internal._GetClientInstance(
        conn_info.api_name,
        conn_info.api_version,
        # Only check response if not connecting to GKE
        check_response_func=response_func,
        http_client=conn_context.HttpClient(),
    )
    # pylint: enable=protected-access
    yield ServerlessOperations(
        client,
        conn_info,
        op_client,
    )


def _Nonce():
  """Return a random string with unlikely collision to use as a nonce."""
  return ''.join(
      random.choice(string.ascii_lowercase) for _ in range(_NONCE_LENGTH)
  )


@dataclasses.dataclass(frozen=True)
class _NewRevisionNonceChange(config_changes_mod.TemplateConfigChanger):
  """Forces a new revision to get created by posting a random nonce label."""

  nonce: str

  def Adjust(self, resource):
    resource.template.labels[revision.NONCE_LABEL] = self.nonce
    resource.template.name = None
    return resource


class _NewRevisionForcingChange(config_changes_mod.RevisionNameChanges):
  """Forces a new revision to get created by changing the revision name."""

  def Adjust(self, resource):
    """Adjust by revision name."""
    if revision.NONCE_LABEL in resource.template.labels:
      del resource.template.labels[revision.NONCE_LABEL]
    return super().Adjust(resource)


def _IsDigest(url):
  """Return true if the given image url is by-digest."""
  return '@sha256:' in url


@dataclasses.dataclass(frozen=True)
class _SwitchToDigestChange(config_changes_mod.TemplateConfigChanger):
  """Switches the configuration from by-tag to by-digest."""

  base_revision: revision.Revision

  def Adjust(self, resource):
    if _IsDigest(self.base_revision.image):
      return resource
    if not self.base_revision.image_digest:
      return resource

    resource.template.image = self.base_revision.image_digest
    return resource


@dataclasses.dataclass(frozen=True)
class _AddDigestToImageChange(config_changes_mod.TemplateConfigChanger):
  """Add image digest that comes from source build."""

  image_digest: str

  def Adjust(self, resource):
    if _IsDigest(resource.template.image):
      return resource

    resource.template.image = resource.template.image + '@' + self.image_digest
    return resource


class ServerlessOperations(object):
  """Client used by Serverless to communicate with the actual Serverless API."""

  def __init__(self, client, conn_context, op_client):
    """Inits ServerlessOperations with given API clients.

    Args:
      client: The API client for interacting with Kubernetes Cloud Run APIs.
      conn_context: the connection context used to create this object.
      op_client: The API client for interacting with One Platform APIs. Or None
        if interacting with Cloud Run for Anthos.
    """
    self._client = client
    self._registry = resources.REGISTRY.Clone()
    self._registry.RegisterApiByName(
        conn_context.api_name, conn_context.api_version
    )
    self._op_client = op_client
    self._region = conn_context.region
    self._conn_context = conn_context

  @property
  def messages_module(self):
    return self._client.MESSAGES_MODULE

  def GetRevision(self, revision_ref):
    """Get the revision.

    Args:
      revision_ref: Resource, revision to get.

    Returns:
      A revision.Revision object.
    """
    messages = self.messages_module
    revision_name = revision_ref.RelativeName()
    request = messages.RunNamespacesRevisionsGetRequest(name=revision_name)
    try:
      with metrics.RecordDuration(metric_names.GET_REVISION):
        response = self._client.namespaces_revisions.Get(request)
      return revision.Revision(response, messages)
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)
    except api_exceptions.HttpNotFoundError:
      return None

  def Upload(self, deployable):
    """Upload the code for the given deployable."""
    deployable.UploadFiles()

  def WaitForCondition(self, poller, max_wait_ms=0):
    """Wait for a configuration to be ready in latest revision.

    Args:
      poller: A ConditionPoller object.
      max_wait_ms: int, if not 0, passed to waiter.PollUntilDone.

    Returns:
      A condition.Conditions object.

    Raises:
      RetryException: Max retry limit exceeded.
      ConfigurationError: configuration failed to
    """

    try:
      if max_wait_ms == 0:
        return waiter.PollUntilDone(poller, None, wait_ceiling_ms=1000)
      return waiter.PollUntilDone(
          poller, None, max_wait_ms=max_wait_ms, wait_ceiling_ms=1000
      )
    except retry.RetryException as err:
      conditions = poller.GetConditions()
      # err.message already indicates timeout. Check ready_cond_type for more
      # information.
      msg = conditions.DescriptiveMessage() if conditions else None
      if msg:
        log.error('Still waiting: {}'.format(msg))
      raise err

  def ListServices(self, namespace_ref):
    """Returns all services in the namespace."""
    messages = self.messages_module
    request = messages.RunNamespacesServicesListRequest(
        parent=namespace_ref.RelativeName()
    )
    try:
      with metrics.RecordDuration(metric_names.LIST_SERVICES):
        response = self._client.namespaces_services.List(request)
      return [service.Service(item, messages) for item in response.items]
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)

  def ListConfigurations(self, namespace_ref):
    """Returns all configurations in the namespace."""
    messages = self.messages_module
    request = messages.RunNamespacesConfigurationsListRequest(
        parent=namespace_ref.RelativeName()
    )
    try:
      with metrics.RecordDuration(metric_names.LIST_CONFIGURATIONS):
        response = self._client.namespaces_configurations.List(request)
      return [
          configuration.Configuration(item, messages) for item in response.items
      ]
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)

  def ListRoutes(self, namespace_ref):
    """Returns all routes in the namespace."""
    messages = self.messages_module
    request = messages.RunNamespacesRoutesListRequest(
        parent=namespace_ref.RelativeName()
    )
    with metrics.RecordDuration(metric_names.LIST_ROUTES):
      response = self._client.namespaces_routes.List(request)
    return [route.Route(item, messages) for item in response.items]

  def GetService(self, service_ref):
    """Return the relevant Service from the server, or None if 404."""
    messages = self.messages_module
    service_get_request = messages.RunNamespacesServicesGetRequest(
        name=service_ref.RelativeName()
    )

    try:
      with metrics.RecordDuration(metric_names.GET_SERVICE):
        service_get_response = self._client.namespaces_services.Get(
            service_get_request
        )
        return service.Service(service_get_response, messages)
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)
    except api_exceptions.HttpNotFoundError:
      return None

  def WaitService(
      self, operation_id, service_ref, release_track=base.ReleaseTrack.GA
  ):
    """Return the relevant Service from the server, or None if 404."""
    messages = self.messages_module
    project = properties.VALUES.core.project.Get(required=True)
    op_name = (
        f'projects/{project}/locations/{self._region}/operations/{operation_id}'
    )
    op_ref = self._registry.ParseRelativeName(
        op_name, collection='run.projects.locations.operations'
    )
    try:
      with metrics.RecordDuration(metric_names.WAIT_OPERATION):
        poller = op_pollers.WaitOperationPoller(
            self.messages_module,
            self._client.projects_locations_services,
            self._client.projects_locations_operations,
        )
        if release_track == base.ReleaseTrack.ALPHA:
          operation = poller.Poll(op_ref)
          # operation.response will only be filled if the operation is done.
          # if the opration isn't done, operation.metadata should have status
          # information for the tracker.
          if operation.response:
            as_dict = encoding.MessageToPyValue(operation.response)
            as_pb = encoding.PyValueToMessage(messages.Service, as_dict)
            return service.Service(as_pb, self.messages_module)
          elif operation.metadata:
            as_dict = encoding.MessageToPyValue(operation.metadata)
            as_pb = encoding.PyValueToMessage(messages.Service, as_dict)
            return service.Service(as_pb, self.messages_module)
          else:
            return self.GetService(service_ref)
        else:
          operation = waiter.PollUntilDone(poller, op_ref)
          as_dict = encoding.MessageToPyValue(operation.response)
          as_pb = encoding.PyValueToMessage(messages.Service, as_dict)
          return service.Service(as_pb, self.messages_module)

    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)
    except api_exceptions.HttpNotFoundError:
      return None

  def GetConfiguration(self, service_or_configuration_ref):
    """Return the relevant Configuration from the server, or None if 404."""
    messages = self.messages_module
    if hasattr(service_or_configuration_ref, 'servicesId'):
      name = self._registry.Parse(
          service_or_configuration_ref.servicesId,
          params={
              'namespacesId': service_or_configuration_ref.namespacesId,
          },
          collection='run.namespaces.configurations',
      ).RelativeName()
    else:
      name = service_or_configuration_ref.RelativeName()
    configuration_get_request = messages.RunNamespacesConfigurationsGetRequest(
        name=name
    )

    try:
      with metrics.RecordDuration(metric_names.GET_CONFIGURATION):
        configuration_get_response = self._client.namespaces_configurations.Get(
            configuration_get_request
        )
      return configuration.Configuration(configuration_get_response, messages)
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)
    except api_exceptions.HttpNotFoundError:
      return None

  def GetRoute(self, service_or_route_ref):
    """Return the relevant Route from the server, or None if 404."""
    messages = self.messages_module
    if hasattr(service_or_route_ref, 'servicesId'):
      name = self._registry.Parse(
          service_or_route_ref.servicesId,
          params={
              'namespacesId': service_or_route_ref.namespacesId,
          },
          collection='run.namespaces.routes',
      ).RelativeName()
    else:
      name = service_or_route_ref.RelativeName()
    route_get_request = messages.RunNamespacesRoutesGetRequest(name=name)

    try:
      with metrics.RecordDuration(metric_names.GET_ROUTE):
        route_get_response = self._client.namespaces_routes.Get(
            route_get_request
        )
      return route.Route(route_get_response, messages)
    except api_exceptions.HttpNotFoundError:
      return None

  def DeleteService(self, service_ref):
    """Delete the provided Service.

    Args:
      service_ref: Resource, a reference to the Service to delete

    Raises:
      ServiceNotFoundError: if provided service is not found.
    """
    messages = self.messages_module
    service_name = service_ref.RelativeName()
    service_delete_request = messages.RunNamespacesServicesDeleteRequest(
        name=service_name,
    )

    try:
      with metrics.RecordDuration(metric_names.DELETE_SERVICE):
        self._client.namespaces_services.Delete(service_delete_request)
    except api_exceptions.HttpNotFoundError:
      raise serverless_exceptions.ServiceNotFoundError(
          'Service [{}] could not be found.'.format(service_ref.servicesId)
      )

  def DeleteRevision(self, revision_ref):
    """Delete the provided Revision.

    Args:
      revision_ref: Resource, a reference to the Revision to delete

    Raises:
      RevisionNotFoundError: if provided revision is not found.
    """
    messages = self.messages_module
    revision_name = revision_ref.RelativeName()
    request = messages.RunNamespacesRevisionsDeleteRequest(name=revision_name)
    try:
      with metrics.RecordDuration(metric_names.DELETE_REVISION):
        self._client.namespaces_revisions.Delete(request)
    except api_exceptions.HttpNotFoundError:
      raise serverless_exceptions.RevisionNotFoundError(
          'Revision [{}] could not be found.'.format(revision_ref.revisionsId)
      )

  def GetRevisionsByNonce(self, namespace_ref, nonce):
    """Return all revisions with the given nonce."""
    messages = self.messages_module
    request = messages.RunNamespacesRevisionsListRequest(
        parent=namespace_ref.RelativeName(),
        labelSelector='{} = {}'.format(revision.NONCE_LABEL, nonce),
    )
    try:
      response = self._client.namespaces_revisions.List(request)
      return [revision.Revision(item, messages) for item in response.items]
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)

  def _GetBaseRevision(self, template, metadata, status):
    """Return a Revision for use as the "base revision" for a change.

    When making a change that should not affect the code running, the
    "base revision" is the revision that we should lock the code to - it's where
    we get the digest for the image to run.

    Getting this revision:
      * If there's a name in the template metadata, use that
      * If there's a nonce in the revisonTemplate metadata, use that
      * If that query produces >1 or 0 after a short timeout, use
        the latestCreatedRevision in status.

    Arguments:
      template: Revision, the revision template to get the base revision of. May
        have been derived from a Service.
      metadata: ObjectMeta, the metadata from the top-level object
      status: Union[ConfigurationStatus, ServiceStatus], the status of the top-
        level object.

    Returns:
      The base revision of the configuration or None if not found by revision
        name nor nonce and latestCreatedRevisionName does not exist on the
        Service object.
    """
    base_revision = None
    # Try to find by revision name
    base_revision_name = template.name
    if base_revision_name:
      try:
        revision_ref_getter = functools.partial(
            self._registry.Parse,
            params={'namespacesId': metadata.namespace},
            collection='run.namespaces.revisions',
        )
        poller = op_pollers.RevisionNameBasedPoller(self, revision_ref_getter)
        base_revision = poller.GetResult(
            waiter.PollUntilDone(
                poller, base_revision_name, sleep_ms=500, max_wait_ms=2000
            )
        )
      except retry.RetryException:
        pass
    # Name polling didn't work. Fall back to nonce polling
    if not base_revision:
      base_revision_nonce = template.labels.get(revision.NONCE_LABEL, None)
      if base_revision_nonce:
        try:
          # TODO(b/148817410): Remove this when the api has been split.
          # This try/except block is needed because the v1alpha1 and v1 run apis
          # have different collection names for the namespaces.
          try:
            namespace_ref = self._registry.Parse(
                metadata.namespace, collection='run.namespaces'
            )
          except resources.InvalidCollectionException:
            namespace_ref = self._registry.Parse(
                metadata.namespace, collection='run.api.v1.namespaces'
            )
          poller = op_pollers.NonceBasedRevisionPoller(self, namespace_ref)
          base_revision = poller.GetResult(
              waiter.PollUntilDone(
                  poller, base_revision_nonce, sleep_ms=500, max_wait_ms=2000
              )
          )
        except retry.RetryException:
          pass
    # Nonce polling didn't work, because some client didn't post one or didn't
    # change one. Fall back to the (slightly racy) `latestCreatedRevisionName`.
    if not base_revision:
      if status.latestCreatedRevisionName:
        # Get by latestCreatedRevisionName
        revision_ref = self._registry.Parse(
            status.latestCreatedRevisionName,
            params={'namespacesId': metadata.namespace},
            collection='run.namespaces.revisions',
        )
        base_revision = self.GetRevision(revision_ref)
    return base_revision

  def _EnsureImageDigest(self, serv, config_changes):
    """Make config_changes include switch by-digest image if not so already."""
    if not _IsDigest(serv.template.image):
      base_revision = self._GetBaseRevision(
          serv.template, serv.metadata, serv.status
      )
      if base_revision:
        config_changes.append(_SwitchToDigestChange(base_revision))

  def _UpdateOrCreateService(
      self, service_ref, config_changes, with_code, serv, dry_run=False
  ):
    """Apply config_changes to the service.

    Create it if necessary.

    Arguments:
      service_ref: Reference to the service to create or update
      config_changes: list of ConfigChanger to modify the service with
      with_code: bool, True if the config_changes contains code to deploy. We
        can't create the service if we're not deploying code.
      serv: service.Service, For update the Service to update and for create
        None.
      dry_run: bool, if True only validate the change.

    Returns:
      The Service object we created or modified.
    """
    messages = self.messages_module
    try:
      if serv:
        # PUT the changed Service
        serv = config_changes_mod.WithChanges(serv, config_changes)
        serv_name = service_ref.RelativeName()
        serv_update_req = messages.RunNamespacesServicesReplaceServiceRequest(
            service=serv.Message(),
            name=serv_name,
            dryRun=('all' if dry_run else None),
        )
        with metrics.RecordDuration(metric_names.UPDATE_SERVICE):
          updated = self._client.namespaces_services.ReplaceService(
              serv_update_req
          )
        return service.Service(updated, messages)

      else:
        if not with_code:
          raise serverless_exceptions.ServiceNotFoundError(
              'Service [{}] could not be found.'.format(service_ref.servicesId)
          )
        # POST a new Service
        new_serv = service.Service.New(self._client, service_ref.namespacesId)
        new_serv.name = service_ref.servicesId
        parent = service_ref.Parent().RelativeName()
        new_serv = config_changes_mod.WithChanges(new_serv, config_changes)
        serv_create_req = messages.RunNamespacesServicesCreateRequest(
            service=new_serv.Message(),
            parent=parent,
            dryRun='all' if dry_run else None,
        )
        with metrics.RecordDuration(metric_names.CREATE_SERVICE):
          raw_service = self._client.namespaces_services.Create(serv_create_req)
        return service.Service(raw_service, messages)
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)
    except api_exceptions.HttpBadRequestError as e:
      exceptions.reraise(serverless_exceptions.HttpError(e))
    except api_exceptions.HttpNotFoundError as e:
      parsed_err = api_lib_exceptions.HttpException(e)
      if (
          hasattr(parsed_err.payload, 'domain_details')
          and 'run.googleapis.com' in parsed_err.payload.domain_details
      ):
        raise parsed_err
      platform = properties.VALUES.run.platform.Get()
      error_msg = 'Deployment endpoint was not found.'
      if platform == 'gke':
        all_clusters = global_methods.ListClusters()
        clusters = ['* {} in {}'.format(c.name, c.zone) for c in all_clusters]
        error_msg += (
            ' Perhaps the provided cluster was invalid or '
            'does not have Cloud Run enabled. Pass the '
            '`--cluster` and `--cluster-location` flags or set the '
            '`run/cluster` and `run/cluster_location` properties to '
            'a valid cluster and zone and retry.'
            '\nAvailable clusters:\n{}'.format('\n'.join(clusters))
        )
      elif platform == 'managed':
        all_regions = global_methods.ListRegions(self._op_client)
        if self._region not in all_regions:
          regions = ['* {}'.format(r) for r in all_regions]
          error_msg += (
              ' The provided region was invalid. '
              'Pass the `--region` flag or set the '
              '`run/region` property to a valid region and retry.'
              '\nAvailable regions:\n{}'.format('\n'.join(regions))
          )
      elif platform == 'kubernetes':
        error_msg += (
            ' Perhaps the provided cluster was invalid or '
            'does not have Cloud Run enabled. Ensure in your '
            'kubeconfig file that the cluster referenced in '
            'the current context or the specified context '
            'is a valid cluster and retry.'
        )
      raise serverless_exceptions.DeploymentFailedError(error_msg)
    except api_exceptions.HttpError as e:
      platform = properties.VALUES.run.platform.Get()
      if platform == 'managed':
        exceptions.reraise(e)
      k8s_error = serverless_exceptions.KubernetesExceptionParser(e)
      causes = '\n\n'.join([c['message'] for c in k8s_error.causes])
      if not causes:
        causes = k8s_error.error
      raise serverless_exceptions.KubernetesError(
          'Error{}:\n{}\n'.format(
              's' if len(k8s_error.causes) > 1 else '', causes
          )
      )

  def UpdateTraffic(
      self,
      service_ref,
      config_changes,
      tracker,
      asyn,
      is_verbose,
      release_track,
  ):
    """Update traffic splits for service."""
    if tracker is None:
      tracker = progress_tracker.NoOpStagedProgressTracker(
          stages.UpdateTrafficStages(),
          interruptable=True,
          aborted_message='aborted',
      )
    serv = self.GetService(service_ref)
    if not serv:
      raise serverless_exceptions.ServiceNotFoundError(
          'Service [{}] could not be found.'.format(service_ref.servicesId)
      )

    updated_serv = self._UpdateOrCreateService(
        service_ref, config_changes, False, serv
    )

    if not asyn:
      if updated_serv.conditions.IsReady():
        return updated_serv
      if updated_serv.operation_id is None or is_verbose:
        getter = functools.partial(self.GetService, service_ref)
      else:
        getter = functools.partial(
            self.WaitService,
            updated_serv.operation_id,
            service_ref,
            release_track,
        )
      poller = op_pollers.ServiceConditionPoller(
          getter, tracker, serv=updated_serv
      )
      self.WaitForCondition(poller)
      updated_serv = poller.GetResource()
    return updated_serv

  def _AddRevisionForcingChange(self, serv, config_changes):
    """Get a new revision forcing config change for the given service."""
    curr_generation = serv.generation if serv is not None else 0
    revision_suffix = '{}-{}'.format(
        str(curr_generation + 1).zfill(5), name_generator.GenerateName()
    )
    config_changes.insert(0, _NewRevisionForcingChange(revision_suffix))

  def _DeleteRevisionBaseImageAnnotation(
      self, config_changes, source_container_name
  ):
    """Delete the base image revision level annotation for source container."""
    config_changes.append(
        config_changes_mod.BaseImagesAnnotationChange(
            deletes=[source_container_name]
        )
    )

  def _ReplaceOrAddBaseImage(
      self,
      config_changes,
      base_image_from_build,
      ingress_container_name,
  ):
    """Replace the base image in the config changes with the rectified base image returned from build.

    Args:
      config_changes: list, objects that implement Adjust().
      base_image_from_build: The base image from build to opt-in automatic build
        image updates.
      ingress_container_name: The name of the ingress container that is build
        from source. This could be empty string.
    """
    config_changes.append(
        config_changes_mod.BaseImagesAnnotationChange(
            updates={ingress_container_name: base_image_from_build}
        )
    )

  def _GetFunctionTargetFromBuildPack(self, pack):
    """Get the function target from the build pack."""
    if pack:
      for env_var in pack[0].get('envs', []):
        if env_var.startswith('GOOGLE_FUNCTION_TARGET='):
          return env_var.split('=', 1)[1]
    return None

  def _ValidateServiceBeforeSourceDeploy(
      self,
      tracker: progress_tracker.StagedProgressTracker,
      service_ref: string,
      prefetch: service.Service,
      config_changes: List[config_changes_mod.ConfigChanger],
      generate_name: bool,
  ):
    """Validate the service in dry run before building."""
    svc = None
    validate_config_changes = config_changes[:]
    if prefetch:
      svc = service.Service(
          copy.deepcopy(prefetch.Message()), self.messages_module
      )
    elif prefetch is not None:
      # prefetch is None if we tried to get it and it's a create, or
      # false if this is a replace so we never looked for it.
      svc = self.GetService(service_ref)
    # source deploy always has a template change so we should always
    # force a new revision name.
    if generate_name:
      self._AddRevisionForcingChange(svc, validate_config_changes)
    else:
      validate_config_changes.append(_NewRevisionNonceChange(_Nonce()))

    tracker.StartStage(stages.VALIDATE_SERVICE)
    tracker.UpdateHeaderMessage('Validating Service...')
    self._UpdateOrCreateService(
        service_ref, validate_config_changes, True, svc, dry_run=True
    )
    tracker.CompleteStage(stages.VALIDATE_SERVICE)

  def ReleaseService(
      self,
      service_ref,
      config_changes,
      release_track,
      tracker=None,
      asyn=False,
      allow_unauthenticated=None,
      multiregion_regions=None,
      for_replace=False,
      prefetch=False,
      build_image=None,
      build_pack=None,
      build_region=None,
      build_source=None,
      repo_to_create=None,
      already_activated_services=False,
      dry_run=False,
      generate_name=False,
      delegate_builds=False,
      base_image=None,
      build_service_account=None,
      deploy_from_source_container_name='',
      build_worker_pool=None,
      build_machine_type=None,
      build_env_vars=None,
      enable_automatic_updates=False,
      is_verbose=False,
      source_bucket=None,
      kms_key=None,
      iap_enabled=None,
      skip_build=False,
  ):
    """Change the given service in prod using the given config_changes.

    Ensures a new revision is always created, even if the spec of the revision
    has not changed.

    Args:
      service_ref: Resource, the service to release.
      config_changes: list, objects that implement Adjust().
      release_track: ReleaseTrack, the release track of a command calling this.
      tracker: StagedProgressTracker, to report on the progress of releasing.
      asyn: bool, if True, return without waiting for the service to be updated.
      allow_unauthenticated: bool, True if creating a hosted Cloud Run service
        which should also have its IAM policy set to allow unauthenticated
        access. False if removing the IAM policy to allow unauthenticated access
        from a service.
      multiregion_regions: The regions for a multi-region service.
      for_replace: bool, If the change is for a replacing the service from a
        YAML specification.
      prefetch: the service, pre-fetched for ReleaseService. `False` indicates
        the caller did not perform a prefetch; `None` indicates a nonexistent
        service.
      build_image: The build image reference to the build.
      build_pack: The build pack reference to the build.
      build_region: The region to use for the build, in case of multi-region.
      build_source: The build source reference to the build.
      repo_to_create: Optional
        googlecloudsdk.command_lib.artifacts.docker_util.DockerRepo defining a
        repository to be created.
      already_activated_services: bool. If true, skip activation prompts for
        services
      dry_run: bool. If true, only validate the configuration.
      generate_name: bool. If true, create a revision name, otherwise add nonce.
      delegate_builds: bool. If true, use the Build API to submit builds.
      base_image: The build base image to opt-in automatic build image updates.
      build_service_account: The service account to use to execute the build.
      deploy_from_source_container_name: The name of the ingress container that
        is deployed from source include build-from-source and zip deploy. This
        field could be an empty string.
      build_worker_pool:  The name of the Cloud Build custom worker pool that
        should be used to build the function.
      build_machine_type: The machine type from Cloud Build default pool to use
        for the build.
      build_env_vars: Dictionary of build env vars to send to submit build.
      enable_automatic_updates: If true, opt-in automatic build image updates.
        If false, opt-out automatic build image updates.
      is_verbose: Print verbose output. Forces polling instead of waiting.
      source_bucket: The existing bucket to use for source uploads. Leave it as
        None to create a new bucket.
      kms_key: The KMS key to use for the deployment.
      iap_enabled: If true, assign run.invoker access to IAP P4SA, if false,
        remove run.invoker access from IAP P4SA.
      skip_build: If true, skip the cloud build step.

    Returns:
      service.Service, the service as returned by the server on the POST/PUT
       request to create/update the service.
    """
    requires_build = build_source is not None and not skip_build

    region = build_region or self._region

    if tracker is None:
      tracker = progress_tracker.NoOpStagedProgressTracker(
          stages.ServiceStages(
              allow_unauthenticated is not None,
              include_validate_service=requires_build,
              include_upload_source=build_source is not None,
              include_build=requires_build,
              include_create_repo=repo_to_create is not None,
              include_iap=iap_enabled is not None,
          ),
          interruptable=True,
          aborted_message='aborted',
      )

    if build_source is not None and skip_build:
      tracker.StartStage(stages.UPLOAD_SOURCE)
      if sources.IsGcsObject(build_source):
        tracker.UpdateHeaderMessage(
            'Using the source from the specified bucket.'
        )
        source_path = build_source
      else:
        source = sources.Upload(
            build_source,
            region,
            service_ref,
            source_bucket,
            sources.ArchiveType.TAR,
            respect_gitignore=False,
        )
        # TODO(b/423646813): Remove this once zip deploys properly handles the
        # generation number.
        source.generation = None
        source_path = sources.GetGsutilUri(source)
      config_changes.append(
          config_changes_mod.SourcesAnnotationChange(
              updates={deploy_from_source_container_name: source_path}
          )
      )
      tracker.CompleteStage(stages.UPLOAD_SOURCE)
    elif requires_build:
      new_conn = self._conn_context.GetContextWithRegionOverride(region)
      with new_conn:
        self._ValidateServiceBeforeSourceDeploy(
            tracker, service_ref, prefetch, config_changes, generate_name
        )
        # TODO(b/355762514): Either remove or re-enable this validation.
        # self._ValidateService(service_ref, config_changes)
        (
            image_digest,
            build_base_image,
            build_id,
            uploaded_source,
            build_name,
        ) = deployer.CreateImage(
            tracker,
            build_image,
            build_source,
            build_pack,
            repo_to_create,
            release_track,
            already_activated_services,
            region,
            service_ref,
            delegate_builds,
            base_image,
            build_service_account,
            build_worker_pool,
            build_machine_type,
            build_env_vars,
            enable_automatic_updates,
            source_bucket,
            kms_key,
        )
        if image_digest is None:
          return
        self._ClearRunFunctionsAnnotations(config_changes)
        self._AddRunFunctionsAnnotations(
            config_changes=config_changes,
            uploaded_source=uploaded_source,
            service_account=build_service_account,
            worker_pool=build_worker_pool,
            build_env_vars=build_env_vars,
            build_pack=build_pack,
            build_id=build_id,
            build_image=build_image,
            build_name=build_name,
            build_base_image=build_base_image,
            build_from_source_container_name=deploy_from_source_container_name,
            enable_automatic_updates=enable_automatic_updates,
        )
        config_changes.append(_AddDigestToImageChange(image_digest))
    if prefetch is None:
      serv = None
    elif build_source:
      # if we're building from source, we want to force a new fetch
      # because building takes a while which leaves a long time for
      # potential write conflicts.
      serv = self.GetService(service_ref)
    else:
      serv = prefetch or self.GetService(service_ref)
    if for_replace:
      with_image = True
    else:
      with_image = any(
          isinstance(c, config_changes_mod.ImageChange) for c in config_changes
      )
      if config_changes_mod.AdjustsTemplate(config_changes):
        # Only force a new revision if there's other template-level changes that
        # warrant a new revision.
        if generate_name:
          self._AddRevisionForcingChange(serv, config_changes)
        else:
          config_changes.append(_NewRevisionNonceChange(_Nonce()))
        if serv and not with_image and not multiregion_regions:
          # Avoid changing the running code by making the new revision by digest
          # We can't do this in multi-region services, because there is no
          # Revisions API.
          self._EnsureImageDigest(serv, config_changes)

    if serv and serv.metadata.deletionTimestamp is not None:
      raise serverless_exceptions.DeploymentFailedError(
          'Service [{}] is in the process of being deleted.'.format(
              service_ref.servicesId
          )
      )

    updated_service = self._UpdateOrCreateService(
        service_ref, config_changes, with_image, serv, dry_run
    )

    # Handle SetIamPolicy call(s).
    self._HandleAllowUnauthenticated(
        service_ref, allow_unauthenticated, multiregion_regions, tracker
    )

    self._HandleIap(service_ref, iap_enabled, updated_service, tracker)

    if not asyn and not dry_run:
      if updated_service.conditions.IsReady():
        return updated_service
      if updated_service.operation_id is None or is_verbose:
        getter = functools.partial(self.GetService, service_ref)
      else:
        getter = functools.partial(
            self.WaitService,
            updated_service.operation_id,
            service_ref,
            release_track,
        )
      poller = op_pollers.ServiceConditionPoller(
          getter,
          tracker,
          dependencies=stages.ServiceDependencies(multiregion_regions),
          serv=updated_service,
      )
      self.WaitForCondition(poller)
      for msg in run_condition.GetNonTerminalMessages(poller.GetConditions()):
        tracker.AddWarning(msg)
      updated_service = poller.GetResource()

    return updated_service

  def _HandleAllowUnauthenticated(
      self, service_ref, allow_unauthenticated, multiregion_regions, tracker
  ):
    """Handle SetIamPolicy call(s)."""
    if allow_unauthenticated is not None and multiregion_regions is not None:
      return self._HandleMultiRegionAllowUnauthenticated(
          service_ref, allow_unauthenticated, multiregion_regions, tracker
      )
    if allow_unauthenticated is not None:
      try:
        tracker.StartStage(stages.SERVICE_IAM_POLICY_SET)
        tracker.UpdateStage(stages.SERVICE_IAM_POLICY_SET, '')
        self.AddOrRemoveIamPolicyBinding(
            service_ref,
            allow_unauthenticated,
            ALLOW_UNAUTH_POLICY_BINDING_MEMBER,
            ALLOW_UNAUTH_POLICY_BINDING_ROLE,
        )
        tracker.CompleteStage(stages.SERVICE_IAM_POLICY_SET)
      except api_exceptions.HttpError:
        warning_message = (
            'Setting IAM policy failed, try "gcloud beta run services '
            '{}-iam-policy-binding --region={region} --member=allUsers '
            '--role=roles/run.invoker {service}"'.format(
                'add' if allow_unauthenticated else 'remove',
                region=self._region,
                service=service_ref.servicesId,
            )
        )
        tracker.CompleteStageWithWarning(
            stages.SERVICE_IAM_POLICY_SET, warning_message=warning_message
        )

  def _HandleMultiRegionAllowUnauthenticated(
      self, service_ref, allow_unauthenticated, multiregion_regions, tracker
  ):
    """Handle SetIamPolicy calls for Multi-Region Services."""
    tracker.StartStage(stages.SERVICE_IAM_POLICY_SET)
    warning_message = None
    for region in multiregion_regions:
      try:
        tracker.UpdateStage(
            stages.SERVICE_IAM_POLICY_SET,
            'Setting IAM policy for region {}'.format(region),
        )
        self.AddOrRemoveIamPolicyBinding(
            service_ref,
            allow_unauthenticated,
            ALLOW_UNAUTH_POLICY_BINDING_MEMBER,
            ALLOW_UNAUTH_POLICY_BINDING_ROLE,
            region_override=region,
        )
      except api_exceptions.HttpError:
        if not warning_message:
          warning_message = (
              'Setting IAM policy failed, try "gcloud beta run services '
              '{}-iam-policy-binding --region=[region] --member=allUsers '
              '--role=roles/run.invoker {service}" for regions: {region}'
              .format(
                  'add' if allow_unauthenticated else 'remove',
                  region=region,
                  service=service_ref.servicesId,
              )
          )
        else:
          warning_message += region
    if not warning_message:
      tracker.CompleteStage(stages.SERVICE_IAM_POLICY_SET)
    else:
      tracker.CompleteStageWithWarning(
          stages.SERVICE_IAM_POLICY_SET, warning_message=warning_message
      )

  def GetServiceAgent(self, project_num):
    """Returns the service agent for the given project.

    For Universe Projects, the format will look like
    service-{project_num}@gcp-sa-iap.{project_prefix}iam.gserviceaccount.com
    FOR GDU format will look like
    service-{project_num}@gcp-sa-iap.iam.gserviceaccount.com

    Args:
      project_num: The project number.
    """
    project_prefix = (
        universe_descriptor.GetUniverseDomainDescriptor().project_prefix
    )
    if project_prefix:
      return f'serviceAccount:service-{project_num}@gcp-sa-iap.{project_prefix}.iam.gserviceaccount.com'
    return f'serviceAccount:service-{project_num}@gcp-sa-iap.iam.gserviceaccount.com'

  def _HandleIap(self, service_ref, iap_enabled, updated_service, tracker):
    """Handle IAP changes."""
    iap_service_agent = self.GetServiceAgent(updated_service.namespace)
    if iap_enabled is not None:
      try:
        tracker.StartStage(stages.SERVICE_IAP_ENABLE)
        tracker.UpdateStage(stages.SERVICE_IAP_ENABLE, '')
        if iap_enabled:
          self._AddIamPolicyBindingWithRetry(service_ref, iap_service_agent)
        else:
          self.AddOrRemoveIamPolicyBinding(
              service_ref,
              False,
              iap_service_agent,
              ALLOW_UNAUTH_POLICY_BINDING_ROLE,
          )
        tracker.CompleteStage(stages.SERVICE_IAP_ENABLE)
      except api_exceptions.HttpError as e:
        if (
            iap_enabled and e.status_code == 400
        ):  # IAP service agent not ready yet.
          warning_message = (
              'IAP has not been successfully enabled. If this is the first time'
              " you're enabling IAP in this project, please wait a few minutes"
              ' for the service agent to propagate, then try enabling IAP again'
              ' on this service.'
          )
        else:
          warning_message = (
              'Setting IAM policy failed, try "gcloud run services'
              ' {}-iam-policy-binding --region={region} --member={member}'
              ' --role=roles/run.invoker {service}"'.format(
                  'add' if iap_enabled else 'remove',
                  region=self._region,
                  member=iap_service_agent,
                  service=service_ref.servicesId,
              )
          )
        tracker.CompleteStageWithWarning(
            stages.SERVICE_IAP_ENABLE, warning_message=warning_message
        )

  @retry.RetryOnException(max_retrials=10, sleep_ms=15 * 1000)
  def _AddIamPolicyBindingWithRetry(self, service_ref, iap_service_agent):
    return self.AddOrRemoveIamPolicyBinding(
        service_ref, True, iap_service_agent, ALLOW_UNAUTH_POLICY_BINDING_ROLE
    )

  def GetWorkerPool(self, worker_pool_ref):
    """Return the relevant WorkerPool from the server, or None if 404."""
    messages = self.messages_module
    worker_pool_get_request = messages.RunNamespacesWorkerpoolsGetRequest(
        name=worker_pool_ref.RelativeName()
    )

    try:
      with metrics.RecordDuration(metric_names.GET_WORKER_POOL):
        worker_pool_get_response = self._client.namespaces_workerpools.Get(
            worker_pool_get_request
        )
        return worker_pool_lib.WorkerPool(worker_pool_get_response, messages)
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)
    except api_exceptions.HttpNotFoundError:
      return None

  def ListWorkerPools(self, project_ref):
    """Returns all worker pools in the project."""
    messages = self.messages_module
    request = messages.RunNamespacesWorkerpoolsListRequest(
        parent=project_ref.RelativeName()
    )
    try:
      with metrics.RecordDuration(metric_names.LIST_WORKER_POOLS):
        response = self._client.namespaces_workerpools.List(request)
      return [
          worker_pool_lib.WorkerPool(item, messages) for item in response.items
      ]
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)

  def ReplaceWorkerPool(
      self,
      worker_pool_ref,
      config_changes,
      tracker,
      asyn,
      dry_run,
  ):
    """Replace the given worker pool in prod using the given config_changes.

    Args:
      worker_pool_ref: Resource, the worker pool to replace.
      config_changes: list, objects that implement Adjust().
      tracker: StagedProgressTracker, to report on the progress of releasing.
      asyn: bool, if True, return without waiting for the worker pool to be
        updated.
      dry_run: bool. If true, only validate the configuration.

    Returns:
      worker_pool.WorkerPool, the worker pool as returned by the server on the
      POST/PUT request to create/update the worker pool.
    """
    if tracker is None:
      tracker = progress_tracker.NoOpStagedProgressTracker(
          stages.WorkerPoolStages(),
          interruptable=True,
          aborted_message='aborted',
      )
    worker_pool = self.GetWorkerPool(worker_pool_ref)

    if worker_pool and worker_pool.metadata.deletionTimestamp is not None:
      raise serverless_exceptions.DeploymentFailedError(
          'Worker pool [{}] is in the process of being deleted.'.format(
              worker_pool_ref.workerpoolsId
          )
      )

    # update or create worker pool
    updated_worker_pool = self._UpdateOrCreateWorkerPool(
        worker_pool_ref, config_changes, worker_pool, dry_run
    )

    if not asyn and not dry_run:
      if updated_worker_pool.conditions.IsReady():
        return updated_worker_pool
    if updated_worker_pool.operation_id is None:
      getter = functools.partial(self.GetWorkerPool, worker_pool_ref)
    else:
      getter = functools.partial(
          self.WaitWorkerPool, updated_worker_pool.operation_id
      )
    poller = op_pollers.WorkerPoolConditionPoller(
        getter,
        tracker,
        worker_pool=updated_worker_pool,
    )
    self.WaitForCondition(poller)
    for msg in run_condition.GetNonTerminalMessages(poller.GetConditions()):
      tracker.AddWarning(msg)
    updated_worker_pool = poller.GetResource()

    return updated_worker_pool

  def WaitWorkerPool(self, operation_id):
    """Return the relevant WorkerPool from the server, or None if 404."""
    messages = self.messages_module
    project = properties.VALUES.core.project.Get(required=True)
    op_name = (
        f'projects/{project}/locations/{self._region}/operations/{operation_id}'
    )
    op_ref = self._registry.ParseRelativeName(
        op_name, collection='run.projects.locations.operations'
    )
    try:
      with metrics.RecordDuration(metric_names.WAIT_OPERATION):
        poller = op_pollers.WaitOperationPoller(
            self.messages_module,
            self._client.projects_locations_workerpools,
            self._client.projects_locations_operations,
        )
        operation = waiter.PollUntilDone(poller, op_ref)
        as_dict = encoding.MessageToPyValue(operation.response)
        as_pb = encoding.PyValueToMessage(messages.WorkerPool, as_dict)
        return worker_pool_lib.WorkerPool(as_pb, self.messages_module)
    except api_exceptions.HttpNotFoundError:
      return None

  def _UpdateOrCreateWorkerPool(
      self,
      worker_pool_ref,
      config_changes,
      worker_pool,
      dry_run,
  ):
    """Update or create worker pool."""
    messages = self.messages_module
    try:
      if worker_pool:
        # PUT the changed WorkerPool
        worker_pool = config_changes_mod.WithChanges(
            worker_pool, config_changes
        )
        worker_pool_name = worker_pool_ref.RelativeName()
        worker_pool_update_req = (
            messages.RunNamespacesWorkerpoolsReplaceWorkerPoolRequest(
                workerPool=worker_pool.Message(),
                name=worker_pool_name,
                dryRun=('all' if dry_run else None),
            )
        )
        with metrics.RecordDuration(metric_names.UPDATE_WORKER_POOL):
          updated = self._client.namespaces_workerpools.ReplaceWorkerPool(
              worker_pool_update_req
          )
        return worker_pool_lib.WorkerPool(updated, messages)
      else:
        # POST a new WorkerPool
        new_worker_pool = worker_pool_lib.WorkerPool.New(
            self._client, worker_pool_ref.namespacesId
        )
        new_worker_pool.name = worker_pool_ref.workerpoolsId
        parent = worker_pool_ref.Parent().RelativeName()
        new_worker_pool = config_changes_mod.WithChanges(
            new_worker_pool, config_changes
        )
        worker_pool_create_req = messages.RunNamespacesWorkerpoolsCreateRequest(
            workerPool=new_worker_pool.Message(),
            parent=parent,
            dryRun='all' if dry_run else None,
        )
        with metrics.RecordDuration(metric_names.CREATE_WORKER_POOL):
          raw_worker_pool = self._client.namespaces_workerpools.Create(
              worker_pool_create_req
          )
        return worker_pool_lib.WorkerPool(raw_worker_pool, messages)
    except api_exceptions.HttpBadRequestError as e:
      exceptions.reraise(serverless_exceptions.HttpError(e))
    except api_exceptions.HttpNotFoundError as e:
      parsed_err = api_lib_exceptions.HttpException(e)
      if (
          hasattr(parsed_err.payload, 'domain_details')
          and 'run.googleapis.com' in parsed_err.payload.domain_details
      ):
        raise parsed_err
      error_msg = 'Deployment endpoint was not found.'
      all_regions = global_methods.ListRegions(self._op_client)
      if self._region not in all_regions:
        regions = ['* {}'.format(r) for r in all_regions]
        error_msg += (
            ' The provided region was invalid. '
            'Pass the `--region` flag or set the '
            '`run/region` property to a valid region and retry.'
            '\nAvailable regions:\n{}'.format('\n'.join(regions))
        )
      raise serverless_exceptions.DeploymentFailedError(error_msg)
    except api_exceptions.HttpError as e:
      exceptions.reraise(e)

  def ListExecutions(
      self, namespace_ref, label_selector='', limit=None, page_size=100
  ):
    """List all executions for the given job.

    Executions list gets sorted by job name, creation timestamp, and completion
    timestamp.

    Args:
      namespace_ref: Resource, namespace to list executions in
      label_selector: Optional[string], extra label selector to filter
        executions
      limit: Optional[int], max number of executions to list.
      page_size: Optional[int], number of executions to fetch at a time

    Yields:
      Executions for the given surface
    """
    messages = self.messages_module
    request = messages.RunNamespacesExecutionsListRequest(
        parent=namespace_ref.RelativeName()
    )
    if label_selector:
      request.labelSelector = label_selector
    try:
      for result in list_pager.YieldFromList(
          service=self._client.namespaces_executions,
          request=request,
          limit=limit,
          batch_size=page_size,
          current_token_attribute='continue_',
          next_token_attribute=('metadata', 'continue_'),
          batch_size_attribute='limit',
      ):
        yield execution.Execution(result, messages)
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)

  def ListTasks(
      self,
      namespace_ref,
      execution_name,
      include_states=None,
      limit=None,
      page_size=100,
  ):
    """List all tasks for the given execution.

    Args:
      namespace_ref: Resource, namespace to list tasks in
      execution_name: str, The execution for which to list tasks.
      include_states: List[str], states of tasks to include in the list.
      limit: Optional[int], max number of tasks to list.
      page_size: Optional[int], number of tasks to fetch at a time

    Yields:
      Executions for the given surface
    """
    messages = self.messages_module
    request = messages.RunNamespacesTasksListRequest(
        parent=namespace_ref.RelativeName()
    )
    label_selectors = []
    if execution_name is not None:
      label_selectors.append(
          '{label} = {name}'.format(
              label=task.EXECUTION_LABEL, name=execution_name
          )
      )
    if include_states is not None:
      status_selector = '{label} in ({states})'.format(
          label=task.STATE_LABEL, states=','.join(include_states)
      )
      label_selectors.append(status_selector)
    if label_selectors:
      request.labelSelector = ','.join(label_selectors)
    try:
      for result in list_pager.YieldFromList(
          service=self._client.namespaces_tasks,
          request=request,
          limit=limit,
          batch_size=page_size,
          current_token_attribute='continue_',
          next_token_attribute=('metadata', 'continue_'),
          batch_size_attribute='limit',
      ):
        yield task.Task(result, messages)
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)

  def ListRevisions(
      self, namespace_ref, label_selector, limit=None, page_size=100
  ):
    """List all revisions for the given service.

    Revision list gets sorted by service name and creation timestamp.

    Args:
      namespace_ref: Resource, namespace to list revisions in
      label_selector: str, label selector for either a service or worker pool
        for which to list revisions.
      limit: Optional[int], max number of revisions to list.
      page_size: Optional[int], number of revisions to fetch at a time

    Yields:
      Revisions for the given surface
    """
    messages = self.messages_module
    request = messages.RunNamespacesRevisionsListRequest(
        parent=namespace_ref.RelativeName(),
    )
    if label_selector is not None:
      # If provided this will be either:
      # 1. 'serving.knative.dev/service = <service>' or
      # 2. 'run.googleapis.com/workerPool = <worker_pool>'.
      request.labelSelector = label_selector
    try:
      for result in list_pager.YieldFromList(
          service=self._client.namespaces_revisions,
          request=request,
          limit=limit,
          batch_size=page_size,
          current_token_attribute='continue_',
          next_token_attribute=('metadata', 'continue_'),
          batch_size_attribute='limit',
      ):
        yield revision.Revision(result, messages)
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)

  def ListDomainMappings(self, namespace_ref):
    """List all domain mappings.

    Args:
      namespace_ref: Resource, namespace to list domain mappings in.

    Returns:
      A list of domain mappings.
    """
    messages = self.messages_module
    request = messages.RunNamespacesDomainmappingsListRequest(
        parent=namespace_ref.RelativeName()
    )
    with metrics.RecordDuration(metric_names.LIST_DOMAIN_MAPPINGS):
      response = self._client.namespaces_domainmappings.List(request)
    return [
        domain_mapping.DomainMapping(item, messages) for item in response.items
    ]

  def CreateDomainMapping(
      self,
      domain_mapping_ref,
      service_name,
      config_changes,
      force_override=False,
  ):
    """Create a domain mapping.

    Args:
      domain_mapping_ref: Resource, domainmapping resource.
      service_name: str, the service to which to map domain.
      config_changes: list of ConfigChanger to modify the domainmapping with
      force_override: bool, override an existing mapping of this domain.

    Returns:
      A domain_mapping.DomainMapping object.
    """

    messages = self.messages_module
    new_mapping = domain_mapping.DomainMapping.New(
        self._client, domain_mapping_ref.namespacesId
    )
    new_mapping.name = domain_mapping_ref.domainmappingsId
    new_mapping.route_name = service_name
    new_mapping.force_override = force_override

    for config_change in config_changes:
      new_mapping = config_change.Adjust(new_mapping)

    request = messages.RunNamespacesDomainmappingsCreateRequest(
        domainMapping=new_mapping.Message(),
        parent=domain_mapping_ref.Parent().RelativeName(),
    )
    with metrics.RecordDuration(metric_names.CREATE_DOMAIN_MAPPING):
      try:
        response = self._client.namespaces_domainmappings.Create(request)
      except api_exceptions.HttpConflictError:
        raise serverless_exceptions.DomainMappingCreationError(
            'Domain mapping to [{}] already exists in this region.'.format(
                domain_mapping_ref.Name()
            )
        )
      # 'run domain-mappings create' is synchronous. Poll for its completion.x
      with progress_tracker.ProgressTracker('Creating...'):
        mapping = waiter.PollUntilDone(
            op_pollers.DomainMappingResourceRecordPoller(self),
            domain_mapping_ref,
        )
      ready = mapping.conditions.get('Ready')
      message = None
      if ready and ready.get('message'):
        message = ready['message']
      if not mapping.records:
        if (
            mapping.ready_condition['reason']
            == domain_mapping.MAPPING_ALREADY_EXISTS_CONDITION_REASON
        ):
          raise serverless_exceptions.DomainMappingAlreadyExistsError(
              'Domain mapping to [{}] is already in use elsewhere.'.format(
                  domain_mapping_ref.Name()
              )
          )
        raise serverless_exceptions.DomainMappingCreationError(
            message or 'Could not create domain mapping.'
        )
      if message:
        log.status.Print(message)
      return mapping

    return domain_mapping.DomainMapping(response, messages)

  def DeleteDomainMapping(self, domain_mapping_ref):
    """Delete a domain mapping.

    Args:
      domain_mapping_ref: Resource, domainmapping resource.
    """
    messages = self.messages_module

    request = messages.RunNamespacesDomainmappingsDeleteRequest(
        name=domain_mapping_ref.RelativeName()
    )
    with metrics.RecordDuration(metric_names.DELETE_DOMAIN_MAPPING):
      self._client.namespaces_domainmappings.Delete(request)

  def GetDomainMapping(self, domain_mapping_ref):
    """Get a domain mapping.

    Args:
      domain_mapping_ref: Resource, domainmapping resource.

    Returns:
      A domain_mapping.DomainMapping object.
    """
    messages = self.messages_module
    request = messages.RunNamespacesDomainmappingsGetRequest(
        name=domain_mapping_ref.RelativeName()
    )
    with metrics.RecordDuration(metric_names.GET_DOMAIN_MAPPING):
      response = self._client.namespaces_domainmappings.Get(request)
    return domain_mapping.DomainMapping(response, messages)

  def DeployJob(
      self,
      job_ref,
      config_changes,
      release_track,
      tracker=None,
      asyn=False,
      build_image=None,
      build_pack=None,
      build_source=None,
      repo_to_create=None,
      prefetch=None,
      already_activated_services=False,
  ):
    """Deploy to create a new Cloud Run Job or to update an existing one.

    Args:
      job_ref: Resource, the job to create or update.
      config_changes: list, objects that implement Adjust().
      release_track: ReleaseTrack, the release track of a command calling this.
      tracker: StagedProgressTracker, to report on the progress of releasing.
      asyn: bool, if True, return without waiting for the job to be updated.
      build_image: The build image reference to the build.
      build_pack: The build pack reference to the build.
      build_source: The build source reference to the build.
      repo_to_create: Optional
        googlecloudsdk.command_lib.artifacts.docker_util.DockerRepo defining a
        repository to be created.
      prefetch: the job, pre-fetched for DeployJob. `None` indicates a
        nonexistent job so the job has to be created, else this is for an
        update.
      already_activated_services: bool. If true, skip activation prompts for
        services

    Returns:
      A job.Job object.
    """
    if tracker is None:
      tracker = progress_tracker.NoOpStagedProgressTracker(
          stages.JobStages(
              include_build=build_source is not None,
              include_create_repo=repo_to_create is not None,
          ),
          interruptable=True,
          aborted_message='aborted',
      )

    if build_source is not None:
      image_digest, _, _, _, _ = deployer.CreateImage(
          tracker,
          build_image,
          build_source,
          build_pack,
          repo_to_create,
          release_track,
          already_activated_services,
          self._region,
          job_ref,
      )
      if image_digest is None:
        return
      config_changes.append(_AddDigestToImageChange(image_digest))

    is_create = not prefetch
    if is_create:
      return self.CreateJob(job_ref, config_changes, tracker, asyn)
    else:
      return self.UpdateJob(job_ref, config_changes, tracker, asyn)

  def CreateJob(self, job_ref, config_changes, tracker=None, asyn=False):
    """Create a new Cloud Run Job.

    Args:
      job_ref: Resource, the job to create.
      config_changes: list, objects that implement Adjust().
      tracker: StagedProgressTracker, to report on the progress of releasing.
      asyn: bool, if True, return without waiting for the job to be updated.

    Returns:
      A job.Job object.
    """
    messages = self.messages_module
    new_job = job.Job.New(self._client, job_ref.Parent().Name())
    new_job.name = job_ref.Name()
    parent = job_ref.Parent().RelativeName()
    for config_change in config_changes:
      new_job = config_change.Adjust(new_job)
    create_request = messages.RunNamespacesJobsCreateRequest(
        job=new_job.Message(), parent=parent
    )
    created_job = None
    with metrics.RecordDuration(metric_names.CREATE_JOB):
      try:
        created_job = job.Job(
            self._client.namespaces_jobs.Create(create_request), messages
        )
      except api_exceptions.HttpConflictError:
        raise serverless_exceptions.DeploymentFailedError(
            'Job [{}] already exists.'.format(job_ref.Name())
        )
      except api_exceptions.HttpBadRequestError as e:
        exceptions.reraise(serverless_exceptions.HttpError(e))

    if not asyn:
      getter = functools.partial(self.GetJob, job_ref)
      poller = op_pollers.ConditionPoller(getter, tracker)
      self.WaitForCondition(poller)
      created_job = poller.GetResource()

    return created_job

  def UpdateJob(self, job_ref, config_changes, tracker=None, asyn=False):
    """Update an existing Cloud Run Job.

    Args:
      job_ref: Resource, the job to update.
      config_changes: list, objects that implement Adjust().
      tracker: StagedProgressTracker, to report on the progress of updating.
      asyn: bool, if True, return without waiting for the job to be updated.

    Returns:
      A job.Job object.
    """
    messages = self.messages_module
    update_job = self.GetJob(job_ref)
    if update_job is None:
      raise serverless_exceptions.JobNotFoundError(
          'Job [{}] could not be found.'.format(job_ref.Name())
      )
    for config_change in config_changes:
      update_job = config_change.Adjust(update_job)
    replace_request = messages.RunNamespacesJobsReplaceJobRequest(
        job=update_job.Message(), name=job_ref.RelativeName()
    )
    returned_job = None
    with metrics.RecordDuration(metric_names.UPDATE_JOB):
      try:
        returned_job = job.Job(
            self._client.namespaces_jobs.ReplaceJob(replace_request), messages
        )
      except api_exceptions.HttpBadRequestError as e:
        exceptions.reraise(serverless_exceptions.HttpError(e))

    if not asyn:
      getter = functools.partial(self.GetJob, job_ref)
      poller = op_pollers.ConditionPoller(getter, tracker)
      self.WaitForCondition(poller)
      returned_job = poller.GetResource()

    return returned_job

  def RunJob(
      self,
      job_ref,
      tracker=None,
      wait=False,
      asyn=False,
      release_track=None,
      overrides=None,
  ):
    """Run a Cloud Run Job, creating an Execution.

    Args:
      job_ref: Resource, the job to run
      tracker: StagedProgressTracker, to report on the progress of running
      wait: boolean, True to wait until the job is complete
      asyn: bool, if True, return without waiting for anything
      release_track: ReleaseTrack, the release track of a command calling this
      overrides: ExecutionOverrides to be applied for this run of a job

    Returns:
      An Execution Resource in its state when RunJob returns.
    """
    messages = self.messages_module
    run_job_request = messages.RunJobRequest()
    if overrides:
      run_job_request.overrides = overrides
    run_request = messages.RunNamespacesJobsRunRequest(
        name=job_ref.RelativeName(), runJobRequest=run_job_request
    )
    with metrics.RecordDuration(metric_names.RUN_JOB):
      try:
        execution_message = self._client.namespaces_jobs.Run(run_request)
      except api_exceptions.HttpError as e:
        if e.status_code == 429:  # resource exhausted
          raise serverless_exceptions.DeploymentFailedError(
              'Resource exhausted error. This may mean that '
              'too many executions are already running. Please wait until one '
              'completes before creating a new one.'
          )
        raise e
    if asyn:
      return execution.Execution(execution_message, messages)

    execution_ref = self._registry.Parse(
        execution_message.metadata.name,
        params={'namespacesId': execution_message.metadata.namespace},
        collection='run.namespaces.executions',
    )
    getter = functools.partial(self.GetExecution, execution_ref)
    terminal_condition = (
        execution.COMPLETED_CONDITION if wait else execution.STARTED_CONDITION
    )
    ex = self.GetExecution(execution_ref)
    for msg in run_condition.GetNonTerminalMessages(
        ex.conditions, ignore_retry=True
    ):
      tracker.AddWarning(msg)
    poller = op_pollers.ExecutionConditionPoller(
        getter,
        tracker,
        terminal_condition,
        dependencies=stages.ExecutionDependencies(),
    )
    try:
      self.WaitForCondition(poller, None if wait else 0)
    except serverless_exceptions.ExecutionFailedError:
      raise serverless_exceptions.ExecutionFailedError(
          'The execution failed.'
          + messages_util.GetExecutionCreatedMessage(release_track, ex)
      )
    return self.GetExecution(execution_ref)

  def GetJob(self, job_ref):
    """Return the relevant Job from the server, or None if 404."""
    messages = self.messages_module
    get_request = messages.RunNamespacesJobsGetRequest(
        name=job_ref.RelativeName()
    )

    try:
      with metrics.RecordDuration(metric_names.GET_JOB):
        job_response = self._client.namespaces_jobs.Get(get_request)
        return job.Job(job_response, messages)
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)
    except api_exceptions.HttpNotFoundError:
      return None

  def GetTask(self, task_ref):
    """Return the relevant Task from the server, or None if 404."""
    messages = self.messages_module
    get_request = messages.RunNamespacesTasksGetRequest(
        name=task_ref.RelativeName()
    )

    try:
      with metrics.RecordDuration(metric_names.GET_TASK):
        task_response = self._client.namespaces_tasks.Get(get_request)
        return task.Task(task_response, messages)
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)
    except api_exceptions.HttpNotFoundError:
      return None

  def GetExecution(self, execution_ref):
    """Return the relevant Execution from the server, or None if 404."""
    messages = self.messages_module
    get_request = messages.RunNamespacesExecutionsGetRequest(
        name=execution_ref.RelativeName()
    )

    try:
      with metrics.RecordDuration(metric_names.GET_EXECUTION):
        execution_response = self._client.namespaces_executions.Get(get_request)
        return execution.Execution(execution_response, messages)
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)
    except api_exceptions.HttpNotFoundError:
      return None

  def ListJobs(self, namespace_ref):
    """Returns all jobs in the namespace."""
    messages = self.messages_module
    request = messages.RunNamespacesJobsListRequest(
        parent=namespace_ref.RelativeName()
    )
    try:
      with metrics.RecordDuration(metric_names.LIST_JOBS):
        response = self._client.namespaces_jobs.List(request)
        return [job.Job(item, messages) for item in response.items]
    except api_exceptions.InvalidDataFromServerError as e:
      serverless_exceptions.MaybeRaiseCustomFieldMismatch(e)

  def DeleteJob(self, job_ref):
    """Delete the provided Job.

    Args:
      job_ref: Resource, a reference to the Job to delete

    Raises:
      JobNotFoundError: if provided job is not found.
    """
    messages = self.messages_module
    request = messages.RunNamespacesJobsDeleteRequest(
        name=job_ref.RelativeName()
    )
    try:
      with metrics.RecordDuration(metric_names.DELETE_JOB):
        self._client.namespaces_jobs.Delete(request)
    except api_exceptions.HttpNotFoundError:
      raise serverless_exceptions.JobNotFoundError(
          'Job [{}] could not be found.'.format(job_ref.Name())
      )

  def DeleteExecution(self, execution_ref):
    """Delete the provided Execution.

    Args:
      execution_ref: Resource, a reference to the Execution to delete

    Raises:
      ExecutionNotFoundError: if provided Execution is not found.
    """
    messages = self.messages_module
    request = messages.RunNamespacesExecutionsDeleteRequest(
        name=execution_ref.RelativeName()
    )
    try:
      with metrics.RecordDuration(metric_names.DELETE_EXECUTION):
        self._client.namespaces_executions.Delete(request)
    except api_exceptions.HttpNotFoundError:
      raise serverless_exceptions.ExecutionNotFoundError(
          'Execution [{}] could not be found.'.format(execution_ref.Name())
      )

  def CancelExecution(self, execution_ref):
    """Cancel the provided Execution.

    Args:
      execution_ref: Resource, a reference to the Execution to cancel

    Raises:
      ExecutionNotFoundError: if provided Execution is not found.
    """
    messages = self.messages_module
    request = messages.RunNamespacesExecutionsCancelRequest(
        name=execution_ref.RelativeName()
    )
    try:
      with metrics.RecordDuration(metric_names.CANCEL_EXECUTION):
        self._client.namespaces_executions.Cancel(request)
    except api_exceptions.HttpNotFoundError:
      raise serverless_exceptions.ExecutionNotFoundError(
          'Execution [{}] could not be found.'.format(execution_ref.Name())
      )

  def _GetIamPolicy(self, service_name):
    """Gets the IAM policy for the service."""
    messages = self.messages_module
    request = messages.RunProjectsLocationsServicesGetIamPolicyRequest(
        resource=six.text_type(service_name)
    )
    response = self._op_client.projects_locations_services.GetIamPolicy(request)
    return response

  def AddOrRemoveIamPolicyBinding(
      self,
      service_ref,
      add_binding=True,
      member=None,
      role=None,
      region_override=None,
  ):
    """Add or remove the given IAM policy binding to the provided service.

    If no members or role are provided, set the IAM policy to the current IAM
    policy. This is useful for checking whether the authenticated user has
    the appropriate permissions for setting policies.

    Args:
      service_ref: str, The service to which to add the IAM policy.
      add_binding: bool, Whether to add to or remove from the IAM policy.
      member: str, One of the users for which the binding applies.
      role: str, The role to grant the provided members.
      region_override: str, The region to use instead of the configured region.

    Returns:
      A google.iam.v1.TestIamPermissionsResponse.
    """
    messages = self.messages_module
    region = region_override or self._region
    oneplatform_service = resource_name_conversion.K8sToOnePlatform(
        service_ref, region
    )
    policy = self._GetIamPolicy(oneplatform_service)
    # Don't modify bindings if not member or roles provided
    if member and role:
      if add_binding:
        iam_util.AddBindingToIamPolicy(messages.Binding, policy, member, role)
      elif iam_util.BindingInPolicy(policy, member, role):
        iam_util.RemoveBindingFromIamPolicy(policy, member, role)
    request = messages.RunProjectsLocationsServicesSetIamPolicyRequest(
        resource=six.text_type(oneplatform_service),
        setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy),
    )
    result = self._op_client.projects_locations_services.SetIamPolicy(request)
    return result

  def CanSetIamPolicyBinding(self, service_ref, region_override=None):
    """Check if user has permission to set the iam policy on the service."""
    messages = self.messages_module
    region = region_override or self._region
    oneplatform_service = resource_name_conversion.K8sToOnePlatform(
        service_ref, region
    )
    request = messages.RunProjectsLocationsServicesTestIamPermissionsRequest(
        resource=six.text_type(oneplatform_service),
        testIamPermissionsRequest=messages.TestIamPermissionsRequest(
            permissions=NEEDED_IAM_PERMISSIONS
        ),
    )
    response = self._client.projects_locations_services.TestIamPermissions(
        request
    )
    return set(NEEDED_IAM_PERMISSIONS).issubset(set(response.permissions))

  def _ValidateService(self, service_ref, config_changes):
    """Validates starting service operation with provided config."""
    serv = self.GetService(service_ref)
    fake_validation_image = _AddDigestToImageChange(FAKE_IMAGE_DIGEST)
    config_changes.append(fake_validation_image)
    self._UpdateOrCreateService(
        service_ref, config_changes, with_code=True, serv=serv, dry_run=True
    )
    config_changes.pop()

  def _ClearRunFunctionsAnnotations(self, config_changes):
    """Clear run functions annotations to the service before setting them."""
    config_changes.append(
        config_changes_mod.DeleteAnnotationChange(
            service.RUN_FUNCTIONS_SOURCE_LOCATION_ANNOTATION_DEPRECATED
        )
    )
    config_changes.append(
        config_changes_mod.DeleteAnnotationChange(
            service.RUN_FUNCTIONS_FUNCTION_TARGET_ANNOTATION_DEPRECATED
        )
    )
    config_changes.append(
        config_changes_mod.DeleteAnnotationChange(
            service.RUN_FUNCTIONS_IMAGE_URI_ANNOTATION_DEPRECATED
        )
    )
    config_changes.append(
        config_changes_mod.DeleteAnnotationChange(
            service.RUN_FUNCTIONS_ENABLE_AUTOMATIC_UPDATES_DEPRECATED
        )
    )

  def _AddRunFunctionsAnnotations(
      self,
      config_changes,
      uploaded_source,
      service_account,
      worker_pool,
      build_env_vars,
      build_pack,
      build_id,
      build_image,
      build_name,
      build_base_image,
      build_from_source_container_name,
      enable_automatic_updates: bool,
  ):
    """Add run functions annotations to the service."""
    build_env_vars_str = json.dumps(build_env_vars) if build_env_vars else None
    function_target = self._GetFunctionTargetFromBuildPack(build_pack)
    source_path = None
    if uploaded_source:
      source_path = sources.GetGsutilUri(uploaded_source)
    image_uri = build_pack[0].get('image') if build_pack else build_image
    annotations_map = {
        service.RUN_FUNCTIONS_BUILD_SERVICE_ACCOUNT_ANNOTATION: service_account,
        service.RUN_FUNCTIONS_BUILD_WORKER_POOL_ANNOTATION: worker_pool,
        service.RUN_FUNCTIONS_BUILD_ENV_VARS_ANNOTATION: build_env_vars_str,
        service.RUN_FUNCTIONS_BUILD_ID_ANNOTATION: build_id,
        service.RUN_FUNCTIONS_BUILD_NAME_ANNOTATION: build_name,
        service.RUN_FUNCTIONS_BUILD_IMAGE_URI_ANNOTATION: image_uri,
        service.RUN_FUNCTIONS_BUILD_SOURCE_LOCATION_ANNOTATION: source_path,
        service.RUN_FUNCTIONS_BUILD_FUNCTION_TARGET_ANNOTATION: function_target,
        service.RUN_FUNCTIONS_BUILD_ENABLE_AUTOMATIC_UPDATES: (
            'true' if enable_automatic_updates else 'false'
        ),
    }

    if enable_automatic_updates:
      self._ReplaceOrAddBaseImage(
          config_changes,
          build_base_image,
          build_from_source_container_name,
      )
    else:
      self._DeleteRevisionBaseImageAnnotation(
          config_changes, build_from_source_container_name
      )

    config_changes.extend(
        config_changes_mod.SetAnnotationChange(k, v)
        for k, v in annotations_map.items()
        if v is not None
    )
    if build_base_image:
      config_changes.append(
          config_changes_mod.SetAnnotationChange(
              service.RUN_FUNCTIONS_BUILD_BASE_IMAGE, build_base_image
          )
      )
    else:
      config_changes.append(
          config_changes_mod.DeleteAnnotationChange(
              service.RUN_FUNCTIONS_BUILD_BASE_IMAGE
          )
      )

  def ValidateConfigOverrides(self, job_ref, config_changes):
    """Apply config changes to Job resource to validate.

    This is to replicate the same validation logic in `jobs/services update`.
    Override attempts with types (out of string literals, secrets,
    config maps) that are different from currently set value type will appear as
    errors in the console.

    Args:
      job_ref: Resource, job resource.
      config_changes: Job configuration changes from Overrides
    """
    run_job = self.GetJob(job_ref)
    for change in config_changes:
      run_job = change.Adjust(run_job)

  def GetExecutionOverrides(
      self, tasks, task_timeout, priority_tier, container_overrides
  ):
    return self.messages_module.Overrides(
        containerOverrides=container_overrides,
        taskCount=tasks,
        timeoutSeconds=task_timeout,
        priorityTier=self.messages_module.Overrides.PriorityTierValueValuesEnum(
            priority_tier.upper()
        ),
    )

  def MakeContainerOverride(self, name, update_env_vars, args, clear_args):
    return self.messages_module.ContainerOverride(
        name=name,
        args=args or [],
        env=self._GetEnvVarList(update_env_vars),
        clearArgs=clear_args,
    )

  def _GetEnvVarList(self, env_vars):
    env_var_list = []
    if env_vars is not None:
      for name, value in env_vars.items():
        env_var_list.append(self.messages_module.EnvVar(name=name, value=value))
    return env_var_list
