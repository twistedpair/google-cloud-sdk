# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utility for working with secret environment variables and volumes for v1."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections

from googlecloudsdk.api_lib.functions.v1 import util
import six


def GetSecretsAsDict(function):
  """Converts secrets from message to flattened secrets configuration dict.

  Args:
    function: Cloud function message.

  Returns:
    Secrets configuration sorted ordered dict.
  """
  secrets_dict = {}
  if function.secretEnvironmentVariables:
    secrets_dict.update({
        secret_env_var.key:
        (secret_env_var.secret + ':' + secret_env_var.version)
        for secret_env_var in function.secretEnvironmentVariables
    })
  if function.secretVolumes:
    for secret_volume in function.secretVolumes:
      mount_path = secret_volume.mountPath
      secret = secret_volume.secret
      if secret_volume.versions:
        for version in secret_volume.versions:
          secret_version = version.version
          secret_file_path = version.path
          secrets_config_key = mount_path + ':' + secret_file_path
          secrets_config_value = secret + ':' + secret_version
          secrets_dict[secrets_config_key] = secrets_config_value
      else:
        secrets_config_key = mount_path + ':/' + secret
        secrets_config_value = secret + ':latest'
        secrets_dict[secrets_config_key] = secrets_config_value
  return collections.OrderedDict(sorted(six.iteritems(secrets_dict)))


def SecretEnvVarsToMessages(secret_env_vars_dict, project):
  """Converts secrets from dict to cloud function SecretEnvVar message list.

  Args:
    secret_env_vars_dict: Secret environment variables configuration dict.
      Prefers a sorted ordered dict for consistency.
    project: Project id of project that hosts the secret.

  Returns:
    A list of cloud function SecretEnvVar message.
  """
  secret_environment_variables = []
  messages = util.GetApiMessagesModule()
  for secret_env_var_key, secret_env_var_value in six.iteritems(
      secret_env_vars_dict):
    secret = secret_env_var_value.split(':')[0]
    version = secret_env_var_value.split(':')[1]
    secret_environment_variables.append(
        messages.SecretEnvVar(
            key=secret_env_var_key,
            projectId=project,
            secret=secret,
            version=version))
  return secret_environment_variables


def SecretVolumesToMessages(secret_volumes_dict, project):
  """Converts secrets from dict to cloud function SecretVolume message list.

  Args:
    secret_volumes_dict: Secrets volumes configuration dict. Prefers a sorted
      ordered dict for consistency.
    project: Project id of project that hosts the secret.

  Returns:
    A list of cloud function SecretVolume message.
  """
  secret_volumes_messages = []
  messages = util.GetApiMessagesModule()
  mount_path_to_secrets = collections.defaultdict(list)
  for secret_volume_key, secret_volume_value in six.iteritems(
      secret_volumes_dict):
    mount_path = secret_volume_key.split(':')[0]
    secret_file_path = secret_volume_key.split(':')[1]
    secret = secret_volume_value.split(':')[0]
    version = secret_volume_value.split(':')[1]
    mount_path_to_secrets[mount_path].append({
        'path': secret_file_path,
        'secret': secret,
        'version': version
    })
  mount_path_to_secrets = collections.OrderedDict(
      sorted(six.iteritems(mount_path_to_secrets)))
  for mount_path, secret_path_values in six.iteritems(mount_path_to_secrets):
    secret = secret_path_values[0]['secret']
    secret_version_messages = []
    for secret_path_value in secret_path_values:
      secret_version_messages.append(
          messages.SecretVersion(
              path=secret_path_value['path'],
              version=secret_path_value['version']))
    secret_volumes_messages.append(
        messages.SecretVolume(
            mountPath=mount_path,
            projectId=project,
            secret=secret,
            versions=secret_version_messages))
  return secret_volumes_messages
