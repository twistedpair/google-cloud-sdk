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
"""Command library for run compose resource command.

This library handles the creation of Google Cloud resources required to deploy a
Docker Compose application to Cloud Run. It's utilized by the
`gcloud run compose up` command.

The core responsibilities include:
  1.  Parsing the JSON output from the 'runcompose' Go binary, which lists
      the necessary resources based on the compose file.
  2.  Providing classes to represent these resources (e.g., Cloud Build).
  3.  Orchestrating the creation of these resources in Google Cloud.
"""

import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional

from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.api_lib.run import global_methods
from googlecloudsdk.api_lib.run import service
from googlecloudsdk.api_lib.secrets import api as secrets_api
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.run import config_changes
from googlecloudsdk.command_lib.run import connection_context
from googlecloudsdk.command_lib.run import exceptions as serverless_exceptions
from googlecloudsdk.command_lib.run import flags as run_flags
from googlecloudsdk.command_lib.run import platforms
from googlecloudsdk.command_lib.run import serverless_operations
from googlecloudsdk.command_lib.run import stages
from googlecloudsdk.command_lib.run.compose import builder
from googlecloudsdk.command_lib.run.compose import tracker as compose_tracker
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.util import files


# Maximum length for a GCS bucket name.
_MAX_BUCKET_NAME_LENGTH = 63


def _generate_gcs_bucket_name(compose_project_name: str, region: str) -> str:
  """Generates a unique bucket name for the compose project.

  The bucket name is derived from the project number, a sanitized version of
  the compose project name, and the region. To ensure the bucket name
  adheres to GCS naming conventions (e.g., max length), a hash is used
  if the initial candidate name is too long.

  Args:
    compose_project_name: The name of the Docker Compose project.
    region: The Google Cloud region.

  Returns:
    A valid GCS bucket name.
  """
  project_number = _get_project_number()
  # Sanitize the project name to be suitable for a bucket name.
  sanitized_project_name = compose_project_name.lower()
  sanitized_project_name = re.sub(r'[^a-z0-9-]+', '-', sanitized_project_name)
  sanitized_project_name = re.sub(r'-+', '-', sanitized_project_name)

  # Construct a candidate bucket name.
  bucket_name_candidate = (
      f'{project_number}-{sanitized_project_name}-{region}-compose'
  )

  # GCS bucket names have a maximum length. If the candidate is too long,
  # generate a shorter version using a hash of the sanitized project name.
  if len(bucket_name_candidate) > _MAX_BUCKET_NAME_LENGTH:
    project_hash = hashlib.sha1(
        sanitized_project_name.encode()
    ).hexdigest()[:8]
    return f'{project_number}-{project_hash}-{region}-compose'
  else:
    return bucket_name_candidate


class SecretConfig:
  """Represents the secret configuration for a service."""

  def __init__(
      self,
      name: Optional[str] = None,
      file: Optional[str] = None,
      mount: Optional[str] = None,
  ):
    self.name = name
    self.file = file
    # secret_version is only set after the secret is created.
    self.secret_version: Optional[str] = None
    self.mount = mount

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'SecretConfig':
    config = cls(
        name=data.get('name'),
        file=data.get('file'),
        mount=data.get('mount'),
    )
    config.secret_version = data.get('secret_version')
    return config

  def handle(self) -> None:
    """Creates the secret in Google Secret Manager and adds a version.

    This method calls the internal function _create_secret_and_add_version
    to perform the actual resource creation and versioning.
    """
    log.debug('Handling secret: %s', self.name)
    _create_secret_and_add_version(self)

  # TODO(b/442334111): Rename secret version field to the version.
  def to_dict(self) -> Dict[str, Any]:
    """Serializes the SecretConfig instance to a dictionary."""
    return {
        'name': self.name,
        'file': self.file,
        'mount': self.mount,
        'secret_version': self.secret_version,
    }


