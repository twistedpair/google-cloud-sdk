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

import json
import os
import re
from typing import Any, Dict, Optional

from googlecloudsdk.api_lib.cloudbuild import cloudbuild_util
from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.api_lib.secrets import api as secrets_api
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.command_lib.builds import submit_util
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files


class BuildConfig:
  """Represents the build configuration for a service."""

  def __init__(
      self, context: Optional[str] = None, dockerfile: Optional[str] = None
  ):
    self.context = context
    self.dockerfile = dockerfile
    self.image_id: Optional[str] = None

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'BuildConfig':
    return cls(
        context=data.get('context'),
        dockerfile=data.get('dockerfile'),
    )

  def to_dict(self) -> Dict[str, Any]:
    """Serializes the BuildConfig instance to a dictionary."""
    return {
        'context': self.context,
        'dockerfile': self.dockerfile,
        'image_id': self.image_id,
    }


class SecretConfig:
  """Represents the secret configuration for a service."""

  def __init__(
      self,
      secret_name: Optional[str] = None,
      file: Optional[str] = None,
      mount_name: Optional[str] = None,
  ):
    self.secret_name = secret_name
    self.file = file
    # secret_version is only set after the secret is created.
    self.secret_version: Optional[str] = None
    self.mount_name = mount_name

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'SecretConfig':
    config = cls(
        secret_name=data.get('secret_name'),
        file=data.get('file'),
        mount_name=data.get('mount_name'),
    )
    config.secret_version = data.get('secret_version')
    return config

  def handle(self) -> None:
    """Creates the secret in Google Secret Manager and adds a version.

    This method calls the internal function _create_secret_and_add_version
    to perform the actual resource creation and versioning.
    """
    _create_secret_and_add_version(self)

  def to_dict(self) -> Dict[str, Any]:
    """Serializes the SecretConfig instance to a dictionary."""
    return {
        'secret_name': self.secret_name,
        'file': self.file,
        'mount_name': self.mount_name,
        'secret_version': self.secret_version,
    }


