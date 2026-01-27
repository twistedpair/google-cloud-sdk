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

from googlecloudsdk.core import log
from googlecloudsdk.core import yaml

ENVIRONMENTS_KEY = "environments"
VARIABLES_KEY = "variables"


def resolve_dynamic_variables(yaml_content, deployment_yaml, env):
  """Resolves the dynamic variables in the YAML file by substituting environment variables.

  Args:
    yaml_content: The content of the YAML file to be resolved. file.
    deployment_yaml: The content of the deployment configuration YAML file.
    env: The environment to use (e.g., "dev", "staging", "prod").

  Returns:
    The resolved_yaml_content YAML file content as a string.
  """

  try:
    deployment_data = yaml.load(deployment_yaml)
  except yaml.YAMLParseError as e:
    raise ValueError("Error parsing deployment.yaml: {}".format(e))

  if ENVIRONMENTS_KEY not in deployment_data:
    raise ValueError("Error: 'environments' not found in deployment.yaml")

  environments = deployment_data[ENVIRONMENTS_KEY]
  if not isinstance(environments, dict):
    raise ValueError(
        f"Error: '{ENVIRONMENTS_KEY}' in deployment.yaml is not a dictionary"
    )
  if env not in environments:
    raise ValueError(f"Error: Environment '{env}' not found in deployment.yaml")

  env_data = environments[env]
  if not isinstance(env_data, dict):
    raise ValueError(
        f"Error: Data for environment '{env}' in deployment.yaml is not a"
        " dictionary"
    )

  combined_variables = {}
  combined_variables["project"] = env_data.get("project", None)
  combined_variables["region"] = env_data.get("region", None)

  if VARIABLES_KEY not in env_data:
    log.info("No variables found in %s dictionary", env)
  else:
    variables = env_data.get(VARIABLES_KEY, {})
    if not isinstance(variables, dict):
      raise ValueError(
          f"Error: '{VARIABLES_KEY}' for environment '{env}' in deployment.yaml"
          " is not a dictionary"
      )
    combined_variables.update(variables)

  resolved_yaml_content = yaml_content
  for key, value in combined_variables.items():
    placeholder_pattern = r"{{\s*" + re.escape(key) + r"\s*}}"
    resolved_yaml_content = re.sub(
        placeholder_pattern, str(value), resolved_yaml_content
    )

  return resolved_yaml_content
