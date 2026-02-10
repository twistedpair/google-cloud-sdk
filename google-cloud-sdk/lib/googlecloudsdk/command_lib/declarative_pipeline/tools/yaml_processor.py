# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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
"""Common utilities for Declarative Pipeline commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.command_lib.declarative_pipeline import deployment_model
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files

ARTIFACT_STORAGE_KEY = "artifact_storage"
ENVIRONMENTS_KEY = "environments"
VARIABLES_KEY = "variables"
RESOURCES_KEY = "resources"


class BadFileError(exceptions.Error):
  """Raised when the file is not valid."""

  pass


def _resolve_string_templates(yaml_content, variables):
  for key, value in variables.items():
    placeholder_pattern = r"{{\s*" + re.escape(key) + r"\s*}}"
    yaml_content = re.sub(placeholder_pattern, str(value), yaml_content)
  return yaml_content


def resolve_dynamic_variables(yaml_content, deployment_path, env):
  """Resolves the dynamic variables in the YAML file by substituting environment variables.

  Args:
    yaml_content: The content of the YAML file to be resolved.
    deployment_path: The path to the deployment configuration YAML file.
    env: The environment to use (e.g., "dev", "staging", "prod").

  Returns:
    The resolved_yaml_content YAML file content as a string.
  """

  validate_deployment(deployment_path, env)
  parsed_deployment = parse_deployment(deployment_path, env)

  combined_variables = {
      "project": parsed_deployment["project"],
      "region": parsed_deployment["region"],
      VARIABLES_KEY: parsed_deployment[VARIABLES_KEY],
  }
  nested_vars = combined_variables.pop(VARIABLES_KEY, {})
  if nested_vars:
    combined_variables.update(nested_vars)

  resolved_resource_profile = _resolve_resource_profile(parsed_deployment)
  resolved_yaml_content = _resolve_string_templates(
      yaml_content, combined_variables
  )
  try:
    resolved_yaml_content = yaml.load(resolved_yaml_content)
  except yaml.YAMLParseError as e:
    raise BadFileError(
        f"Failed to parse pipeline YAML after variable substitution:: {e}"
    )

  if (
      isinstance(resolved_yaml_content, dict)
      and "actions" in resolved_yaml_content
  ):
    resolved_yaml_content = _resolve_pipeline_yaml(
        resolved_yaml_content, resolved_resource_profile, parsed_deployment
    )
  return resolved_yaml_content


def _resolve_resource_profile(deployment):
  """Resolves the resource profile."""
  profile_resource = next(
      (r for r in deployment[RESOURCES_KEY] if r.type == "resourceProfile"),
      None,
  )
  resource_profile = {}
  if profile_resource and hasattr(profile_resource, "source"):
    try:
      raw_profile_content = files.ReadFileContents(profile_resource.source)
      resolved_profile_str = _resolve_string_templates(
          raw_profile_content, deployment[VARIABLES_KEY]
      )
      resource_profile = yaml.load(resolved_profile_str)
    except (IOError, OSError, yaml.Error) as e:
      raise BadFileError(
          "Error reading or parsing resource profile"
          f" '{profile_resource.source}': {e}"
      ) from e
  return resource_profile


def _resolve_pipeline_yaml(yaml_content, resource_profile, deployment):
  """Resolves pipeline specific configurations within the YAML content.

  This function injects artifact storage details and resource profile
  definitions
  into the actions defined in the pipeline YAML.

  Args:
    yaml_content: The parsed YAML content of the pipeline.
    resource_profile: The resolved resource profile.
    deployment: A dictionary containing deployment-specific configurations,
      including "resources" and "artifact_storage".

  Returns:
    The modified YAML content with pipeline configurations resolved.

  Raises:
    ValueError: If there is an error reading the resource profile file.
  """
  profile_definition = {}
  if resource_profile:
    profile_definition = resource_profile.get("definition", {})

  for action in yaml_content.get("actions", []):
    action["depsBucket"] = deployment[ARTIFACT_STORAGE_KEY]["bucket"]
    if "script" in action and "mainPythonFileUri" in action["script"]:
      action["filename"] = action["script"]["mainPythonFileUri"]
      del action["script"]["mainPythonFileUri"]
      if not action["script"]:
        del action["script"]
    config = action.setdefault("config", {})
    session_template = config.setdefault("sessionTemplate", {})
    session_template["inline"] = profile_definition

  return yaml_content


def validate_deployment(deployment_path, env):
  """Validates the deployment configuration."""
  try:
    deployment_yaml = yaml.load_path(str(deployment_path))
  except yaml.YAMLParseError as e:
    raise BadFileError(f"Error parsing deployment.yaml: {e}")

  try:
    deployment = deployment_model.DeploymentModel.build(deployment_yaml)
  except (KeyError, TypeError, ValueError, AttributeError) as e:
    raise BadFileError(f"Error parsing deployment configuration: {e}") from e

  environments = getattr(deployment, ENVIRONMENTS_KEY)

  if env not in environments:
    raise BadFileError(f"Environment '{env}' not found in deployment file.")

  environment = environments[env]

  if not isinstance(environment, deployment_model.EnvironmentModel):
    raise BadFileError(
        f"Environment '{env}' is not a valid object in deployment file."
    )
  if environment.artifact_storage:
    if not isinstance(
        environment.artifact_storage,
        deployment_model.ArtifactStorageModel,
    ):
      raise BadFileError(
          f"Environment '{env}' has invalid artifact_storage in deployment"
          " file."
      )
  if not environment.resources:
    raise BadFileError(
        f"Environment '{env}' has no resources in deployment file."
    )
  if not environment.variables:
    log.info(f"Environment '{env}' has no variables in deployment file.")
  else:
    if not isinstance(environment.variables, dict):
      raise BadFileError(
          f"Error: '{VARIABLES_KEY}' for environment '{env}' in deployment.yaml"
          " is not a dictionary"
      )
  return deployment


def parse_deployment(deployment_path, env):
  """Extracts storage and environment specific configuration."""
  deployment = validate_deployment(deployment_path, env)
  environments = getattr(deployment, ENVIRONMENTS_KEY)
  environment = environments[env]
  artifact_storage = environment.artifact_storage
  if artifact_storage:
    artifact_storage = {
        "bucket": artifact_storage.bucket,
        "path_prefix": artifact_storage.path_prefix,
    }

  return {
      ARTIFACT_STORAGE_KEY: {
          "bucket": artifact_storage["bucket"],
          "path_prefix": artifact_storage["path_prefix"],
      },
      "project": environment.project,
      "region": environment.region,
      "composer_env": environment.composer_environment,
      "variables": environment.variables,
      "resources": environment.resources,
  }