class BindMountConfig:
  """Represents the bind mount configuration for a service."""

  def __init__(
      self, source: Optional[str] = None, target: Optional[str] = None
  ):
    self.source = source
    self.target = target

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'BindMountConfig':
    return cls(
        source=data.get('source'),
        target=data.get('target'),
    )

  def _upload_directory(
      self,
      gcs_client: storage_api.StorageClient,
      bucket_name: str,
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
        object_ref = storage_util.ObjectReference(bucket_name, gcs_file_path)
        gcs_client.CopyFileToGCS(local_file, object_ref)
    log.status.Print(
        f"Uploaded directory '{source_path}' to 'gs://{bucket_name}/{gcs_path}'"
    )

  def _upload_file(
      self,
      gcs_client: storage_api.StorageClient,
      bucket_name: str,
      gcs_path: str,
      source_path: str,
  ) -> None:
    """Uploads a single file to GCS."""
    if not os.path.isfile(source_path):
      raise exceptions.Error(f"Source path '{source_path}' is not a file.")
    object_ref = storage_util.ObjectReference(bucket_name, gcs_path)
    gcs_client.CopyFileToGCS(source_path, object_ref)
    log.status.Print(
        f"Uploaded file '{source_path}' to 'gs://{bucket_name}/{gcs_path}'"
    )

  def handle(
      self,
      gcs_client: storage_api.StorageClient,
      bucket_name: str,
      service_name: str,
  ) -> None:
    """Handles the creation of resources for the bind mount."""
    source = self.source
    if not source or not os.path.exists(source):
      raise exceptions.Error(
          f"Bind mount source '{source}' for service '{service_name}' does not"
          ' exist.'
      )

    source_basename = os.path.basename(source)
    gcs_path = '/'.join(['bind_mounts', service_name, source_basename])

    if os.path.isdir(source):
      self._upload_directory(gcs_client, bucket_name, gcs_path, source)
    elif os.path.isfile(source):
      self._upload_file(gcs_client, bucket_name, gcs_path, source)
    else:
      raise exceptions.Error(
          f"Source path '{source}' is not a file or directory."
      )

  def to_dict(self) -> Dict[str, Any]:
    """Serializes the BindMountConfig instance to a dictionary."""
    return {
        'source': self.source,
        'target': self.target,
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


class VolumeConfig:
  """Represents the volume configuration for a docker compose project."""

  def __init__(
      self,
      bind_mount: Optional[Dict[str, list[BindMountConfig]]] = None,
      named_volume: Optional[Dict[str, NamedVolumeConfig]] = None,
  ):
    self.bind_mount = bind_mount if bind_mount is not None else {}
    self.named_volume = named_volume if named_volume is not None else {}
    self._gcs_client = storage_api.StorageClient()

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

  def _generate_bucket_name(
      self, compose_project_name: str, region: str
  ) -> str:
    """Generates a unique bucket name for the compose project."""
    project_number = _get_project_number()
    sanitized_project_name = compose_project_name.lower()
    sanitized_project_name = re.sub(r'[^a-z0-9-]+', '-', sanitized_project_name)
    sanitized_project_name = re.sub(r'-+', '-', sanitized_project_name)
    return f'{project_number}-{sanitized_project_name}-{region}-compose-volumes'

  def _get_compute_service_account(self) -> str:
    project_number = _get_project_number()
    return f'{project_number}-compute@developer.gserviceaccount.com'

  def _ensure_bucket_exists(self, bucket_name: str, region: str) -> None:
    """Creates the GCS bucket if it doesn't exist and sets IAM policy."""
    try:
      self._gcs_client.CreateBucketIfNotExists(bucket_name, location=region)
      log.status.Print(
          f"Ensured bucket '{bucket_name}' exists in region '{region}'."
      )
    except Exception as e:
      raise exceptions.Error(f"Failed to create bucket '{bucket_name}': {e}")

    # Add IAM policy binding for the compute service account
    try:
      service_account = self._get_compute_service_account()
      bucket_resource = storage_util.BucketReference(bucket_name)
      policy = self._gcs_client.GetIamPolicy(bucket_resource)
      iam_util.AddBindingToIamPolicy(
          storage_util.GetMessages().Binding,
          policy,
          f'serviceAccount:{service_account}',
          'roles/storage.objectUser',
      )
      self._gcs_client.SetIamPolicy(bucket_resource, policy)
      log.status.Print(
          f'Set roles/storage.admin for {service_account} on bucket'
          f" '{bucket_name}'."
      )
    except Exception as e:
      raise exceptions.Error(
          f"Failed to set IAM policy on bucket '{bucket_name}': {e}"
      )

  def handle(self, compose_project_name: str, region: str) -> None:
    """Handles all volume configurations."""
    if not self.bind_mount and not self.named_volume:
      log.debug('No volumes to handle.')
      return

    bucket_name = self._generate_bucket_name(compose_project_name, region)
    self._ensure_bucket_exists(bucket_name, region)

    # Handle bind mounts
    for service_name, bind_mounts in self.bind_mount.items():
      for bm_config in bind_mounts:
        bm_config.handle(self._gcs_client, bucket_name, service_name)

    log.status.Print('Volume handling complete.')

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
    }


class ResourcesConfig:
  """Represents the resources config sent form runcompose go binary."""

  def __init__(
      self,
      source_builds: Optional[Dict[str, BuildConfig]] = None,
      secrets: Optional[Dict[str, SecretConfig]] = None,
      volumes: Optional[VolumeConfig] = None,
      project_name: Optional[str] = None,
  ):
    self.source_builds = source_builds if source_builds is not None else {}
    self.secrets = secrets if secrets is not None else {}
    self.volumes = volumes if volumes is not None else VolumeConfig()
    self.project_name = project_name

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
        key: BuildConfig.from_dict(value)
        for key, value in data.get('source_builds', {}).items()
    }
    secrets = {
        key: SecretConfig.from_dict(value)
        for key, value in data.get('secrets', {}).items()
    }
    volumes = VolumeConfig.from_dict(data.get('volumes', {}))
    project_name = data.get('project_name')
    return cls(
        source_builds=source_builds,
        secrets=secrets,
        volumes=volumes,
        project_name=project_name,
    )

  def handle_resources(self) -> 'ResourcesConfig':
    """Creates or updates all resources defined in the configuration.

    This method orchestrates the handling of each type of resource,
    such as secrets, by calling their respective handle() methods.

    Returns:
      The ResourcesConfig instance after handling the resources.
    """
    if not self.secrets:
      log.debug('No secrets to handle.')
      return self
    for name, secret_config in self.secrets.items():
      log.status.Print('Handling secret: %s', name)
      secret_config.handle()
    return self

  def to_dict(self) -> Dict[str, Any]:
    """Serializes the ResourcesConfig instance to a dictionary."""
    return {
        'project_name': self.project_name,
        'source_builds': {
            name: build.to_dict() for name, build in self.source_builds.items()
        },
        'secrets': {
            name: secret.to_dict() for name, secret in self.secrets.items()
        },
        'volumes': self.volumes.to_dict(),
    }

  def to_json(self) -> str:
    """Serializes the ResourcesConfig instance to a JSON string."""
    return json.dumps(self.to_dict())


def perform_source_build(
    source_build: Dict[str, BuildConfig],
    repo: str,
    project_name: str,
    region: str,
) -> None:
  """Performs source build across containers mentioned in the compose file."""
  for container, build_config in source_build.items():
    try:
      _build_from_source(build_config, container, repo, project_name, region)
    except submit_util.FailedBuildException as e:
      log.error(f'Build failed for container {container}: {e}')
      raise
    except exceptions.Error as e:
      log.error(f'An error occurred during build submission: {e}')
      raise


