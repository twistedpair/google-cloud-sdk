# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Utility functions for Cloud KMS integration with GCE.

Collection of methods to handle Cloud KMS (Key Management Service) resources
with Google Compute Engine (GCE).
"""

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope import parser_errors
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

KMS_HELP_URL = ('https://cloud.google.com/compute/docs/disks/'
                'customer-managed-encryption')
_KMS_ARGS = ['kms-key', 'kms-keyring', 'kms-location', 'kms-project',
             'boot-disk-kms-key', 'boot-disk-kms-keyring',
             'boot-disk-kms-location', 'boot-disk-kms-project']


def AddKmsKeyArgs(parser, resource_type='resource'):
  """Adds arguments related to Cloud KMS keys."""
  parser.add_argument(
      '--kms-key',
      help="""\
      The Cloud KMS (Key Management Service) cryptokey that will be used to
      protect the {resource}.

      This can either be the fully qualified path or the name.

      The fully qualified Cloud KMS cryptokey has the format:
      ``projects/<project-id>/locations/<location>/keyRings/<ring-name>/
      cryptoKeys/<key-name>''

      If the value is not fully qualified then --kms-location and --kms-keyring
      are required. For keys in a different project use --kms-project.

      See {kms_help} for more details.
      """.format(resource=resource_type, kms_help=KMS_HELP_URL))

  parser.add_argument(
      '--kms-project',
      help="""\
      Project that contains the Cloud KMS cryptokey that will protect the
      {resource}.

      If the project is not specified then the project where the {resource} is
      being created will be used.

      If this flag is set then --key-location, --kms-keyring, and --kms-key
      are required.

      See {kms_help} for more details.
      """.format(resource=resource_type, kms_help=KMS_HELP_URL))

  parser.add_argument(
      '--kms-location',
      help="""\
      Location of the Cloud KMS cryptokey to be used for protecting the
      {resource}.

      All Cloud KMS cryptokeys reside in a 'location'.
      To get a list of possible locations run 'gcloud kms locations list'.

      If this flag is set then --kms-keyring and --kms-key are required.

      See {kms_help} for more details.
      """.format(resource=resource_type, kms_help=KMS_HELP_URL))

  parser.add_argument(
      '--kms-keyring',
      help="""\
      The name of the keyring which contains the Cloud KMS cryptokey that will
      protect the {resource}.

      If this flag is set then --kms-location and --kms-key are required.

      See {kms_help} for more details.
      """.format(resource=resource_type, kms_help=KMS_HELP_URL))


def _GetSpecifiedKmsArgs(args):
  """Returns the first KMS related argument as a string."""
  if not args:
    return None
  specified = set()
  for keyword in _KMS_ARGS:
    if getattr(args, keyword.replace('-', '_'), None):
      specified.add('--' + keyword)
  return specified


def _GetSpecifiedKmsDict(args):
  """Returns the first KMS related argument as a string."""
  if not args:
    return None
  specified = set()
  for keyword in _KMS_ARGS:
    if keyword in args:
      specified.add(keyword)
  return specified


def _DictToKmsKey(args, resource_project):
  """Returns the Cloud KMS crypto key name based on the KMS args."""
  if not args:
    return None

  if 'kms-project' not in args:
    args['kms-project'] = resource_project

  def GetValue(args, key):
    def GetValueFunc():
      val = args[key] if key in args else None
      if val:
        return val
      raise parser_errors.RequiredError(argument=key)
    return GetValueFunc

  return resources.REGISTRY.Parse(
      GetValue(args, 'kms-key')(),
      params={
          'projectsId': args['kms-project'] if 'kms-project' in args else
                        properties.VALUES.core.project.GetOrFail,
          'locationsId': GetValue(args, 'kms-location'),
          'keyRingsId': GetValue(args, 'kms-keyring'),
          'cryptoKeysId': GetValue(args, 'kms-key'),
      },
      collection='cloudkms.projects.locations.keyRings.cryptoKeys')


def _ArgsToKmsKey(args, resource_project):
  """Returns the Cloud KMS crypto key name based on the KMS args."""
  if not args:
    return None

  if hasattr(args, 'boot_disk_kms_key'):
    if args.boot_disk_kms_project:
      resource_project = args.boot_disk_kms_project
    return resources.REGISTRY.Parse(
        args.boot_disk_kms_key,
        params={
            'projectsId': resource_project or
                          properties.VALUES.core.project.GetOrFail,
            'locationsId': args.MakeGetOrRaise('--boot_disk_kms_location'),
            'keyRingsId': args.MakeGetOrRaise('--boot_disk_kms_keyring'),
            'cryptoKeysId': args.MakeGetOrRaise('--boot_disk_kms_key'),
        },
        collection='cloudkms.projects.locations.keyRings.cryptoKeys')
  elif hasattr(args, 'kms_key'):
    if args.kms_project:
      resource_project = args.kms_project
    return resources.REGISTRY.Parse(
        args.kms_key,
        params={
            'projectsId': resource_project or
                          properties.VALUES.core.project.GetOrFail,
            'locationsId': args.MakeGetOrRaise('--kms_location'),
            'keyRingsId': args.MakeGetOrRaise('--kms_keyring'),
            'cryptoKeysId': args.MakeGetOrRaise('--kms_key'),
        },
        collection='cloudkms.projects.locations.keyRings.cryptoKeys')
  else:
    return None


def _DictToMessage(args, compute_client, resource_project):
  """Returns the Cloud KMS crypto key name based on the values in the dict."""
  key = _DictToKmsKey(args, resource_project)
  if not key:
    return None
  return compute_client.MESSAGES_MODULE.CustomerEncryptionKey(
      kmsKeyName=str(key.RelativeName()))


def _ArgsToMessage(args, compute_client, resource_project):
  key = _ArgsToKmsKey(args, resource_project)
  if not key:
    return None
  return compute_client.MESSAGES_MODULE.CustomerEncryptionKey(
      kmsKeyName=str(key.RelativeName()))


def MaybeGetKmsKey(args, project, apitools_client, current_value):
  """Gets the Cloud KMS CryptoKey reference from command arguments.

  Args:
    args: Namespaced command line arguments.
    project: Default project for the Cloud KMS encryption key.
    apitools_client: Compute API HTTP client.
    current_value: Current CustomerEncryptionKey value.

  Returns:
    CustomerEncryptionKey message with the KMS key populated if args has a key.
  Raises:
    ConflictingArgumentsException if an encryption key is already populated.
  """
  if bool(_GetSpecifiedKmsArgs(args)):
    if current_value:
      raise exceptions.ConflictingArgumentsException(
          '--csek-key-file', *_GetSpecifiedKmsArgs(args))
    return _ArgsToMessage(args, apitools_client, project)
  return current_value


def MaybeGetKmsKeyFromDict(args, project, apitools_client, current_value):
  """Gets the Cloud KMS CryptoKey reference for a boot disk's initialize params.

  Args:
    args: A dictionary of a boot disk's initialize params.
    project: Default project for the Cloud KMS encryption key.
    apitools_client: Compute API HTTP client.
    current_value: Current CustomerEncryptionKey value.

  Returns:
    CustomerEncryptionKey message with the KMS key populated if args has a key.
  Raises:
    ConflictingArgumentsException if an encryption key is already populated.
  """
  if bool(_GetSpecifiedKmsDict(args)):
    if current_value:
      raise exceptions.ConflictingArgumentsException(
          '--csek-key-file', *_GetSpecifiedKmsArgs(args))
    return _DictToMessage(args, apitools_client, project)
  return current_value
