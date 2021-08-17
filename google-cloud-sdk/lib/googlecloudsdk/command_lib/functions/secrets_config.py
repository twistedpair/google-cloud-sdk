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
"""Utility for configuring and parsing secrets args."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import re

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope.arg_parsers import ArgumentTypeError
from googlecloudsdk.core import log
import six

_SECRET_PATH_PATTERN = re.compile('^(/+[a-zA-Z0-9-_.]*[a-zA-Z0-9-_]+)+'
                                  '((/*:(/*[a-zA-Z0-9-_.]*[a-zA-Z0-9-_]+)+)'
                                  '|(/+[a-zA-Z0-9-_.]*[a-zA-Z0-9-_]+))$')

_DEFAULT_PROJECT_SECRET_REF_PATTERN = re.compile(
    '^(?P<secret>[a-zA-Z0-9-_]+):(?P<version>[1-9][0-9]*|latest)$')
_SECRET_VERSION_RESOURCE_REF_PATTERN = re.compile(
    '^projects/([^/]+)/secrets/([a-zA-Z0-9-_]+)/versions/([1-9][0-9]*|latest)$')
_SECRET_VERSION_REF_PATTERN = re.compile(
    '^projects/(?P<project>[^/]+)/secrets/(?P<secret>[a-zA-Z0-9-_]+)'
    ':(?P<version>[1-9][0-9]*|latest)$')

_DEFAULT_PROJECT_IDENTIFIER = '*'

_SECRET_VERSION_SECRET_RESOURCE_PATTERN = re.compile(
    '^(?P<secret_resource>projects/[^/]+/secrets/[a-zA-Z0-9-_]+)'
    '/versions/(?P<version>[1-9][0-9]*|latest)$')
_SECRET_RESOURCE_PATTERN = re.compile(
    '^projects/(?P<project>[^/]+)/secrets/(?P<secret>[a-zA-Z0-9-_]+)$')


def _CanonicalizePath(secret_path):
  """Canonicalizes secret path to the form `/mount_path:/secret_file_path`.

  Gcloud secret path is more restrictive than the backend (shortn/_bwgb3xdRxL).
  Paths are reduced to their canonical forms before the request is made.

  Args:
    secret_path: Complete path to the secret.

  Returns:
    Canonicalized secret path.
  """
  secret_path = re.sub(r'/+', '/', secret_path)
  mount_path, _, secret_file_path = secret_path.rpartition('/')
  if ':' in secret_path:
    mount_path, _, secret_file_path = secret_path.partition(':')
  mount_path = mount_path[:-1] if mount_path.endswith('/') else mount_path
  secret_file_path = '/' + secret_file_path if not secret_file_path.startswith(
      '/') else secret_file_path
  return mount_path + ':' + secret_file_path


def _SecretsKeyType(key):
  """Validates and canonicalizes secrets key configuration.

  Args:
    key: Secrets key configuration.

  Returns:
    Canonicalized secrets key configuration.

  Raises:
    ArgumentTypeError: Secrets key configuration is not valid.
  """
  if not key.strip():
    raise ArgumentTypeError(
        'Secret environment variable names/secret paths cannot be empty.')
  canonicalized_key = key
  if _SECRET_PATH_PATTERN.search(key):
    canonicalized_key = _CanonicalizePath(key)
  else:
    if '/' in key:
      log.warning("'{}' will be interpreted as a secret environment variable "
                  "name as it doesn't match the pattern for a secret path "
                  "'/mount_path:/secret_file_path'.".format(key))
    if key.startswith('X_GOOGLE_') or key in [
        'GOOGLE_ENTRYPOINT', 'GOOGLE_FUNCTION_TARGET', 'GOOGLE_RUNTIME',
        'GOOGLE_RUNTIME_VERSION'
    ]:
      raise ArgumentTypeError(
          "Secret environment variable name '{}' is reserved for internal "
          'use.'.format(key))
  return canonicalized_key


def _CanonicalizeValue(value):
  """Canonicalizes secret value reference to the secret version resource name.

  Output format: `projects/{project}/secrets/{secret}/versions/{version}`.
  The project in the above reference will be * if the user used a default
  project secret.

  Args:
    value: Secret value reference as a string.

  Returns:
    Canonicalized secret value reference.
  """
  dp_secret_ref_match = _DEFAULT_PROJECT_SECRET_REF_PATTERN.search(value)
  secret_version_res_ref_match = _SECRET_VERSION_RESOURCE_REF_PATTERN.search(
      value)
  secret_version_ref_match = _SECRET_VERSION_REF_PATTERN.search(value)

  if dp_secret_ref_match:
    return 'projects/{project}/secrets/{secret}/versions/{version}'.format(
        project=_DEFAULT_PROJECT_IDENTIFIER,
        secret=dp_secret_ref_match.group('secret'),
        version=dp_secret_ref_match.group('version'))
  elif secret_version_res_ref_match:
    return value
  elif secret_version_ref_match:
    return 'projects/{project}/secrets/{secret}/versions/{version}'.format(
        project=secret_version_ref_match.group('project'),
        secret=secret_version_ref_match.group('secret'),
        version=secret_version_ref_match.group('version'))
  raise ArgumentTypeError(
      "Secrets value configuration must match the pattern 'SECRET:VERSION' or "
      "'projects/{{PROJECT}}/secrets/{{SECRET}}:{{VERSION}}' or "
      "'projects/{{PROJECT}}/secrets/{{SECRET}}/versions/{{VERSION}}' "
      "where VERSION is a number or the label 'latest' [{}]".format(value))


def _SecretsValueType(value):
  """Validates secrets value configuration.

  The restrictions for gcloud are strict when compared to GCF to accommodate
  future changes without making it confusing for the user.

  Args:
    value: Secrets value configuration.

  Returns:
    Secrets value configuration as a string.

  Raises:
    ArgumentTypeError: Secrets value configuration is not valid.
  """
  if '=' in value:
    raise ArgumentTypeError(
        "Secrets value configuration cannot contain '=' [{}]".format(value))
  return _CanonicalizeValue(value)


def _SecretsDiffer(project1, secret1, project2, secret2):
  """Returns true if the two secrets differ.

  The secrets can be considered as different if either the secret name is
  different or the project is different with the secret name being the same. If
  one project is represented using the project number and the other is
  represented using its project id, then it may not be possible to determine if
  the two projects are the same, so the validation is relaxed.

  Args:
    project1: Project ID or number of the first secret.
    secret1: Secret name of the first secret.
    project2: Project ID or number of the second secret.
    secret2: Secret name of the second secret.

  Returns:
    True if the two secrets differ, False otherwise.
  """
  return (secret1 != secret2 or
          (project1 != project2 and
           project1.isnumeric() == project2.isnumeric() and
           project1 != _DEFAULT_PROJECT_IDENTIFIER and
           project2 != _DEFAULT_PROJECT_IDENTIFIER))


def _ValidateSecrets(secrets_dict):
  """Additional secrets validations that require the entire dict.

  Args:
    secrets_dict: Secrets configuration dict to validate.
  """
  mount_path_to_secret = collections.defaultdict(list)
  for key, value in six.iteritems(secrets_dict):
    if _SECRET_PATH_PATTERN.search(key):
      mount_path = key.split(':')[0]
      secret_res1 = _SECRET_VERSION_SECRET_RESOURCE_PATTERN.search(value).group(
          'secret_resource')

      if mount_path in mount_path_to_secret:
        secret_res_match1 = _SECRET_RESOURCE_PATTERN.search(secret_res1)
        project1 = secret_res_match1.group('project')
        secret1 = secret_res_match1.group('secret')

        for secret_res2 in mount_path_to_secret[mount_path]:
          secret_res_match2 = _SECRET_RESOURCE_PATTERN.search(secret_res2)
          project2 = secret_res_match2.group('project')
          secret2 = secret_res_match2.group('secret')

          if _SecretsDiffer(project1, secret1, project2, secret2):
            raise ArgumentTypeError(
                'More than one secret is configured for the mount path '
                "'{mount_path}' [violating secrets: {secret1},{secret2}]."
                .format(
                    mount_path=mount_path,
                    secret1=secret1
                    if project1 == _DEFAULT_PROJECT_IDENTIFIER else secret_res1,
                    secret2=secret2 if project2 == _DEFAULT_PROJECT_IDENTIFIER
                    else secret_res2))
      else:
        mount_path_to_secret[mount_path].append(secret_res1)


class ArgSecretsDict(arg_parsers.ArgDict):
  """ArgDict customized for holding secrets configuration."""

  def __init__(self,
               key_type=None,
               value_type=None,
               spec=None,
               min_length=0,
               max_length=None,
               allow_key_only=False,
               required_keys=None,
               operators=None):
    """Initializes the base ArgDict by forwarding the parameters."""
    super(ArgSecretsDict, self).__init__(
        key_type=key_type,
        value_type=value_type,
        spec=spec,
        min_length=min_length,
        max_length=max_length,
        allow_key_only=allow_key_only,
        required_keys=required_keys,
        operators=operators)

  def __call__(self, arg_value):  # pylint:disable=missing-docstring
    secrets_dict = collections.OrderedDict(
        sorted(six.iteritems(super(ArgSecretsDict, self).__call__(arg_value))))
    _ValidateSecrets(secrets_dict)
    return secrets_dict


def ConfigureFlags(parser):
  """Add flags for configuring secret environment variables and secret volumes.

  Args:
    parser: Argument parser.
  """
  kv_metavar = ('SECRET_ENV_VAR=SECRET_VALUE_REF,'
                '/secret_path=SECRET_VALUE_REF,'
                '/mount_path:/secret_file_path=SECRET_VALUE_REF')
  k_metavar = 'SECRET_ENV_VAR,/secret_path,/mount_path:/secret_file_path'

  flag_group = parser.add_mutually_exclusive_group()
  flag_group.add_argument(
      '--set-secrets',
      metavar=kv_metavar,
      action=arg_parsers.UpdateAction,
      type=ArgSecretsDict(
          key_type=_SecretsKeyType, value_type=_SecretsValueType),
      help="""
      List of secret environment variables and secret volumes to configure.
      Existing secrets configuration will be overwritten.

      You can reference a secret value referred to as `SECRET_VALUE_REF` in the
      help text in the following ways.

      * Use `${SECRET}:${VERSION}` if you are referencing a secret in the same
        project, where `${SECRET}` is the name of the secret in secret manager
        (not the full resource name) and `${VERSION}` is the version of the
        secret which is either a `positive integer` or the label `latest`.
        For example, use `SECRET_FOO:1` to reference version `1` of the secret
        `SECRET_FOO` which exists in the same project as the function.

      * Use `projects/${PROJECT}/secrets/${SECRET}/versions/${VERSION}` or
        `projects/${PROJECT}/secrets/${SECRET}:${VERSION}` to reference a secret
        version using the full resource name, where `${PROJECT}` is either the
        project number (`preferred`) or the project ID of the project which
        contains the secret, `${SECRET}` is the name of the secret in secret
        manager (not the full resource name) and `${VERSION}` is the version of
        the secret which is either a `positive integer` or the label `latest`.
        For example, use `projects/1234567890/secrets/SECRET_FOO/versions/1` or
        `projects/project_id/secrets/SECRET_FOO/versions/1` to reference version
        `1` of the secret `SECRET_FOO` that exists in the project `1234567890`
        or `project_id` respectively.
        This format is useful when the secret exists in a different project.

      To configure the secret as an environment variable, use
      `SECRET_ENV_VAR=SECRET_VALUE_REF`. To use the value of the secret, read
      the environment variable `SECRET_ENV_VAR` as you would normally do in the
      function's programming language.

      We recommend using a `numeric` version for secret environment variables
      as any updates to the secret value are not reflected until new clones
      start.

      To mount the secret within a volume use `/secret_path=SECRET_VALUE_REF` or
      `/mount_path:/secret_file_path=SECRET_VALUE_REF`. To use the value of the
      secret, read the file at `/secret_path` as you would normally do in the
      function's programming language.

      For example, `/etc/secrets/secret_foo=SECRET_FOO:latest` or
      `/etc/secrets:/secret_foo=SECRET_FOO:latest` will make the value of the
      `latest` version of the secret `SECRET_FOO` available in a file
      `secret_foo` under the directory `/etc/secrets`. `/etc/secrets` will be
      considered as the `mount path` and will `not` be available for any other
      volume.

      We recommend referencing the `latest` version when using secret volumes so
      that the secret's value changes are reflected immediately.""")

  update_remove_flag_group = flag_group.add_argument_group(help="""
      Only `--update-secrets` and `--remove-secrets` can be used together. If
      both are specified, then `--remove-secrets` will be applied first.""")
  update_remove_flag_group.add_argument(
      '--update-secrets',
      metavar=kv_metavar,
      action=arg_parsers.UpdateAction,
      type=ArgSecretsDict(
          key_type=_SecretsKeyType, value_type=_SecretsValueType),
      help="""
      List of secret environment variables and secret volumes to update.
      Existing secrets configuration not specified in this list will be
      preserved.""")
  update_remove_flag_group.add_argument(
      '--remove-secrets',
      metavar=k_metavar,
      action=arg_parsers.UpdateAction,
      type=arg_parsers.ArgList(element_type=_SecretsKeyType),
      help="""
      List of secret environment variable names and secret paths to remove.

      Existing secrets configuration of secret environment variable names and
      secret paths not specified in this list will be preserved.

      To remove a secret environment variable, use the name of the environment
      variable `SECRET_ENV_VAR`.

      To remove a file within a secret volume or the volume itself, use the
      secret path as the key (either `/secret_path` or
      `/mount_path:/secret_file_path`).""")

  flag_group.add_argument(
      '--clear-secrets',
      action='store_true',
      help='Remove all secret environment variables and volumes.')


