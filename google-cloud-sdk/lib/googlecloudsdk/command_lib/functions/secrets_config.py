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

_SECRET_PATH_PATTERN = re.compile('^(/+[a-zA-Z0-9-_.]*[a-zA-Z0-9-_]+)+/*:'
                                  '(/*[a-zA-Z0-9-_.]*[a-zA-Z0-9-_]+)+$')
_SECRET_VALUE_PATTERN = re.compile('^[a-zA-Z0-9-_]+:([1-9][0-9]*|latest)$')


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


def _SecretsValueType(value):
  """Validates secrets value configuration.

  The restrictions for gcloud are strict when compared to GCF to accommodate
  future changes without making it confusing for the user.

  Args:
    value: Secrets value configuration.

  Returns:
    Secrets value configuration.

  Raises:
    ArgumentTypeError: Secrets value configuration is not valid.
  """
  if '=' in value:
    raise ArgumentTypeError(
        "Secrets value configuration cannot contain '=' [{}]".format(value))
  if not _SECRET_VALUE_PATTERN.search(value):
    raise ArgumentTypeError(
        "Secrets value configuration must match the pattern 'SECRET:VERSION' "
        "where VERSION is a number or the label 'latest' [{}]".format(value))
  return value


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

  @staticmethod
  def ValidateSecrets(secrets_dict):
    """Additional secrets validations that require the entire dict.

    This method is static so that it can be used to validate secrets dict
    generated from secrets args.

    Args:
      secrets_dict: Secrets configuration dict to validate.
    """
    mount_path_to_secret = {}
    for key, value in six.iteritems(secrets_dict):
      if _SECRET_PATH_PATTERN.search(key):
        mount_path = key.split(':')[0]
        secret = value.split(':')[0]
        if mount_path in mount_path_to_secret and mount_path_to_secret[
            mount_path] != secret:
          raise ArgumentTypeError(
              'More than one secret is configured for the mount path '
              "'{mount_path}' [violating secrets: {secret1},{secret2}].".format(
                  mount_path=mount_path,
                  secret1=mount_path_to_secret[mount_path],
                  secret2=secret))
        else:
          mount_path_to_secret[mount_path] = value.split(':')[0]

  def __call__(self, arg_value):  # pylint:disable=missing-docstring
    secrets_dict = collections.OrderedDict(
        sorted(six.iteritems(super(ArgSecretsDict, self).__call__(arg_value))))
    ArgSecretsDict.ValidateSecrets(secrets_dict)
    return secrets_dict


def ConfigureFlags(parser):
  """Add flags for configuring secret environment variables and secret volumes.

  Args:
    parser: Argument parser.
  """
  kv_metavar = ('SECRET_ENV_VAR=SECRET:VERSION,'
                '/mount_path:/secret_file_path=SECRET:VERSION')
  k_metavar = 'SECRET_ENV_VAR,/mount_path:/secret_file_path'

  flag_group = parser.add_mutually_exclusive_group()
  flag_group.add_argument(
      '--set-secrets',
      metavar=kv_metavar,
      action=arg_parsers.UpdateAction,
      type=ArgSecretsDict(
          key_type=_SecretsKeyType, value_type=_SecretsValueType),
      help=('List of secret environment variables and secret volumes to '
            'configure. Existing secrets configuration will be overwritten.'))
  update_remove_flag_group = flag_group.add_argument_group(
      help=('Only `--update-secrets` and `--remove-secrets` can be used '
            'together. If both are specified, then `--remove-secrets` will be '
            'applied first.'))
  update_remove_flag_group.add_argument(
      '--update-secrets',
      metavar=kv_metavar,
      action=arg_parsers.UpdateAction,
      type=ArgSecretsDict(
          key_type=_SecretsKeyType, value_type=_SecretsValueType),
      help=('List of secret environment variables and secret volumes to '
            'update. Existing secrets configuration not specified in this list '
            'will be preserved.'))
  update_remove_flag_group.add_argument(
      '--remove-secrets',
      metavar=k_metavar,
      action=arg_parsers.UpdateAction,
      type=arg_parsers.ArgList(element_type=_SecretsKeyType),
      help=('List of secret environment variable names and secret paths to '
            'remove. Existing secrets configuration of secret environment '
            'variable names and secret paths not specified in this list will '
            'be preserved.'))
  flag_group.add_argument(
      '--clear-secrets',
      action='store_true',
      help='Remove all secret environment variables and volumes.')


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


def ApplyFlags(old_secrets_dict, args):
  """Applies the current flags to existing secrets configuration.

  Args:
    old_secrets_dict: Existing secrets configuration dict.
    args: All CLI arguments.

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

  new_secrets_dict = collections.OrderedDict(
      sorted(six.iteritems(new_secrets_dict)))
  # Handles the case when the newly configured secrets could conflict with
  # existing secrets.
  ArgSecretsDict.ValidateSecrets(new_secrets_dict)

  new_secrets_dict_by_type = _SplitSecretsDict(new_secrets_dict)
  needs_update['secret_environment_variables'] = old_secrets_dict_by_type[
      'secret_environment_variables'] != new_secrets_dict_by_type[
          'secret_environment_variables']
  needs_update['secret_volumes'] = old_secrets_dict_by_type[
      'secret_volumes'] != new_secrets_dict_by_type['secret_volumes']
  return new_secrets_dict_by_type, needs_update