class Config:
  """Represents the config configuration for a service."""

  def __init__(
      self,
      name: Optional[str] = None,
      file: Optional[str] = None,
      target: Optional[str] = None,
  ):
    self.name = name
    self.file = file
    self.target = target
    self.bucket_name: Optional[str] = None

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'Config':
    config = cls(
        name=data.get('name'),
        file=data.get('file'),
        target=data.get('target'),
    )
    config.bucket_name = data.get('bucket_name')
    return config

  def handle(self, bucket_name: str, region: str) -> None:
    """Handles the creation of resources for the config."""
    if not self.name:
      raise exceptions.Error(
          f'Config declared without a name, but name is required: {self.file}'
      )
    log.debug('Handling config: %s', self.name)
    gcs_handler = GcsHandler(bucket_name, region)
    gcs_handler.ensure_bucket()
    self.bucket_name = bucket_name
    source = self.file
    if not source or not os.path.exists(source):
      raise exceptions.Error(
          f"Config source '{source}' for config '{self.name}' does not exist."
      )

    source_basename = os.path.basename(source)
    gcs_path = '/'.join(['configs', self.name, source_basename])

    if os.path.isfile(source):
      gcs_handler.upload_file(gcs_path, source)
    else:
      raise exceptions.Error(f"Config source path '{source}' is not a file.")

  def to_dict(self) -> Dict[str, Any]:
    """Serializes the ConfigConfig instance to a dictionary."""
    return {
        'name': self.name,
        'file': self.file,
        'target': self.target,
        'bucket_name': self.bucket_name,
    }


class BindMountConfig:
  """Represents the bind mount configuration for a service."""

  def __init__(
      self, source: Optional[str] = None, target: Optional[str] = None
  ):
    self.source = source
    self.target = target
    self.mount_source: Optional[str] = None

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'BindMountConfig':
    config = cls(
        source=data.get('source'),
        target=data.get('target'),
    )

    config.mount_source = data.get('mount_source')
    return config

  def handle(self, gcs_handler: 'GcsHandler', service_name: str) -> None:
    """Handles the creation of resources for the bind mount."""
    gcs_handler.ensure_bucket()
    source = self.source
    if not source or not os.path.exists(source):
      raise exceptions.Error(
          f"Bind mount source '{source}' for service '{service_name}' does not"
          ' exist.'
      )

    # Resolve the source path to handle cases like '.', './', etc. consistently.
    if os.path.abspath(source) == os.getcwd():
      gcs_path = '/'.join(['bind_mounts', service_name])
    else:
      source_basename = os.path.basename(source)
      gcs_path = '/'.join(['bind_mounts', service_name, source_basename])

    self.mount_source = gcs_path
    if os.path.isdir(source):
      gcs_handler.upload_directory(gcs_path, source)
    elif os.path.isfile(source):
      gcs_handler.upload_file(gcs_path, source)
    else:
      raise exceptions.Error(
          f"Source path '{source}' is not a file or directory."
      )

  def to_dict(self) -> Dict[str, Any]:
    """Serializes the BindMountConfig instance to a dictionary."""
    return {
        'source': self.source,
        'target': self.target,
        'mount_source': self.mount_source,
    }


class NamedVolumeConfig:
  """Represents the named volume configuration for a service."""

  def __init__(self, name: Optional[str] = None):
    self.name = name

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'NamedVolumeConfig':
    return cls(
        name=data.get('name'),
    )

  def to_dict(self) -> Dict[str, Any]:
    """Serializes the NamedVolumeConfig instance to a dictionary."""
    return {
        'name': self.name,
    }