def IsArgsSpecified(args):
  """Returns true if at least one of the flags for secrets is specified.

  Args:
    args: Argparse namespace.

  Returns:
    True if at least one of the flags for secrets is specified.
  """
  secrets_flags = {
      '--set-secrets', '--update-secrets', '--remove-secrets', '--clear-secrets'
  }
  specified_flags = set(args.GetSpecifiedArgNames())
  return bool(specified_flags.intersection(secrets_flags))


def _SplitSecretsDict(secrets_dict):
  """Splits the secrets dict into sorted ordered dicts for every secret type.

  Args:
    secrets_dict: Secrets configuration dict.

  Returns:
    A new dict of sorted ordered dicts for every secret type.
  """
  secrets_dict_by_type = {}
  secret_env_var_dict = {}
  secret_path_dict = {}
  for secret_key, secret_value in six.iteritems(secrets_dict):
    if _SECRET_PATH_PATTERN.search(secret_key):
      secret_path_dict[secret_key] = secret_value
    else:
      secret_env_var_dict[secret_key] = secret_value
  secrets_dict_by_type[
      'secret_environment_variables'] = collections.OrderedDict(
          sorted(six.iteritems(secret_env_var_dict)))
  secrets_dict_by_type['secret_volumes'] = collections.OrderedDict(
      sorted(six.iteritems(secret_path_dict)))
  return secrets_dict_by_type


