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
"""Utilities for Vertex AI Model Garden APIs."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.ai import constants
from googlecloudsdk.command_lib.ai import flags

_HF_WILDCARD_FILTER = 'is_hf_wildcard(true)'
_NATIVE_MODEL_FILTER = 'is_hf_wildcard(false)'
_VERIFIED_DEPLOYMENT_FILTER = (
    'labels.VERIFIED_DEPLOYMENT_CONFIG=VERIFIED_DEPLOYMENT_SUCCEED'
)


def IsHuggingFaceModel(model_name: str) -> bool:
  """Returns whether the model is a Hugging Face model."""
  return bool(re.match(r'^[^/]+/[^/@]+$', model_name))


def IsCustomWeightsModel(model: str) -> bool:
  """Returns whether the model is a custom weights model."""
  return bool(re.match(r'^gs://', model))


def DeployCustomWeightsModel(
    messages,
    projects_locations_service,
    model,
    machine_type,
    accelerator_type,
    accelerator_count,
    project,
    location,
):
  """Deploys a custom weights model."""
  deploy_request = messages.GoogleCloudAiplatformV1beta1DeployRequest()
  deploy_request.customModel = (
      messages.GoogleCloudAiplatformV1beta1DeployRequestCustomModel(
          gcsUri=model
      )
  )

  if machine_type:
    deploy_request.deployConfig = messages.GoogleCloudAiplatformV1beta1DeployRequestDeployConfig(
        dedicatedResources=messages.GoogleCloudAiplatformV1beta1DedicatedResources(
            machineSpec=messages.GoogleCloudAiplatformV1beta1MachineSpec(
                machineType=machine_type,
                acceleratorType=accelerator_type,
                acceleratorCount=accelerator_count,
            ),
            minReplicaCount=1,
        ),
    )

  request = messages.AiplatformProjectsLocationsDeployRequest(
      destination=f'projects/{project}/locations/{location}',
      googleCloudAiplatformV1beta1DeployRequest=deploy_request,
  )
  return projects_locations_service.Deploy(request)


class ModelGardenClient(object):
  """Client used for interacting with Model Garden APIs."""

  def __init__(self, version=constants.BETA_VERSION):
    client = apis.GetClientInstance(
        constants.AI_PLATFORM_API_NAME,
        constants.AI_PLATFORM_API_VERSION[version],
    )
    self._messages = client.MESSAGES_MODULE
    self._publishers_models_service = client.publishers_models
    self._projects_locations_service = client.projects_locations

  def GetPublisherModel(
      self,
      model_name,
      is_hugging_face_model=False,
      include_equivalent_model_garden_model_deployment_configs=True,
      hugging_face_token=None,
  ):
    """Get a publisher model.

    Args:
      model_name: The name of the model to get. The format should be
        publishers/{publisher}/models/{model}
      is_hugging_face_model: Whether the model is a hugging face model.
      include_equivalent_model_garden_model_deployment_configs: Whether to
        include equivalent Model Garden model deployment configs for Hugging
        Face models.
      hugging_face_token: The Hugging Face access token to access the model
        artifacts for gated models unverified by Model Garden.

    Returns:
      A publisher model.
    """
    request = self._messages.AiplatformPublishersModelsGetRequest(
        name=model_name,
        isHuggingFaceModel=is_hugging_face_model,
        includeEquivalentModelGardenModelDeploymentConfigs=include_equivalent_model_garden_model_deployment_configs,
        huggingFaceToken=hugging_face_token,
    )
    return self._publishers_models_service.Get(request)

  def Deploy(
      self,
      project,
      location,
      model,
      accept_eula,
      accelerator_type,
      accelerator_count,
      machine_type,
      endpoint_display_name,
      hugging_face_access_token,
      spot,
      reservation_affinity,
      use_dedicated_endpoint,
      disable_dedicated_endpoint,
      enable_fast_tryout,
      container_image_uri=None,
      container_command=None,
      container_args=None,
      container_env_vars=None,
      container_ports=None,
      container_grpc_ports=None,
      container_predict_route=None,
      container_health_route=None,
      container_deployment_timeout_seconds=None,
      container_shared_memory_size_mb=None,
      container_startup_probe_exec=None,
      container_startup_probe_period_seconds=None,
      container_startup_probe_timeout_seconds=None,
      container_health_probe_exec=None,
      container_health_probe_period_seconds=None,
      container_health_probe_timeout_seconds=None,
  ):
    """Deploy an open weight model.

    Args:
      project: The project to deploy the model to.
      location: The location to deploy the model to.
      model: The name of the model to deploy or its gcs uri for custom weights.
      accept_eula: Whether to accept the end-user license agreement.
      accelerator_type: The type of accelerator to use.
      accelerator_count: The number of accelerators to use.
      machine_type: The type of machine to use.
      endpoint_display_name: The display name of the endpoint.
      hugging_face_access_token: The Hugging Face access token.
      spot: Whether to deploy the model on Spot VMs.
      reservation_affinity: The reservation affinity to use.
      use_dedicated_endpoint: Whether to use a dedicated endpoint.
      disable_dedicated_endpoint: Whether to disable the dedicated endpoint.
      enable_fast_tryout: Whether to enable fast tryout.
      container_image_uri: Immutable. URI of the Docker image to be used as the
        custom container for serving predictions. This URI must identify an
        image in Artifact Registry or Container Registry. Learn more about the
        [container publishing requirements](https://cloud.google.com/vertex-
        ai/docs/predictions/custom-container-requirements#publishing), including
        permissions requirements for the Vertex AI Service Agent. The container
        image is ingested upon ModelService.UploadModel, stored internally, and
        this original path is afterwards not used. To learn about the
        requirements for the Docker image itself, see [Custom container
        requirements](https://cloud.google.com/vertex-
        ai/docs/predictions/custom-container-requirements#). You can use the URI
        to one of Vertex AI's [pre-built container images for
        prediction](https://cloud.google.com/vertex-ai/docs/predictions/pre-
        built-containers) in this field.
      container_command: Specifies the command that runs when the container
        starts. This overrides the container's [ENTRYPOINT](https://docs.docker.
        com/engine/reference/builder/#entrypoint). Specify this field as an
        array of executable and arguments, similar to a Docker `ENTRYPOINT`'s
        "exec" form, not its "shell" form. If you do not specify this field,
        then the container's `ENTRYPOINT` runs, in conjunction with the args
        field or the container's
        [`CMD`](https://docs.docker.com/engine/reference/builder/#cmd), if
        either exists. If this field is not specified and the container does not
        have an `ENTRYPOINT`, then refer to the Docker documentation about [how
        `CMD` and `ENTRYPOINT`
        interact](https://docs.docker.com/engine/reference/builder/#understand-
        how-cmd-and-entrypoint-interact). If you specify this field, then you
        can also specify the `args` field to provide additional arguments for
        this command. However, if you specify this field, then the container's
        `CMD` is ignored. See the [Kubernetes documentation about how the
        `command` and `args` fields interact with a container's `ENTRYPOINT` and
        `CMD`](https://kubernetes.io/docs/tasks/inject-data-application/define-
        command-argument-container/#notes). In this field, you can reference
        [environment variables set by Vertex
        AI](https://cloud.google.com/vertex-ai/docs/predictions/custom-
        container-requirements#aip-variables) and environment variables set in
        the env field. You cannot reference environment variables set in the
        Docker image. In order for environment variables to be expanded,
        reference them by using the following syntax: $( VARIABLE_NAME) Note
        that this differs from Bash variable expansion, which does not use
        parentheses. If a variable cannot be resolved, the reference in the
        input string is used unchanged. To avoid variable expansion, you can
        escape this syntax with `$$`; for example: $$(VARIABLE_NAME) This field
        corresponds to the `command` field of the Kubernetes Containers [v1 core
        API](https://kubernetes.io/docs/reference/generated/kubernetes-
        api/v1.23/#container-v1-core).
      container_args: Specifies arguments for the command that runs when the
        container starts. This overrides the container's
        [`CMD`](https://docs.docker.com/engine/reference/builder/#cmd). Specify
        this field as an array of executable and arguments, similar to a Docker
        `CMD`'s "default parameters" form. If you don't specify this field but
        do specify the command field, then the command from the `command` field
        runs without any additional arguments. See the [Kubernetes documentation
        about how the `command` and `args` fields interact with a container's
        `ENTRYPOINT` and `CMD`](https://kubernetes.io/docs/tasks/inject-data-
        application/define-command-argument-container/#notes). If you don't
        specify this field and don't specify the `command` field, then the
        container's
        [`ENTRYPOINT`](https://docs.docker.com/engine/reference/builder/#cmd)
        and `CMD` determine what runs based on their default behavior. See the
        Docker documentation about [how `CMD` and `ENTRYPOINT`
        interact](https://docs.docker.com/engine/reference/builder/#understand-
        how-cmd-and-entrypoint-interact). In this field, you can reference
        [environment variables set by Vertex
        AI](https://cloud.google.com/vertex-ai/docs/predictions/custom-
        container-requirements#aip-variables) and environment variables set in
        the env field. You cannot reference environment variables set in the
        Docker image. In order for environment variables to be expanded,
        reference them by using the following syntax: $( VARIABLE_NAME) Note
        that this differs from Bash variable expansion, which does not use
        parentheses. If a variable cannot be resolved, the reference in the
        input string is used unchanged. To avoid variable expansion, you can
        escape this syntax with `$$`; for example: $$(VARIABLE_NAME) This field
        corresponds to the `args` field of the Kubernetes Containers [v1 core
        API](https://kubernetes.io/docs/reference/generated/kubernetes-
        api/v1.23/#container-v1-core)..
      container_env_vars: List of environment variables to set in the container.
        After the container starts running, code running in the container can
        read these environment variables. Additionally, the command and args
        fields can reference these variables. Later entries in this list can
        also reference earlier entries. For example, the following example sets
        the variable `VAR_2` to have the value `foo bar`: ```json [ { "name":
        "VAR_1", "value": "foo" }, { "name": "VAR_2", "value": "$(VAR_1) bar" }
        ] ``` If you switch the order of the variables in the example, then the
        expansion does not occur. This field corresponds to the `env` field of
        the Kubernetes Containers [v1 core
        API](https://kubernetes.io/docs/reference/generated/kubernetes-
        api/v1.23/#container-v1-core).
      container_ports: List of ports to expose from the container. Vertex AI
        sends any http prediction requests that it receives to the first port on
        this list. Vertex AI also sends [liveness and health
        checks](https://cloud.google.com/vertex-ai/docs/predictions/custom-
        container-requirements#liveness) to this port. If you do not specify
        this field, it defaults to following value: ```json [ { "containerPort":
        8080 } ] ``` Vertex AI does not use ports other than the first one
        listed. This field corresponds to the `ports` field of the Kubernetes
        Containers [v1 core
        API](https://kubernetes.io/docs/reference/generated/kubernetes-
        api/v1.23/#container-v1-core).
      container_grpc_ports: List of ports to expose from the container. Vertex
        AI sends any grpc prediction requests that it receives to the first port
        on this list. Vertex AI also sends [liveness and health
        checks](https://cloud.google.com/vertex-ai/docs/predictions/custom-
        container-requirements#liveness) to this port. If you do not specify
        this field, gRPC requests to the container will be disabled. Vertex AI
        does not use ports other than the first one listed. This field
        corresponds to the `ports` field of the Kubernetes Containers [v1 core
        API](https://kubernetes.io/docs/reference/generated/kubernetes-
        api/v1.23/#container-v1-core).
      container_predict_route: HTTP path on the container to send prediction
        requests to. Vertex AI forwards requests sent using
        projects.locations.endpoints.predict to this path on the container's IP
        address and port. Vertex AI then returns the container's response in the
        API response. For example, if you set this field to `/foo`, then when
        Vertex AI receives a prediction request, it forwards the request body in
        a POST request to the `/foo` path on the port of your container
        specified by the first value of this `ModelContainerSpec`'s ports field.
        If you don't specify this field, it defaults to the following value when
        you deploy this Model to an Endpoint:
        /v1/endpoints/ENDPOINT/deployedModels/DEPLOYED_MODEL:predict The
        placeholders in this value are replaced as follows: * ENDPOINT: The last
        segment (following `endpoints/`)of the Endpoint.name][] field of the
        Endpoint where this Model has been deployed. (Vertex AI makes this value
        available to your container code as the [`AIP_ENDPOINT_ID` environment
        variable](https://cloud.google.com/vertex-ai/docs/predictions/custom-
        container-requirements#aip-variables).) * DEPLOYED_MODEL:
        DeployedModel.id of the `DeployedModel`. (Vertex AI makes this value
        available to your container code as the [`AIP_DEPLOYED_MODEL_ID`
        environment variable](https://cloud.google.com/vertex-
        ai/docs/predictions/custom-container-requirements#aip-variables).)
      container_health_route: HTTP path on the container to send health checks
        to. Vertex AI intermittently sends GET requests to this path on the
        container's IP address and port to check that the container is healthy.
        Read more about [health checks](https://cloud.google.com/vertex-
        ai/docs/predictions/custom-container-requirements#health). For example,
        if you set this field to `/bar`, then Vertex AI intermittently sends a
        GET request to the `/bar` path on the port of your container specified
        by the first value of this `ModelContainerSpec`'s ports field. If you
        don't specify this field, it defaults to the following value when you
        deploy this Model to an Endpoint: /v1/endpoints/ENDPOINT/deployedModels/
        DEPLOYED_MODEL:predict The placeholders in this value are replaced as
          follows * ENDPOINT: The last segment (following `endpoints/`)of the
          Endpoint.name][] field of the Endpoint where this Model has been
          deployed. (Vertex AI makes this value available to your container code
          as the [`AIP_ENDPOINT_ID` environment
          variable](https://cloud.google.com/vertex-ai/docs/predictions/custom-
          container-requirements#aip-variables).) * DEPLOYED_MODEL:
          DeployedModel.id of the `DeployedModel`. (Vertex AI makes this value
          available to your container code as the [`AIP_DEPLOYED_MODEL_ID`
          environment variable](https://cloud.google.com/vertex-
          ai/docs/predictions/custom-container-requirements#aip-variables).)
      container_deployment_timeout_seconds (int): Deployment timeout in seconds.
      container_shared_memory_size_mb (int): The amount of the VM memory to
        reserve as the shared memory for the model in megabytes.
      container_startup_probe_exec (Sequence[str]): Exec specifies the action to
        take. Used by startup probe. An example of this argument would be
        ["cat", "/tmp/healthy"]
      container_startup_probe_period_seconds (int): How often (in seconds) to
        perform the startup probe. Default to 10 seconds. Minimum value is 1.
      container_startup_probe_timeout_seconds (int): Number of seconds after
        which the startup probe times out. Defaults to 1 second. Minimum value
        is 1.
      container_health_probe_exec (Sequence[str]): Exec specifies the action to
        take. Used by health probe. An example of this argument would be ["cat",
        "/tmp/healthy"]
      container_health_probe_period_seconds (int): How often (in seconds) to
        perform the health probe. Default to 10 seconds. Minimum value is 1.
      container_health_probe_timeout_seconds (int): Number of seconds after
        which the health probe times out. Defaults to 1 second. Minimum value is
        1.

    Returns:
      The deploy long-running operation.
    """
    if use_dedicated_endpoint and disable_dedicated_endpoint:
      raise ValueError(
          'use_dedicated_endpoint and disable_dedicated_endpoint cannot both be'
          ' True.'
      )
    container_spec = None
    if container_image_uri:
      container_spec = (
          self._messages.GoogleCloudAiplatformV1beta1ModelContainerSpec(
              healthRoute=container_health_route,
              imageUri=container_image_uri,
              predictRoute=container_predict_route,
          )
      )
      if container_command:
        container_spec.command = container_command
      if container_args:
        container_spec.args = container_args
      if container_env_vars:
        container_spec.env = [
            self._messages.GoogleCloudAiplatformV1beta1EnvVar(
                name=k, value=container_env_vars[k]
            )
            for k in container_env_vars
        ]
      if container_ports:
        container_spec.ports = [
            self._messages.GoogleCloudAiplatformV1beta1Port(containerPort=port)
            for port in container_ports
        ]
      if container_grpc_ports:
        container_spec.grpcPorts = [
            self._messages.GoogleCloudAiplatformV1beta1Port(containerPort=port)
            for port in container_grpc_ports
        ]
      if container_deployment_timeout_seconds:
        container_spec.deploymentTimeout = (
            str(container_deployment_timeout_seconds) + 's'
        )
      if container_shared_memory_size_mb:
        container_spec.sharedMemorySizeMb = container_shared_memory_size_mb
      if (
          container_startup_probe_exec
          or container_startup_probe_period_seconds
          or container_startup_probe_timeout_seconds
      ):
        startup_probe_exec = None
        if container_startup_probe_exec:
          startup_probe_exec = (
              self._messages.GoogleCloudAiplatformV1beta1ProbeExecAction(
                  command=container_startup_probe_exec
              )
          )
        container_spec.startupProbe = (
            self._messages.GoogleCloudAiplatformV1beta1Probe(
                exec_=startup_probe_exec,
                periodSeconds=container_startup_probe_period_seconds,
                timeoutSeconds=container_startup_probe_timeout_seconds,
            )
        )
      if (
          container_health_probe_exec
          or container_health_probe_period_seconds
          or container_health_probe_timeout_seconds
      ):
        health_probe_exec = None
        if container_health_probe_exec:
          health_probe_exec = (
              self._messages.GoogleCloudAiplatformV1beta1ProbeExecAction(
                  command=container_health_probe_exec
              )
          )
        container_spec.healthProbe = (
            self._messages.GoogleCloudAiplatformV1beta1Probe(
                exec_=health_probe_exec,
                periodSeconds=container_health_probe_period_seconds,
                timeoutSeconds=container_health_probe_timeout_seconds,
            )
        )

    if IsCustomWeightsModel(model):
      return DeployCustomWeightsModel(
          self._messages,
          self._projects_locations_service,
          model,
          machine_type,
          accelerator_type,
          accelerator_count,
          project,
          location,
      )
    elif IsHuggingFaceModel(model):
      deploy_request = self._messages.GoogleCloudAiplatformV1beta1DeployRequest(
          huggingFaceModelId=model
      )
    else:
      deploy_request = self._messages.GoogleCloudAiplatformV1beta1DeployRequest(
          publisherModelName=model
      )

    deploy_request.modelConfig = (
        self._messages.GoogleCloudAiplatformV1beta1DeployRequestModelConfig(
            huggingFaceAccessToken=hugging_face_access_token,
            acceptEula=accept_eula,
            containerSpec=container_spec,
        )
    )
    deploy_request.endpointConfig = (
        self._messages.GoogleCloudAiplatformV1beta1DeployRequestEndpointConfig(
            endpointDisplayName=endpoint_display_name,
            dedicatedEndpointEnabled=use_dedicated_endpoint,
            dedicatedEndpointDisabled=disable_dedicated_endpoint,
        )
    )
    deploy_request.deployConfig = self._messages.GoogleCloudAiplatformV1beta1DeployRequestDeployConfig(
        dedicatedResources=self._messages.GoogleCloudAiplatformV1beta1DedicatedResources(
            machineSpec=self._messages.GoogleCloudAiplatformV1beta1MachineSpec(
                machineType=machine_type,
                acceleratorType=accelerator_type,
                acceleratorCount=accelerator_count,
                reservationAffinity=flags.ParseReservationAffinityFlag(
                    reservation_affinity, constants.BETA_VERSION
                ),
            ),
            minReplicaCount=1,
            spot=spot,
        ),
        fastTryoutEnabled=enable_fast_tryout,
    )
    request = self._messages.AiplatformProjectsLocationsDeployRequest(
        destination=f'projects/{project}/locations/{location}',
        googleCloudAiplatformV1beta1DeployRequest=deploy_request,
    )
    return self._projects_locations_service.Deploy(request)

  def ListPublisherModels(
      self,
      limit=None,
      batch_size=100,
      list_hf_models=False,
      model_filter=None,
  ):
    """List publisher models in Model Garden.

    Args:
      limit: The maximum number of items to list. None if all available records
        should be yielded.
      batch_size: The number of items to list per page.
      list_hf_models: Whether to only list Hugging Face models.
      model_filter: The filter on model name to apply on server-side.

    Returns:
      The list of publisher models in Model Garden..
    """
    filter_str = _NATIVE_MODEL_FILTER
    if list_hf_models:
      filter_str = ' AND '.join(
          [_HF_WILDCARD_FILTER, _VERIFIED_DEPLOYMENT_FILTER]
      )
    if model_filter:
      filter_str = (
          f'{filter_str} AND (model_user_id=~"(?i).*{model_filter}.*" OR'
          f' display_name=~"(?i).*{model_filter}.*")'
      )
    return list_pager.YieldFromList(
        self._publishers_models_service,
        self._messages.AiplatformPublishersModelsListRequest(
            parent='publishers/*',
            listAllVersions=True,
            filter=filter_str,
        ),
        field='publisherModels',
        batch_size_attribute='pageSize',
        batch_size=batch_size,
        limit=limit,
    )