class GcsHandler:
  """Handles GCS operations for compose resources."""

  def __init__(self, bucket_name: str, region: str):
    log.debug(
        'Initializing GcsHandler for bucket %s in region %s',
        bucket_name,
        region,
    )
    self.bucket_name = bucket_name
    self.region = region
    self._gcs_client = storage_api.StorageClient()
    self._bucket_ensured = False

  def ensure_bucket(self):
    """Ensures the GCS bucket exists."""
    if not self._bucket_ensured:
      self._ensure_bucket_exists(self.bucket_name)
      self._bucket_ensured = True

  def _ensure_bucket_exists(self, bucket_name: str) -> None:
    """Creates the GCS bucket if it doesn't exist and sets IAM policy."""
    try:
      self._gcs_client.CreateBucketIfNotExists(
          bucket_name, location=self.region
      )
      log.debug(
          f"Ensured bucket '{bucket_name}' exists in region '{self.region}'."
      )
    except Exception as e:
      raise exceptions.Error(
          f"Failed to create bucket '{bucket_name}': {e}"
      )

    # Add IAM policy binding for the compute service account
    try:
      service_account = _get_compute_service_account()
      bucket_resource = storage_util.BucketReference(bucket_name)
      policy = self._gcs_client.GetIamPolicy(bucket_resource)
      binding_class = policy.field_by_name('bindings').message_type
      iam_util.AddBindingToIamPolicy(
          binding_class,
          policy,
          f'serviceAccount:{service_account}',
          'roles/storage.objectUser',
      )
      self._gcs_client.SetIamPolicy(bucket_resource, policy)
      log.debug(
          f'Set roles/storage.objectUser for {service_account} on bucket'
          f" '{bucket_name}'."
      )
    except Exception as e:
      raise exceptions.Error(
          f"Failed to set IAM policy on bucket '{bucket_name}': {e}"
      )

  def upload_directory(
      self,
      gcs_path: str,
      source_path: str,
  ) -> None:
    """Uploads a directory to GCS."""
    if not os.path.isdir(source_path):
      raise exceptions.Error(f"Source path '{source_path}' is not a directory.")

    for root, _, files_in_dir in os.walk(source_path):
      for file_name in files_in_dir:
        local_file = os.path.join(root, file_name)
        relative_path = os.path.relpath(local_file, source_path)
        gcs_file_path = '/'.join(
            [gcs_path, relative_path.replace(os.sep, '/')]
        )
        object_ref = storage_util.ObjectReference(self.bucket_name, gcs_file_path)
        self._gcs_client.CopyFileToGCS(local_file, object_ref)
    log.debug(
        f"Uploaded directory '{source_path}' to"
        f" 'gs://{self.bucket_name}/{gcs_path}'"
    )

  def upload_file(self, gcs_path: str, source_path: str) -> None:
    """Uploads a single file to GCS."""
    if not os.path.isfile(source_path):
      raise exceptions.Error(f"Source path '{source_path}' is not a file.")
    object_ref = storage_util.ObjectReference(self.bucket_name, gcs_path)
    self._gcs_client.CopyFileToGCS(source_path, object_ref)
    log.debug(
        f"Uploaded file '{source_path}' to 'gs://{self.bucket_name}/{gcs_path}'"
    )


class VolumeConfig:
  """Represents the volume configuration for a docker compose project."""

  def __init__(
      self,
      bind_mount: Optional[Dict[str, list[BindMountConfig]]] = None,
      named_volume: Optional[Dict[str, NamedVolumeConfig]] = None,
  ):
    self.bind_mount = bind_mount if bind_mount is not None else {}
    self.named_volume = named_volume if named_volume is not None else {}
    self.bucket_name: Optional[str] = None

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'VolumeConfig':
    """Creates a VolumeConfig instance from a dictionary."""
    bind_mount = {
        key: [BindMountConfig.from_dict(item) for item in value]
        for key, value in data.get('bind_mount', {}).items()
    }
    named_volume = {
        key: NamedVolumeConfig.from_dict(value)
        for key, value in data.get('named_volume', {}).items()
    }
    return cls(bind_mount=bind_mount, named_volume=named_volume)

  def handle(self, bucket_name: str, region: str) -> None:
    """Handles all volume configurations."""
    if not self.bind_mount and not self.named_volume:
      log.debug('No volumes to handle.')
      return

    log.debug('Handling volume configurations.')
    gcs_handler = GcsHandler(bucket_name, region)
    gcs_handler.ensure_bucket()
    self.bucket_name = bucket_name

    # Handle bind mounts
    for service_name, bind_mounts in self.bind_mount.items():
      for bm_config in bind_mounts:
        bm_config.handle(gcs_handler, service_name)

    log.debug('Volume handling complete.')

  def to_dict(self) -> Dict[str, Any]:
    """Serializes the VolumeConfig instance to a dictionary."""
    return {
        'bind_mount': {
            key: [item.to_dict() for item in value]
            for key, value in self.bind_mount.items()
        },
        'named_volume': {
            key: value.to_dict() for key, value in self.named_volume.items()
        },
        'bucket_name': self.bucket_name,
    }