def _CanonicalizeKey(key):
  """Canonicalizes secrets configuration key.

  Args:
    key: Secrets configuration key.

  Returns:
    Canonicalized secrets configuration key.
  """
  if _SECRET_PATH_PATTERN.search(key):
    return _CanonicalizePath(key)
  return key


def _CanonicalizedDict(secrets_dict):
  """Canonicalizes all keys in the dict and returns a new dict.

  Args:
    secrets_dict: Existing secrets configuration dict.

  Returns:
    Canonicalized secrets configuration dict.
  """
  return collections.OrderedDict(
      sorted(
          six.iteritems({
              _CanonicalizeKey(key): value
              for (key, value) in secrets_dict.items()
          })))


def _SubstituteDefaultProject(secret_version_ref, default_project_id,
                              default_project_number):
  """Replaces the default project number in place of * or project ID.

  Args:
    secret_version_ref: Secret value reference.
    default_project_id: The project ID of the project to which the function is
      deployed.
    default_project_number: The project number of the project to which the
      function is deployed.

  Returns:
    Secret value reference with * or project ID replaced by the default project.
  """
  return re.sub(
      r'projects/([*]|{project_id})/'.format(project_id=default_project_id),
      'projects/{project_number}/'.format(
          project_number=default_project_number), secret_version_ref)


