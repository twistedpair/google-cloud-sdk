# -*- coding: utf-8 -*- #
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Allows you to write surfaces in terms of logical Serverless operations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections
import contextlib
import copy
import functools
import glob
import os
import random
import string
from apitools.base.py import exceptions as api_exceptions
from googlecloudsdk.api_lib.run import build_template
from googlecloudsdk.api_lib.run import configuration
from googlecloudsdk.api_lib.run import domain_mapping
from googlecloudsdk.api_lib.run import k8s_object
from googlecloudsdk.api_lib.run import metrics
from googlecloudsdk.api_lib.run import revision
from googlecloudsdk.api_lib.run import route
from googlecloudsdk.api_lib.run import service
from googlecloudsdk.api_lib.util import apis_internal
from googlecloudsdk.api_lib.util import exceptions as exceptions_util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.command_lib.run import config_changes as config_changes_mod
from googlecloudsdk.command_lib.run import deployable as deployable_pkg
from googlecloudsdk.command_lib.run import exceptions as serverless_exceptions
from googlecloudsdk.command_lib.run import pretty_print
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.util import retry

DEFAULT_ENDPOINT_VERSION = 'v1'


_NONCE_LENGTH = 10
# Used to force a new revision, and also to tie a particular request for changes
# to a particular created revision.
NONCE_LABEL = 'client.knative.dev/nonce'

# Wait 11 mins for each deployment. This is longer than the server timeout,
# making it more likely to get a useful error message from the server.
MAX_WAIT_MS = 660000


class UnknownAPIError(exceptions.Error):
  pass


# Because some terminals cannot update multiple lines of output simultaneously,
# the order of conditions in this dictionary should match the order in which we
# expect cloud run resources to complete deployment.
def _ServiceStages():
  """Return a new mapping from conditions to Stages."""
  return collections.OrderedDict([
      ('ConfigurationsReady', progress_tracker.Stage(
          'Creating Revision...')),
      ('RoutesReady', progress_tracker.Stage('Routing traffic...'))])


@contextlib.contextmanager
def Connect(conn_context):
  """Provide a ServerlessOperations instance to use.

  If we're using the GKE Serverless Add-on, connect to the relevant cluster.
  Otherwise, connect to the right region of GSE.

  Arguments:
    conn_context: a context manager that yields a ConnectionInfo and manages a
      dynamic context that makes connecting to serverless possible.

  Yields:
    A ServerlessOperations instance.
  """
  with conn_context as conn_info:
    yield ServerlessOperations(
        apis_internal._GetClientInstance(  # pylint: disable=protected-access
            conn_info.api_name, conn_info.api_version,
            ca_certs=conn_info.ca_certs),
        conn_info.api_name, conn_info.api_version)