class ResourcesConfig:
  """Represents the resources config sent form runcompose go binary."""

  def __init__(
      self,
      source_builds: Optional[Dict[str, builder.BuildConfig]] = None,
      secrets: Optional[Dict[str, SecretConfig]] = None,
      volumes: Optional[VolumeConfig] = None,
      project: Optional[str] = None,
      configs: Optional[list[Config]] = None,
  ):
    self.source_builds = source_builds if source_builds is not None else {}
    self.secrets = secrets if secrets is not None else {}
    self.volumes = volumes if volumes is not None else VolumeConfig()
    self.project = project

    self.configs = configs if configs is not None else []

  def get_required_apis(self, no_build: bool = False) -> List[str]:
    """Returns a list of APIs required for the resources in this config."""
    required_apis = {
        'run.googleapis.com',
        'cloudresourcemanager.googleapis.com',
    }

    if self.source_builds and not no_build:
      required_apis.update({
          'cloudbuild.googleapis.com',
          'storage.googleapis.com',
          'artifactregistry.googleapis.com',
      })
    if self.secrets:
      required_apis.update(
          {'secretmanager.googleapis.com', 'iam.googleapis.com'}
      )
    if self.volumes.bind_mount or self.volumes.named_volume or self.configs:
      required_apis.update({'storage.googleapis.com', 'iam.googleapis.com'})

    return sorted(list(required_apis))

  @classmethod
  def from_json(cls, json_data: str) -> 'ResourcesConfig':
    """Parses the JSON string to create a ResourcesConfig instance."""
    data = json.loads(json_data)
    config = cls.from_dict(data)
    return config

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'ResourcesConfig':
    """Creates a ResourcesConfig instance from a dictionary."""
    source_builds = {
        key: builder.BuildConfig.from_dict(value)
        for key, value in data.get('source_builds', {}).items()
    }
    secrets = {
        key: SecretConfig.from_dict(value)
        for key, value in data.get('secrets', {}).items()
    }
    volumes = VolumeConfig.from_dict(data.get('volumes', {}))
    configs = [
        Config.from_dict(item) for item in data.get('configs', [])
    ]
    project = data.get('project')
    return cls(
        source_builds=source_builds,
        secrets=secrets,
        volumes=volumes,
        project=project,
        configs=configs,
    )

  def handle_resources(
      self,
      region: str,
      repo: str,
      tracker: progress_tracker.StagedProgressTracker,
      no_build: bool = False,
  ) -> 'ResourcesConfig':
    """Creates or updates all resources defined in the configuration.

    This method orchestrates the handling of each type of resource,
    such as secrets, by calling their respective handle() methods.

    Args:
      region: The region of the compose project.
      repo: The repo of the compose project.
      tracker: The progress tracker to use for handling the resources.
      no_build: If true, skip building from source.

    Returns:
      The ResourcesConfig instance after handling the resources.
    """
    if not self.project:
      raise exceptions.Error(
          'Project name is missing in Compose file, but is required when'
          ' using volumes or configs.'
      )
    if self.source_builds:
      builder.handle(
          self.source_builds,
          repo,
          self.project,
          region,
          tracker,
          no_build,
      )

    log.debug('Starting resource handling for project: %s', self.project)
    if self.secrets:
      tracker.StartStage(
          compose_tracker.StagedProgressTrackerStage.SECRETS.get_key()
      )
      for name, secret_config in self.secrets.items():
        log.debug(f'Handling secret: {name}')
        secret_config.handle()
      tracker.CompleteStage(
          compose_tracker.StagedProgressTrackerStage.SECRETS.get_key()
      )

    if self.volumes.bind_mount or self.volumes.named_volume or self.configs:
      log.debug('Initializing GCS handler for volumes and/or configs.')
      bucket_name = _generate_gcs_bucket_name(self.project, region)
      if self.volumes.bind_mount or self.volumes.named_volume:
        tracker.StartStage(
            compose_tracker.StagedProgressTrackerStage.VOLUMES.get_key()
        )
        self.volumes.handle(bucket_name, region)
        tracker.CompleteStage(
            compose_tracker.StagedProgressTrackerStage.VOLUMES.get_key()
        )
      if self.configs:
        tracker.StartStage(
            compose_tracker.StagedProgressTrackerStage.CONFIGS.get_key()
        )
        for config in self.configs:
          log.debug('Handling config: %s', config.name)
          config.handle(bucket_name, region)
        tracker.CompleteStage(
            compose_tracker.StagedProgressTrackerStage.CONFIGS.get_key()
        )
    return self

  def to_dict(self) -> Dict[str, Any]:
    """Serializes the ResourcesConfig instance to a dictionary."""
    return {
        'project': self.project,
        'source_builds': {
            name: build.to_dict() for name, build in self.source_builds.items()
        },
        'secrets': {
            name: secret.to_dict() for name, secret in self.secrets.items()
        },
        'volumes': self.volumes.to_dict(),
        'configs': [c.to_dict() for c in self.configs],
    }

  def to_json(self) -> str:
    """Serializes the ResourcesConfig instance to a JSON string."""
    return json.dumps(self.to_dict())


