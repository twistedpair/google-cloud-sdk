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
import re

from googlecloudsdk.api_lib.functions.v1 import util
import six


_SECRET_VERSION_RESOURCE_PATTERN = re.compile(
    '^projects/(?P<project>[^/]+)/secrets/(?P<secret>[^/]+)'
    '/versions/(?P<version>[^/]+)$')


def _GetSecretVersionResource(project, secret, version):
  return 'projects/{project}/secrets/{secret}/versions/{version}'.format(
      project=project or '*', secret=secret, version=version)


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
        sev.key: _GetSecretVersionResource(sev.projectId, sev.secret,
                                           sev.version)
        for sev in function.secretEnvironmentVariables
    })
  if function.secretVolumes:
    for secret_volume in function.secretVolumes:
      mount_path = secret_volume.mountPath
      project = secret_volume.projectId
      secret = secret_volume.secret
      if secret_volume.versions:
        for version in secret_volume.versions:
          secrets_config_key = mount_path + ':' + version.path
          secrets_config_value = _GetSecretVersionResource(
              project, secret, version.version)
          secrets_dict[secrets_config_key] = secrets_config_value
      else:
        secrets_config_key = mount_path + ':/' + secret
        secrets_config_value = _GetSecretVersionResource(
            project, secret, 'latest')
        secrets_dict[secrets_config_key] = secrets_config_value
  return collections.OrderedDict(sorted(six.iteritems(secrets_dict)))


def _ParseSecretRef(secret_ref):
  """Splits a secret version resource into its components.

  Args:
    secret_ref: Secret version resource reference.

  Returns:
    A dict with entries for project, secret and version.
  """
  secret_ref_match = _SECRET_VERSION_RESOURCE_PATTERN.search(secret_ref)
  return {
      'project': secret_ref_match.group('project'),
      'secret': secret_ref_match.group('secret'),
      'version': secret_ref_match.group('version'),
  }


def SecretEnvVarsToMessages(secret_env_vars_dict):
  """Converts secrets from dict to cloud function SecretEnvVar message list.

  Args:
    secret_env_vars_dict: Secret environment variables configuration dict.
      Prefers a sorted ordered dict for consistency.

  Returns:
    A list of cloud function SecretEnvVar message.
  """
  secret_environment_variables = []
  messages = util.GetApiMessagesModule()
  for secret_env_var_key, secret_env_var_value in six.iteritems(
      secret_env_vars_dict):
    secret_ref = _ParseSecretRef(secret_env_var_value)
    secret_environment_variables.append(
        messages.SecretEnvVar(
            key=secret_env_var_key,
            projectId=secret_ref['project'],
            secret=secret_ref['secret'],
            version=secret_ref['version']))
  return secret_environment_variables


def SecretVolumesToMessages(secret_volumes_dict):
  """Converts secrets from dict to cloud function SecretVolume message list.

  Args:
    secret_volumes_dict: Secrets volumes configuration dict. Prefers a sorted
      ordered dict for consistency.

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
    secret_ref = _ParseSecretRef(secret_volume_value)
    mount_path_to_secrets[mount_path].append({
        'path': secret_file_path,
        'project': secret_ref['project'],
        'secret': secret_ref['secret'],
        'version': secret_ref['version']
    })
  mount_path_to_secrets = collections.OrderedDict(
      sorted(six.iteritems(mount_path_to_secrets)))
  for mount_path, secret_path_values in six.iteritems(mount_path_to_secrets):
    project = secret_path_values[0]['project']
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