class ConditionPoller(waiter.OperationPoller):
  """A poller for serverless deployment.

  Takes in a reference to a StagedProgressTracker, and updates it with progress.
  """

  def __init__(self, resource_getter, tracker, stages, dependencies=None):
    """Initialize the ConditionPoller.

    Start any unblocked stages in the tracker immediately.

    Arguments:
      resource_getter: function, returns a resource with conditions.
      tracker: a StagedProgressTracker to keep updated
      stages: List[Stage], the stages in the tracker
      dependencies: Dict[str, Set[str]], The dependencies between conditions.
        The condition represented by each key can only start when the set of
        conditions in the corresponding value have all completed.
    """
    # _dependencies is a map of condition -> {preceding conditions}
    # It is meant to be checked off as we finish things.
    self._dependencies = copy.deepcopy(dependencies) if dependencies else {}
    self._stages = stages
    self._resource_getter = resource_getter
    self._tracker = tracker
    self._completed_stages = set()
    self._started_stages = set()
    self._failed_stages = set()
    self._StartUnblocked()

  def _IsBlocked(self, condition):
    return condition in self._dependencies

  def IsDone(self, conditions):
    """Overrides.

    Args:
      conditions: A condition.Conditions object.

    Returns:
      a bool indicates whether `conditions` is terminal.
    """
    if conditions is None:
      return False
    return conditions.IsTerminal()

  def Poll(self, unused_ref):
    """Overrides.

    Args:
      unused_ref: A string representing the operation reference. Currently it
        must be 'deploy'.

    Returns:
      A condition.Conditions object.
    """
    conditions = self.GetConditions()

    if conditions is None or not conditions.IsFresh():
      return None

    ready_message = conditions.DescriptiveMessage()
    if ready_message:
      self._tracker.UpdateHeaderMessage(ready_message)

    for condition in conditions.TerminalSubconditions():
      message = conditions[condition]['message']
      status = conditions[condition]['status']
      self._PossiblyUpdateMessage(condition, message, ready_message)
      if status is None:
        continue
      elif status:
        self._PossiblyCompleteStage(condition, message, conditions.IsReady())
      else:
        self._PossiblyFailStage(condition, message)

    if conditions.IsReady():
      self._tracker.UpdateHeaderMessage('Done.')
      # TODO(b/120679874): Should not have to manually call Tick()
      self._tracker.Tick()
    elif conditions.IsFailed():
      raise serverless_exceptions.DeploymentFailedError(ready_message)

    return conditions

  def _PossiblyUpdateMessage(self, condition, message, ready_message):
    """Update the stage message.

    Args:
      condition: str, The name of the status condition.
      message: str, The new message to display
      ready_message: str, The ready message we're displaying.
    """
    if condition in self._completed_stages or not message:
      return

    if self._IsBlocked(condition):
      return

    if message != ready_message:
      self._tracker.UpdateStage(self._stages[condition], message)

  def _RecordStageComplete(self, condition):
    """Take care of the internal-to-this-class bookkeeping stage complete."""
    self._completed_stages.add(condition)
    # Unblock anything that was blocked on this.
    unblocked = []
    # Strategy: "check off" each dependency as we complete it by removing from
    # the set in the value. When the set of dependencies is empty, remove the
    # entry from the dict.
    for other_condition, requirements in self._dependencies.items():
      requirements.discard(condition)
      if not requirements:
        unblocked.append(other_condition)
    for other_condition in unblocked:
      del self._dependencies[other_condition]

  def _PossiblyCompleteStage(self, condition, message, ready):
    """Complete the stage if it's not already complete.

    Make sure the necessary internal bookkeeping is done.

    Args:
      condition: str, The name of the condition whose stage should be completed.
      message: str, The detailed message for the condition.
      ready: boolean, True if the Ready condition is true.
    """
    if condition in self._completed_stages:
      return
    # A blocked condition is likely to remain True (indicating the previous
    # operation concerning it was successful) until the blocking condition(s)
    # finish and it's time to switch to Unknown (the current operation
    # concerning it is in progress). Don't mark those done before they switch to
    # Unknown.
    if condition not in self._started_stages:
      return
    self._RecordStageComplete(condition)
    self._StartUnblocked()
    self._tracker.CompleteStage(self._stages[condition], message)

  def _StartUnblocked(self):

    """Call StartStage in the tracker for any not-started not-blocked tasks.

    Record the fact that they're started in our internal bookkeeping.
    """
    # The set of stages that aren't marked started and don't have unsatisfied
    # dependencies are "newly unblocked".
    newly_unblocked = (set(self._stages.keys())
                       - self._started_stages - set(self._dependencies.keys()))
    for unblocked in newly_unblocked:
      self._started_stages.add(unblocked)
      self._tracker.StartStage(self._stages[unblocked])
    # TODO(b/120679874): Should not have to manually call Tick()
    self._tracker.Tick()

  def _PossiblyFailStage(self, condition, message):
    """Possibly fail the stage.

    Args:
      condition: str, The name of the status whose stage failed.
      message: str, The detailed message for the condition.

    Raises:
      DeploymentFailedError: If the 'Ready' condition failed.
    """
    # Don't fail an already failed stage.
    if condition in self._failed_stages:
      return

    stage = self._stages[condition]
    self._failed_stages.add(condition)
    self._tracker.FailStage(
        stage,
        serverless_exceptions.DeploymentFailedError(message),
        message)

  def GetResult(self, conditions):
    """Overrides.

    Get terminal conditions as the polling result.

    Args:
      conditions: A condition.Conditions object.

    Returns:
      A condition.Conditions object.
    """
    return conditions

  def GetConditions(self):
    """Returns the resource conditions wrapped in condition.Conditions.

    Returns:
      A condition.Conditions object.
    """
    resource = self._resource_getter()
    if resource is None:
      return None
    return resource.conditions


def _Nonce():
  """Return a random string with unlikely collision to use as a nonce."""
  return ''.join(
      random.choice(string.ascii_lowercase) for _ in range(_NONCE_LENGTH))