def ApplyFlags(old_secrets_dict, args, default_project_id,
               default_project_number):
  """Applies the current flags to existing secrets configuration.

  Args:
    old_secrets_dict: Existing secrets configuration dict.
    args: Argparse namespace.
    default_project_id: The project ID of the project to which the function is
      deployed.
    default_project_number: The project number of the project to which the
      function is deployed.

  Returns:
    new_secrets_dict_by_type: A new dict of ordered dicts, one for every secret
      type that holds the secrets configuration for that type generated by
      applying the flags to the existing secrets configuration.
    needs_update: A dict with an entry for every secret type that holds a
      boolean value which indicates if the secret configuration for that type
      needs to be updated.

  Raises:
    ArgumentTypeError: Generated secrets configuration is invalid.
  """
  specified_args = args.GetSpecifiedArgs()
  set_flag_value = specified_args.get('--set-secrets')
  update_flag_value = specified_args.get('--update-secrets')
  remove_flag_value = specified_args.get('--remove-secrets')
  clear_flag_value = specified_args.get('--clear-secrets')

  old_secrets_dict = old_secrets_dict or {}
  old_secrets_dict_by_type = _SplitSecretsDict(old_secrets_dict)
  new_secrets_dict = old_secrets_dict
  new_secrets_dict_by_type = old_secrets_dict_by_type
  needs_update = {}
  if clear_flag_value:
    new_secrets_dict = {}
  elif set_flag_value:
    new_secrets_dict = set_flag_value
  elif update_flag_value or remove_flag_value:
    old_secrets_dict = _CanonicalizedDict(old_secrets_dict)
    update_flag_value = update_flag_value or {}
    remove_flag_value = remove_flag_value or []
    new_secrets_dict = {
        key: value
        for (key, value) in six.iteritems(old_secrets_dict)
        if key not in remove_flag_value
    }
    new_secrets_dict.update(update_flag_value)
  else:
    return old_secrets_dict_by_type, {
        'secret_environment_variables': False,
        'secret_volumes': False
    }

  new_secrets_dict = {
      secrets_key: _SubstituteDefaultProject(secrets_value, default_project_id,
                                             default_project_number)
      for secrets_key, secrets_value in six.iteritems(new_secrets_dict)
  }
  new_secrets_dict = collections.OrderedDict(
      sorted(six.iteritems(new_secrets_dict)))
  # Handles the case when the newly configured secrets could conflict with
  # existing secrets.
  _ValidateSecrets(new_secrets_dict)

  new_secrets_dict_by_type = _SplitSecretsDict(new_secrets_dict)
  needs_update['secret_environment_variables'] = old_secrets_dict_by_type[
      'secret_environment_variables'] != new_secrets_dict_by_type[
          'secret_environment_variables']
  needs_update['secret_volumes'] = old_secrets_dict_by_type[
      'secret_volumes'] != new_secrets_dict_by_type['secret_volumes']
  return new_secrets_dict_by_type, needs_update
