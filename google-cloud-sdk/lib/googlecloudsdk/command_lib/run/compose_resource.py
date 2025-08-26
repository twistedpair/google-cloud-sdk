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
from typing import Any, Dict, Optional

from googlecloudsdk.api_lib.cloudbuild import cloudbuild_util
from googlecloudsdk.command_lib.builds import submit_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log


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


class SecretConfig:
  """Represents the secret configuration for a service."""

  def __init__(
      self, secret_name: Optional[str] = None, file: Optional[str] = None
  ):
    self.secret_name = secret_name
    self.file = file
    # secret_version is only set after the secret is created.
    self.secret_version: Optional[str] = None

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'SecretConfig':
    return cls(
        secret_name=data.get('secret_name'),
        file=data.get('file'),
    )


class ResourcesConfig:
  """Represents the resources config sent form runcompose go binary."""

  def __init__(
      self,
      source_builds: Optional[Dict[str, BuildConfig]] = None,
      secrets: Optional[Dict[str, SecretConfig]] = None,
      project_name: Optional[str] = None,
  ):
    self.source_builds = source_builds if source_builds is not None else {}
    self.secrets = secrets if secrets is not None else {}
    self.project_name = project_name

  @classmethod
  def from_json(cls, json_data: str) -> 'ResourcesConfig':
    """Parses the JSON string to create a ResourcesConfig instance."""
    data = json.loads(json_data)
    return cls.from_dict(data)

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
    project_name = data.get('project_name')
    return cls(
        source_builds=source_builds, secrets=secrets, project_name=project_name
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

  # Get the Cloud Build API message module
  messages = cloudbuild_util.GetMessagesModule()
  try:
    # Create the build configuration. This will upload the source
    # and set up the build steps to use the Dockerfile.
    log.status.Print(
        f"Creating build config for image '{image}' from source '{source_path}'"
    )
    build_config = submit_util.CreateBuildConfig(
        tag=image,
        no_cache=False,
        messages=messages,
        substitutions=None,
        arg_config=None,
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

  except submit_util.FailedBuildException as e:
    log.error(f'Build failed: {e}')
  except exceptions.Error as e:
    log.error(f'An error occurred during build submission: {e}')