class TranslateResult:
  """Represents the translate command result from runcompose go binary."""

  def __init__(
      self,
      services: Optional[Dict[str, str]] = None,
      models: Optional[Dict[str, str]] = None,
  ):
    self.services = services if services is not None else {}
    self.models = models if models is not None else {}

  @classmethod
  def from_json(cls, json_data: str) -> 'TranslateResult':
    """Parses the JSON string to create a TranslateResult instance."""
    data = json.loads(json_data)
    return cls.from_dict(data)

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'TranslateResult':
    """Creates a TranslateResult instance from a dictionary."""
    services = data.get('services', {})
    models = data.get('models', {})
    return cls(services=services, models=models)

  def to_json(self) -> str:
    """Serializes the TranslateResult instance to a JSON string."""
    return json.dumps(self.to_dict())

  def to_dict(self) -> Dict[str, Any]:
    """Serializes the TranslateResult instance to a dictionary."""
    return {
        'services': self.services,
        'models': self.models,
    }


def _create_secret_and_add_version(
    config: SecretConfig
) -> None:
  """Creates a secret if it doesn't exist and adds a version from a file."""
  if not config.name or not config.file or not config.mount:
    raise ValueError('Secret name, file path and mount name are required.')

  if not os.path.exists(config.file):
    raise ValueError(f'Secret file not found: {config.file}')

  secrets_client = secrets_api.Secrets()
  project = properties.VALUES.core.project.Get(required=True)
  secret_ref = resources.REGISTRY.Parse(
      config.name,
      params={'projectsId': project},
      collection='secretmanager.projects.secrets',
  )

  # Check if secret exists
  if secrets_client.GetOrNone(secret_ref) is None:
    log.debug(f"Creating secret '{config.name}' in project '{project}'.")
    try:
      # Default replication policy is automatic
      secrets_client.Create(
          secret_ref,
          policy='automatic',
          locations=None,
          labels=None,
          tags=None,
      )
      log.debug(f"Secret '{config.name}' created.")
    except Exception as e:
      log.error(f"Failed to create secret '{config.name}': {e}")
      raise
  else:
    log.debug(f"Secret '{config.name}' already exists.")

  # Add IAM policy binding for the compute service account
  try:
    service_account = _get_compute_service_account()
    policy = secrets_client.GetIamPolicy(secret_ref)
    member = f'serviceAccount:{service_account}'
    role = 'roles/secretmanager.secretAccessor'
    if not iam_util.BindingInPolicy(policy, member, role):
      binding_class = policy.field_by_name('bindings').message_type
      iam_util.AddBindingToIamPolicy(
          binding_class,
          policy,
          member,
          role,
      )
      secrets_client.SetIamPolicy(secret_ref, policy)
      log.debug(f"Set {role} for {service_account} on secret '{config.name}'.")
    else:
      log.debug(
          f'{role} for {service_account} already exists on secret'
          f" '{config.name}'."
      )
  except Exception as e:
    raise exceptions.Error(
        f"Failed to set IAM policy on secret '{config.name}': {e}"
    )

  # Add secret version
  try:
    log.debug(
        f"Reading secret content from '{config.file}' for secret"
        f" '{config.mount}'."
    )
    secret_data = files.ReadBinaryFileContents(config.file)

    log.debug(f"Adding new version to secret '{config.name}'.")
    # data_crc32c is not calculated here, but could be added for integrity
    # TODO(b/440494739): Reuse secret values if unchanged
    version = secrets_client.AddVersion(
        secret_ref, secret_data, data_crc32c=None
    )
    config.secret_version = version.name
    log.debug(
        f"Added secret version '{config.secret_version}' to secret"
        f" '{config.name}'."
    )
  except Exception as e:
    log.error(f"Failed to add version to secret '{config.name}': {e}")
    raise