class _NewRevisionForcingChange(config_changes_mod.ConfigChanger):
  """Forces a new revision to get created by posting a random nonce label."""

  def __init__(self, nonce):
    self._nonce = nonce

  def AdjustConfiguration(self, config, metadata):
    del metadata
    config.revision_labels[NONCE_LABEL] = self._nonce


def _IsDigest(url):
  """Return true if the given image url is by-digest."""
  return '@sha256:' in url


class NonceBasedRevisionPoller(waiter.OperationPoller):
  """To poll for exactly one revision with the given nonce to appear."""

  def __init__(self, operations, namespace_ref):
    self._operations = operations
    self._namespace = namespace_ref

  def IsDone(self, revisions):
    return bool(revisions)

  def Poll(self, nonce):
    return self._operations.GetRevisionsByNonce(self._namespace, nonce)

  def GetResult(self, revisions):
    if len(revisions) == 1:
      return revisions[0]
    return None


class _SwitchToDigestChange(config_changes_mod.ConfigChanger):
  """Switches the configuration from by-tag to by-digest."""

  def __init__(self, base_revision):
    self._base_revision = base_revision

  def AdjustConfiguration(self, config, metadata):
    if _IsDigest(self._base_revision.image):
      return
    if not self._base_revision.image_digest:
      return

    annotations = k8s_object.AnnotationsFromMetadata(
        config.MessagesModule(), metadata)
    # Mutates through to metadata: Save the by-tag user intent.
    annotations[configuration.USER_IMAGE_ANNOTATION] = self._base_revision.image
    config.image = self._base_revision.image_digest