def _write_cloudbuild_config(context: str, image_tag: str) -> str:
  """Writes a cloudbuild.yaml file to the service source directory.

  Args:
    context: The build context directory.
    image_tag: The full tag for the image to be built.

  Returns:
    The path to the written cloudbuild.yaml file.
  """
  config_data = {
      'steps': [{
          'id': f'Build Docker Image: {image_tag}',
          'name': 'gcr.io/cloud-builders/docker',
          'args': ['buildx', 'build', '-t', image_tag, '.'],
      }],
      'images': [image_tag],
  }

  out_dir = os.path.join(context, 'out')
  file_path = os.path.join(out_dir, 'cloudbuild.yaml')
  try:
    files.MakeDir(out_dir)
    with files.FileWriter(file_path) as f:
      yaml.dump(config_data, f)
    log.debug(f"Wrote Cloud Build config to '{file_path}'")
    return file_path
  except Exception as e:
    raise exceptions.Error(
        f"Failed to write Cloud Build config to '{file_path}': {e}"
    )


def _build_from_source(
    config: BuildConfig,
    container: str,
    repo: str,
    project_name: str,
    region: str,
) -> None:
  """Performs source build for a given container using build config."""
  source_path = config.context
  if source_path is None:
    raise ValueError('Build context is required for source build.')

  image = '{repo}/{project_name}_{container}:{tag}'.format(
      repo=repo, project_name=project_name, container=container, tag='latest'
  )
  config.image_id = image

  # Write the cloudbuild.yaml file to the service source directory.
  config_path = _write_cloudbuild_config(
      source_path, image
  )

  # Get the Cloud Build API message module
  messages = cloudbuild_util.GetMessagesModule()

  # Create the build configuration. This will upload the source
  # and set up the build steps to use the Dockerfile.
  log.status.Print(
      f"Creating build config for image '{image}' from source '{source_path}'"
  )
  build_config = submit_util.CreateBuildConfig(
      tag=None,
      no_cache=False,
      messages=messages,
      substitutions=None,
      arg_config=config_path,
      is_specified_source=True,
      no_source=False,
      source=source_path,
      gcs_source_staging_dir=None,
      ignore_file=None,
      arg_gcs_log_dir=None,
      arg_machine_type=None,
      arg_disk_size=None,
      arg_worker_pool=None,
      arg_dir=None,
      arg_revision=None,
      arg_git_source_dir=None,
      arg_git_source_revision=None,
      arg_service_account=None,
      buildpack=None,
      hide_logs=False,
      # skip_set_source defaults to False, so SetSource is called internally
  )

  log.status.Print('Submitting build to Google Cloud Build')
  # Submit and wait for the build
  build, _ = submit_util.Build(
      messages,
      # TODO(b/381256138): optimize for parallel source builds
      async_=False,
      build_config=build_config,
      build_region=region,
  )
  log.status.Print(f'Build {build.id} finished with status {build.status}')
  log.status.Print(f"Image '{image}' created.")


def _create_secret_and_add_version(
    config: SecretConfig
) -> None:
  """Creates a secret if it doesn't exist and adds a version from a file."""
  if not config.secret_name or not config.file or not config.mount_name:
    raise ValueError('Secret name, file path and mount name are required.')

  if not os.path.exists(config.file):
    raise ValueError(f'Secret file not found: {config.file}')

  secrets_client = secrets_api.Secrets()
  project = properties.VALUES.core.project.Get(required=True)
  secret_ref = resources.REGISTRY.Parse(
      config.secret_name,
      params={'projectsId': project},
      collection='secretmanager.projects.secrets',
  )

  # Check if secret exists
  if secrets_client.GetOrNone(secret_ref) is None:
    log.status.Print(
        f"Creating secret '{config.secret_name}' in project '{project}'."
    )
    try:
      # Default replication policy is automatic
      secrets_client.Create(
          secret_ref,
          policy='automatic',
          locations=None,
          labels=None,
          tags=None,
      )
      log.status.Print(f"Secret '{config.secret_name}' created.")
    except Exception as e:
      log.error(f"Failed to create secret '{config.secret_name}': {e}")
      raise
  else:
    log.status.Print(f"Secret '{config.secret_name}' already exists.")

  # Add secret version
  try:
    log.status.Print(
        f"Reading secret content from '{config.file}' for secret"
        f" '{config.mount_name}'."
    )
    secret_data = files.ReadBinaryFileContents(config.file)

    log.status.Print(f"Adding new version to secret '{config.secret_name}'.")
    # data_crc32c is not calculated here, but could be added for integrity
    # TODO(b/440494739): Reuse secret values if unchanged
    version = secrets_client.AddVersion(
        secret_ref, secret_data, data_crc32c=None
    )
    config.secret_version = version.name
    log.status.Print(
        f"Added secret version '{config.secret_version}' to secret"
        f" '{config.secret_name}'."
    )
  except Exception as e:
    log.error(f"Failed to add version to secret '{config.secret_name}': {e}")
    raise


def _get_project_number() -> str:
  """Retrieves the project number for the current project."""

  project_id = properties.VALUES.core.project.Get(required=True)
  project = projects_api.GetProject(project_id)
  return str(project.projectNumber)