def _get_project_number() -> str:
  """Retrieves the project number for the current project."""

  project_id = properties.VALUES.core.project.Get(required=True)
  project_ref = resources.REGISTRY.Parse(
      project_id, collection='cloudresourcemanager.projects'
  )
  project = projects_api.Get(project_ref)
  return str(project.projectNumber)


def deploy_application(
    yaml_file_path: str,
    region: str,
    args: Any,
    release_track: base.ReleaseTrack,
) -> None:
  """Deploys a Cloud Run application from a YAML file.

  Args:
    yaml_file_path: The path to the Cloud Run service YAML file.
    region: The region to deploy the application to.
    args: The arguments passed to the command.
    release_track: The release track of the command.
  """
  project = properties.VALUES.core.project.Get(required=True)

  run_messages = apis.GetMessagesModule(
      global_methods.SERVERLESS_API_NAME,
      global_methods.SERVERLESS_API_VERSION,
  )

  try:
    service_dict = yaml.load_path(yaml_file_path)
    if not service_dict:
      raise exceptions.Error(f"Could not parse YAML file '{yaml_file_path}'.")
  except (files.Error, yaml.Error) as e:
    raise exceptions.Error(
        f"Failed to read or parse YAML file '{yaml_file_path}': {e}"
    )

  new_service = None
  try:
    raw_service = messages_util.DictToMessageWithErrorCheck(
        service_dict, run_messages.Service
    )
    new_service = service.Service(raw_service, run_messages)
  except messages_util.ScalarTypeMismatchError as e:
    serverless_exceptions.MaybeRaiseCustomFieldMismatch(
        e,
        help_text=(
            'Please make sure that the YAML file matches the Knative '
            'service definition spec in https://kubernetes.io/docs/'
            'reference/kubernetes-api/service-resources/service-v1/'
            '#Service.'
        ),
    )

  if not new_service or not new_service.name:
    raise exceptions.Error('Service name is missing in the YAML file.')

  log.status.Print(
      f'Deploying service \'{new_service.name}\' in project \'{project}\''
      f' in region \'{region}\'.'
  )

  service_ref = resources.REGISTRY.Parse(
      new_service.metadata.name,
      params={'namespacesId': project},
      collection='run.namespaces.services',
  )
  conn_context = connection_context.GetConnectionContext(
      None,
      platform=platforms.PLATFORM_MANAGED,
      region_label=region,
  )
  with serverless_operations.Connect(conn_context) as client:
    existing_service = client.GetService(service_ref)
    changes = [config_changes.ReplaceServiceChange(new_service)]
    allow_unauthenticated = run_flags.GetAllowUnauthenticated(
        args, client, service_ref, not existing_service
    )
    # Avoid failure removing a policy binding for a service that
    # doesn't exist.
    if not existing_service and not allow_unauthenticated:
      allow_unauthenticated = None

    header = (
        f'Deploying service \'{new_service.name}\'...'
        if not existing_service
        else f'Updating service \'{new_service.name}\'...'
    )

    with progress_tracker.StagedProgressTracker(
        header,
        stages.ServiceStages(allow_unauthenticated is not None),
        failure_message='Deployment failed',
        suppress_output=False,
        success_message=f"Service '{new_service.name}' has been deployed.",
    ) as tracker:
      deployed_service = client.ReleaseService(
          service_ref,
          changes,
          release_track,
          tracker,
          asyn=False,
          allow_unauthenticated=allow_unauthenticated,
          for_replace=True,
          prefetch=existing_service,
      )
  if (
      deployed_service
      and deployed_service.status
      and deployed_service.status.url
  ):
    log.status.Print(f'Service URL: {deployed_service.status.url}')


def _get_compute_service_account() -> str:
  """Retrieves the default compute service account for the current project."""
  project_number = _get_project_number()
  return f'{project_number}-compute@developer.gserviceaccount.com'