class ServerlessOperations(object):
  """Client used by Serverless to communicate with the actual Serverless API.
  """

  def __init__(self, client, api_name, api_version):
    self._client = client
    self._registry = resources.REGISTRY.Clone()
    self._registry.RegisterApiByName(api_name, api_version)
    self._temporary_build_template_registry = {}

  @property
  def _messages_module(self):
    return self._client.MESSAGES_MODULE

  def IsSourceBranch(self):
    # TODO(b/112662240): Remove once the build field is public
    return hasattr(self._client.MESSAGES_MODULE.ConfigurationSpec, 'build')

  # For internal-only source testing. Codepaths inaccessable except on
  # build from dev branch.
  # TODO(b/112662240): productionalize when source is landing
  def _TemporaryBuildTemplateRegistry(self, namespace_ref):
    """Return the list of build templates available, mocking the server."""
    if namespace_ref.RelativeName() in self._temporary_build_template_registry:
      return self._temporary_build_template_registry[
          namespace_ref.RelativeName()]

    detect = build_template.BuildTemplate.New(
        self._client, 'default')
    detect.name = 'detect'
    detect.annotations[build_template.IGNORE_GLOB_ANNOTATION] = (
        '["/*", "!package.json","!Pipfile.lock"]')

    nodejs_8_9_4 = build_template.BuildTemplate.New(
        self._client, 'default')
    nodejs_8_9_4.name = 'nodejs_8_9_4'
    nodejs_8_9_4.annotations[build_template.IGNORE_GLOB_ANNOTATION] = (
        '["node_modules/"]')
    nodejs_8_9_4.labels[build_template.LANGUAGE_LABEL] = 'nodejs'
    nodejs_8_9_4.labels[build_template.VERSION_LABEL] = '8.9.4'
    nodejs_8_9_4.annotations[build_template.DEV_IMAGE_ANNOTATION] = (
        'gcr.io/local-run-demo/nodejs_dev:latest')

    go_1_10_1 = build_template.BuildTemplate.New(
        self._client, 'default')
    go_1_10_1.name = 'go_1_10_1'
    go_1_10_1.labels[build_template.LANGUAGE_LABEL] = 'go'
    go_1_10_1.labels[build_template.VERSION_LABEL] = '1.10.1'
    lst = [detect, nodejs_8_9_4, go_1_10_1]
    self._temporary_build_template_registry[namespace_ref.RelativeName()] = lst
    return lst

  def Detect(self, namespace_ref, source_ref, function_entrypoint=None):
    """Detects important properties and returns a Deployable.

    Args:
      namespace_ref: str, the namespace to look for build templates in
      source_ref: source_ref.SourceRef, refers to some source code
      function_entrypoint: str, allows you to specify this is a function, and
                           the function to run.

    Returns:
      a new Deployable referring to the source
    """
    template = self._DetectBuildTemplate(namespace_ref, source_ref)

    if (source_ref.source_type == source_ref.SourceType.IMAGE
        and not template and not function_entrypoint):
      return deployable_pkg.ServerlessContainer(source_ref)

    if not self.IsSourceBranch():
      raise serverless_exceptions.UnknownDeployableError()
    # TODO(b/112662240): Put at top when source lands.
    from googlecloudsdk.command_lib.run import source_deployable  # pylint: disable=g-import-not-at-top
    if (function_entrypoint and
        template and
        source_ref.source_type == source_ref.SourceType.DIRECTORY):
      return source_deployable.ServerlessFunction(source_ref, template,
                                                  function_entrypoint)

    if (source_ref.source_type == source_ref.SourceType.DIRECTORY and
        template and
        not function_entrypoint):
      return source_deployable.ServerlessApp(source_ref, template)

    raise serverless_exceptions.UnknownDeployableError()

  def GetRevision(self, revision_ref):
    """Get the revision.

    Args:
      revision_ref: Resource, revision to get.

    Returns:
      A revision.Revision object.
    """
    messages = self._messages_module
    revision_name = revision_ref.RelativeName()
    request = messages.ServerlessNamespacesRevisionsGetRequest(
        name=revision_name)
    try:
      with metrics.record_duration(metrics.GET_REVISION):
        response = self._client.namespaces_revisions.Get(request)
      return revision.Revision(response, messages)
    except api_exceptions.HttpNotFoundError:
      return None

  def Upload(self, deployable):
    """Upload the code for the given deployable."""
    deployable.UploadFiles()

  def _GetRoute(self, service_ref):
    """Return the relevant Route from the server, or None if 404."""
    messages = self._messages_module
    # GET the Route
    route_name = self._registry.Parse(
        service_ref.servicesId,
        params={
            'namespacesId': service_ref.namespacesId,
        },
        collection='serverless.namespaces.routes').RelativeName()
    route_get_request = messages.ServerlessNamespacesRoutesGetRequest(
        name=route_name,
    )

    try:
      with metrics.record_duration(metrics.GET_ROUTE):
        route_get_response = self._client.namespaces_routes.Get(
            route_get_request)
      return route.Route(route_get_response, messages)
    except api_exceptions.HttpNotFoundError:
      return None

  def _GetBuildTemplateByName(self, namespace_ref, name):
    """Return the BuildTemplate with the given name, or None."""
    # Implementation to be replaced once the concept exists on the server.
    for templ in self._TemporaryBuildTemplateRegistry(namespace_ref):
      if templ.name == name:
        return templ
    return None

  def _GetBuildTemplateByLanguageVersion(self, namespace_ref,
                                         language, version):
    """Return the BuildTemplate with the given language & version, or None."""
    # Implementation to be replaced once the concept exists on the server.
    del namespace_ref
    for templ in self._temporary_build_template_registry:
      if (templ.language, templ.version) == (language, version):
        return templ
    return None

  def WaitForCondition(self, getter):
    """Wait for a configuration to be ready in latest revision."""
    stages = _ServiceStages()
    with progress_tracker.StagedProgressTracker(
        'Deploying...',
        stages.values(),
        failure_message='Deployment failed') as tracker:
      config_poller = ConditionPoller(getter, tracker, stages, dependencies={
          'RoutesReady': {'ConfigurationsReady'},
      })
      try:
        conditions = waiter.PollUntilDone(
            config_poller, None,
            wait_ceiling_ms=1000)
      except retry.RetryException as err:
        conditions = config_poller.GetConditions()
        # err.message already indicates timeout. Check ready_cond_type for more
        # information.
        msg = conditions.DescriptiveMessage() if conditions else None
        if msg:
          log.error('Still waiting: {}'.format(msg))
        raise err
      if not conditions.IsReady():
        raise serverless_exceptions.ConfigurationError(
            conditions.DescriptiveMessage())

  def GetServiceUrl(self, service_ref):
    """Return the main URL for the service."""
    serv = self.GetService(service_ref)
    if serv.domain:
      return serv.domain
    # Older versions of knative don't populate domain on Service, only Route.
    serv_route = self._GetRoute(service_ref)
    return serv_route.domain

  def GetActiveRevisions(self, service_ref):
    """Return the actively serving revisions.

    Args:
      service_ref: the service Resource reference.

    Returns:
      {str, int}, A dict mapping revisionID to its traffic percentage target.

    Raises:
      serverless_exceptions.NoActiveRevisionsError: if no serving revisions
        were found.
    """
    serv_route = self._GetRoute(service_ref)
    active_revisions = serv_route.active_revisions

    if len(active_revisions) < 1:
      raise serverless_exceptions.NoActiveRevisionsError()

    return serv_route.active_revisions

  def _DetectBuildTemplate(self, namespace_ref, source_ref):
    """Determine the appropriate build template from source.

    Args:
      namespace_ref: Resource, namespace to find build templates in.
      source_ref: SourceRef, The service's image repo or source directory.

    Returns:
      The detected build template name.
    """
    if source_ref.source_type == source_ref.SourceType.IMAGE:
      return None
    elif glob.glob(os.path.join(source_ref.source_path, '*.go')):
      return self._GetBuildTemplateByName(namespace_ref, 'go_1_10_1')
    else:
      return self._GetBuildTemplateByName(namespace_ref, 'nodejs_8_9_4')

  def ListServices(self, namespace_ref):
    messages = self._messages_module
    request = messages.ServerlessNamespacesServicesListRequest(
        parent=namespace_ref.RelativeName())
    with metrics.record_duration(metrics.LIST_SERVICES):
      response = self._client.namespaces_services.List(request)
    return [service.Service(item, messages) for item in response.items]

  def ListConfigurations(self, namespace_ref):
    messages = self._messages_module
    request = messages.ServerlessNamespacesConfigurationsListRequest(
        parent=namespace_ref.RelativeName())
    with metrics.record_duration(metrics.LIST_CONFIGURATIONS):
      response = self._client.namespaces_configurations.List(request)
    return [configuration.Configuration(item, messages)
            for item in response.items]

  def ListRoutes(self, namespace_ref):
    messages = self._messages_module
    request = messages.ServerlessNamespacesRoutesListRequest(
        parent=namespace_ref.RelativeName())
    with metrics.record_duration(metrics.LIST_ROUTES):
      response = self._client.namespaces_routes.List(request)
    return [route.Route(item, messages) for item in response.items]

  def GetService(self, service_ref):
    """Return the relevant Service from the server, or None if 404."""
    messages = self._messages_module
    service_get_request = messages.ServerlessNamespacesServicesGetRequest(
        name=service_ref.RelativeName())

    try:
      with metrics.record_duration(metrics.GET_SERVICE):
        service_get_response = self._client.namespaces_services.Get(
            service_get_request)
      return service.Service(service_get_response, messages)
    except api_exceptions.HttpNotFoundError:
      return None

  def GetConfiguration(self, service_or_configuration_ref):
    """Return the relevant Configuration from the server, or None if 404."""
    messages = self._messages_module
    if hasattr(service_or_configuration_ref, 'servicesId'):
      name = self._registry.Parse(
          service_or_configuration_ref.servicesId,
          params={
              'namespacesId': service_or_configuration_ref.namespacesId,
          },
          collection='serverless.namespaces.configurations').RelativeName()
    else:
      name = service_or_configuration_ref.RelativeName()
    configuration_get_request = (
        messages.ServerlessNamespacesConfigurationsGetRequest(
            name=name))

    try:
      with metrics.record_duration(metrics.GET_CONFIGURATION):
        configuration_get_response = self._client.namespaces_configurations.Get(
            configuration_get_request)
      return configuration.Configuration(configuration_get_response, messages)
    except api_exceptions.HttpNotFoundError:
      return None

  def GetRoute(self, service_or_route_ref):
    """Return the relevant Route from the server, or None if 404."""
    messages = self._messages_module
    if hasattr(service_or_route_ref, 'servicesId'):
      name = self._registry.Parse(
          service_or_route_ref.servicesId,
          params={
              'namespacesId': service_or_route_ref.namespacesId,
          },
          collection='serverless.namespaces.routes').RelativeName()
    else:
      name = service_or_route_ref.RelativeName()
    route_get_request = (
        messages.ServerlessNamespacesRoutesGetRequest(
            name=name))

    try:
      with metrics.record_duration(metrics.GET_ROUTE):
        route_get_response = self._client.namespaces_routes.Get(
            route_get_request)
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
    messages = self._messages_module
    service_name = service_ref.RelativeName()
    service_delete_request = messages.ServerlessNamespacesServicesDeleteRequest(
        name=service_name,
    )

    try:
      with metrics.record_duration(metrics.DELETE_SERVICE):
        self._client.namespaces_services.Delete(service_delete_request)
    except api_exceptions.HttpNotFoundError:
      raise serverless_exceptions.ServiceNotFoundError(
          'Service [{}] could not be found.'.format(service_ref.servicesId))

  def DeleteRevision(self, revision_ref):
    """Delete the provided Revision.

    Args:
      revision_ref: Resource, a reference to the Revision to delete

    Raises:
      RevisionNotFoundError: if provided revision is not found.
    """
    messages = self._messages_module
    revision_name = revision_ref.RelativeName()
    request = messages.ServerlessNamespacesRevisionsDeleteRequest(
        name=revision_name)
    try:
      with metrics.record_duration(metrics.DELETE_REVISION):
        self._client.namespaces_revisions.Delete(request)
    except api_exceptions.HttpNotFoundError:
      raise serverless_exceptions.RevisionNotFoundError(
          'Revision [{}] could not be found.'.format(revision_ref.revisionsId))

  def GetRevisionsByNonce(self, namespace_ref, nonce):
    """Return all revisions with the given nonce."""
    messages = self._messages_module
    request = messages.ServerlessNamespacesRevisionsListRequest(
        parent=namespace_ref.RelativeName(),
        labelSelector='{} = {}'.format(NONCE_LABEL, nonce))
    response = self._client.namespaces_revisions.List(request)
    return [revision.Revision(item, messages) for item in response.items]

  def _GetBaseRevision(self, config, metadata, status):
    """Return a Revision for use as the "base revision" for a change.

    When making a change that should not affect the code running, the
    "base revision" is the revision that we should lock the code to - it's where
    we get the digest for the image to run.

    Getting this revision:
      * If there's a nonce in the revisonTemplate metadata, use that
      * If that query produces >1 or produces 0 after a short timeout, use
        the latestCreatedRevision in status.

    Arguments:
      config: Configuration, the configuration to get the base revision of.
        May have been derived from a Service.
      metadata: ObjectMeta, the metadata from the top-level object
      status: Union[ConfigurationStatus, ServiceStatus], the status of the top-
        level object.

    Returns:
      The base revision of the configuration.
    """
    # Or returns None if not available by nonce & the control plane has not
    # implemented latestCreatedRevisionName on the Service object yet.
    base_revision_nonce = config.revision_labels.get(NONCE_LABEL, None)
    base_revision = None
    if base_revision_nonce:
      try:
        namespace_ref = self._registry.Parse(
            metadata.namespace,
            collection='serverless.namespaces')
        poller = NonceBasedRevisionPoller(self, namespace_ref)
        base_revision = poller.GetResult(waiter.PollUntilDone(
            poller, base_revision_nonce,
            sleep_ms=500, max_wait_ms=2000))
      except retry.WaitException:
        pass
    # Nonce polling didn't work, because some client didn't post one or didn't
    # change one. Fall back to the (slightly racy) `latestCreatedRevisionName`.
    if not base_revision:
      # TODO(b/117663680) Getattr -> normal access.
      if getattr(status, 'latestCreatedRevisionName', None):
        # Get by latestCreatedRevisionName
        revision_ref = self._registry.Parse(
            status.latestCreatedRevisionName,
            params={'namespacesId': metadata.namespace},
            collection='serverless.namespaces.revisions')
        base_revision = self.GetRevision(revision_ref)
    return base_revision

  def _EnsureImageDigest(self, serv, config_changes):
    """Make config_changes include switch by-digest image if not so already."""
    if not _IsDigest(serv.configuration.image):
      base_revision = self._GetBaseRevision(
          serv.configuration, serv.metadata, serv.status)
      if base_revision:
        config_changes.append(_SwitchToDigestChange(base_revision))

  def _UpdateOrCreateService(self, service_ref, config_changes, with_code):
    """Apply config_changes to the service. Create it if necessary.

    Arguments:
      service_ref: Reference to the service to create or update
      config_changes: list of ConfigChanger to modify the service with
      with_code: boolean, True if the config_changes contains code to deploy.
        We can't create the service if we're not deploying code.

    Returns:
      The Service object we created or modified.
    """
    nonce = _Nonce()
    config_changes = [_NewRevisionForcingChange(nonce)] + config_changes
    messages = self._messages_module
    # GET the Service
    serv = self.GetService(service_ref)
    try:
      if serv:
        if not with_code:
          # Avoid changing the running code by making the new revision by digest
          self._EnsureImageDigest(serv, config_changes)
        # PUT the changed Service
        for config_change in config_changes:
          config_change.AdjustConfiguration(serv.configuration, serv.metadata)
        serv_name = service_ref.RelativeName()
        serv_update_req = (
            messages.ServerlessNamespacesServicesReplaceServiceRequest(
                service=serv.Message(),
                name=serv_name))
        with metrics.record_duration(metrics.UPDATE_SERVICE):
          updated = self._client.namespaces_services.ReplaceService(
              serv_update_req)
        return service.Service(updated, messages)

      else:
        if not with_code:
          raise serverless_exceptions.ServiceNotFoundError(
              'Service [{}] could not be found.'.format(service_ref.servicesId))
        # POST a new Service
        new_serv = service.Service.New(self._client, service_ref.namespacesId)
        new_serv.name = service_ref.servicesId
        pretty_print.Info('Creating new service [{bold}{service}{reset}]',
                          service=new_serv.name)
        parent = service_ref.Parent().RelativeName()
        for config_change in config_changes:
          config_change.AdjustConfiguration(new_serv.configuration,
                                            new_serv.metadata)
        serv_create_req = (
            messages.ServerlessNamespacesServicesCreateRequest(
                service=new_serv.Message(),
                parent=parent))
        with metrics.record_duration(metrics.CREATE_SERVICE):
          raw_service = self._client.namespaces_services.Create(
              serv_create_req)
        return service.Service(raw_service, messages)
    except api_exceptions.HttpBadRequestError as e:
      error_payload = exceptions_util.HttpErrorPayload(e)
      if error_payload.field_violations:
        if (serverless_exceptions.BadImageError.IMAGE_ERROR_FIELD
            in error_payload.field_violations):
          exceptions.reraise(serverless_exceptions.BadImageError(e))
      exceptions.reraise(e)
    except api_exceptions.HttpNotFoundError as e:
      # TODO(b/118339293): List available regions to check whether provided
      # region is invalid or not.
      raise serverless_exceptions.DeploymentFailedError(
          'Deployment endpoint was not found. Perhaps the provided '
          'region was invalid. Set the `run/region` property to a valid '
          'region and retry. Ex: `gcloud config set run/region us-central1`')

  def ReleaseService(self, service_ref, config_changes, asyn=False):
    """Change the given service in prod using the given config_changes.

    Ensures a new revision is always created, even if the spec of the revision
    has not changed.

    Arguments:
      service_ref: Resource, the service to release
      config_changes: list, objects that implement AdjustConfiguration().
      asyn: bool, if True release asyncronously
    """
    with_code = any(
        isinstance(c, deployable_pkg.Deployable) for c in config_changes)
    self._UpdateOrCreateService(service_ref, config_changes, with_code)
    if not asyn:
      getter = functools.partial(self.GetService, service_ref)
      self.WaitForCondition(getter)

  def ListRevisions(self, namespace_ref, service_name):
    """List all revisions for the given service.

    Args:
      namespace_ref: Resource, namespace to list revisions in
      service_name: str, The service for which to list revisions.

    Returns:
      A list of revisions for the given service.
    """
    messages = self._messages_module
    request = messages.ServerlessNamespacesRevisionsListRequest(
        parent=namespace_ref.RelativeName(),
    )
    if service_name is not None:
      # For now, same as the service name, and keeping compatible with
      # 'service-less' operation.
      request.labelSelector = 'serving.knative.dev/service = {}'.format(
          service_name)
    with metrics.record_duration(metrics.LIST_REVISIONS):
      response = self._client.namespaces_revisions.List(request)
    return [revision.Revision(item, messages) for item in response.items]

  def ListDomainMappings(self, namespace_ref):
    """List all domain mappings.

    Args:
      namespace_ref: Resource, namespace to list domain mappings in.

    Returns:
      A list of domain mappings.
    """
    messages = self._messages_module
    request = messages.ServerlessNamespacesDomainmappingsListRequest(
        parent=namespace_ref.RelativeName())
    with metrics.record_duration(metrics.LIST_DOMAIN_MAPPINGS):
      response = self._client.namespaces_domainmappings.List(request)
    return [domain_mapping.DomainMapping(item, messages)
            for item in response.items]
