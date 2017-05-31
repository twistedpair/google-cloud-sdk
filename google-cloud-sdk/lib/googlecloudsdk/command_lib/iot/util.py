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
"""General utilties for Cloud IoT commands."""
from googlecloudsdk.api_lib.cloudiot import devices
from googlecloudsdk.api_lib.cloudiot import registries
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import times


LOCATIONS_COLLECTION = 'cloudiot.projects.locations'
REGISTRIES_COLLECTION = 'cloudiot.projects.locations.registries'
DEVICES_COLLECTION = 'cloudiot.projects.locations.registries.devices'
DEVICE_CONFIGS_COLLECTION = 'cloudiot.projects.locations.registries.devices.configVersions'
_PROJECT = lambda: properties.VALUES.core.project.Get(required=True)


# Maximum number of public key credentials for a device
MAX_PUBLIC_KEY_NUM = 3


class InvalidPublicKeySpecificationError(exceptions.Error):
  """Indicates an issue with supplied public key credential(s)."""


class InvalidKeyFileError(exceptions.Error):
  """Indicates that a provided key file is malformed."""


class BadCredentialIndexError(exceptions.Error):
  """Indicates that a user supplied a bad index into a device's credentials."""

  def __init__(self, device_id, credentials, index):
    super(BadCredentialIndexError, self).__init__(
        'Invalid credential index [{index}]; device [{device}] has '
        '{num_credentials} credentials. (Indexes are zero-based.))'.format(
            index=index, device=device_id, num_credentials=len(credentials)))


class BadDeviceError(exceptions.Error):
  """Indicates that a given device is malformed."""


def RegistriesUriFunc(resource):
  return ParseRegistry(resource.name).SelfLink()


def DevicesUriFunc(resource):
  return ParseDevice(resource.name).SelfLink()


def ParseEnableMqttConfig(enable_mqtt_config, client=None):
  if enable_mqtt_config is None:
    return None
  client = client or registries.RegistriesClient()
  mqtt_config_enum = client.mqtt_config_enum
  if enable_mqtt_config:
    return mqtt_config_enum.MQTT_ENABLED
  else:
    return mqtt_config_enum.MQTT_DISABLED


def ParseEnableDevice(enable_device, client=None):
  if enable_device is None:
    return None
  client = client or devices.DevicesClient()
  enabled_state_enum = client.enabled_state_enum
  if enable_device is True:
    return enabled_state_enum.DEVICE_ENABLED
  elif enable_device is False:
    return enabled_state_enum.DEVICE_DISABLED
  else:
    raise ValueError('Invalid value for [enable_device].')


_ALLOWED_KEYS = ['type', 'path', 'expiration-time']
_REQUIRED_KEYS = ['type', 'path']


def _ValidatePublicKeyDict(public_key):
  unrecognized_keys = (set(public_key.keys()) - set(_ALLOWED_KEYS))
  if unrecognized_keys:
    raise TypeError(
        'Unrecognized keys [{}] for public key specification.'.format(
            ', '.join(unrecognized_keys)))

  for key in _REQUIRED_KEYS:
    if key not in public_key:
      raise InvalidPublicKeySpecificationError(
          '--public-key argument missing value for `{}`.'.format(key))


def _ConvertStringToFormatEnum(type_, messages):
  if type_ == 'rs256':
    return messages.PublicKeyCredential.FormatValueValuesEnum.RSA_X509_PEM
  elif type_ == 'es256':
    return messages.PublicKeyCredential.FormatValueValuesEnum.ES256_PEM
  else:
    # Should have been caught by argument parsing
    raise ValueError('Invalid key type [{}]'.format(type_))


def _ReadKeyFileFromPath(path):
  if not path:
    raise ValueError('path is required')
  try:
    with open(path, 'r') as f:
      return f.read()
  except (IOError, OSError) as err:
    raise InvalidKeyFileError('Could not read key file [{}]:\n\n{}'.format(
        path, err))


def ParseCredential(path, type_str, expiration_time=None, messages=None):
  messages = messages or devices.GetMessagesModule()

  type_ = _ConvertStringToFormatEnum(type_str, messages)
  contents = _ReadKeyFileFromPath(path)
  if expiration_time:
    expiration_time = times.FormatDateTime(expiration_time)

  return messages.DeviceCredential(
      expirationTime=expiration_time,
      publicKey=messages.PublicKeyCredential(
          format=type_,
          key=contents
      )
  )


def ParseCredentials(public_keys, messages=None):
  """Parse a DeviceCredential from user-supplied arguments.

  Returns a list of DeviceCredential with the appropriate type, expiration time
  (if provided), and contents of the file for each public key.

  Args:
    public_keys: list of dict (maximum 3) representing public key credentials.
      The dict should have the following keys:
      - 'type': Required. The key type. One of [es256, rs256]
      - 'path': Required. Path to a valid key file on disk.
      - 'expiration-time': Optional. datetime, the expiration time for the
        credential.
    messages: module or None, the apitools messages module for Cloud IoT (uses a
      default module if not provided).

  Returns:
    List of DeviceCredential (possibly empty).

  Raises:
    TypeError: if an invalid public_key specification is given in public_keys
    ValueError: if an invalid public key type is given (that is, neither es256
      nor rs256)
    InvalidPublicKeySpecificationError: if a public_key specification is missing
      a required part, or too many public keys are provided.
    InvalidKeyFileError: if a valid combination of flags is given, but the
      specified key file is not valid or not readable.
  """
  messages = messages or devices.GetMessagesModule()

  if not public_keys:
    return []

  if len(public_keys) > MAX_PUBLIC_KEY_NUM:
    raise InvalidPublicKeySpecificationError(
        ('Too many public keys specified: '
         '[{}] given, but maximum [{}] allowed.').format(
             len(public_keys), MAX_PUBLIC_KEY_NUM))

  credentials = []
  for key in public_keys:
    _ValidatePublicKeyDict(key)
    credentials.append(
        ParseCredential(key.get('path'), key.get('type'),
                        key.get('expiration-time'), messages=messages))
  return credentials


def GetRegistry():
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName('cloudiot', 'v1beta1')
  return registry


def ParseLocation(region):
  return GetRegistry().Parse(
      region,
      params={'projectsId': _PROJECT}, collection=LOCATIONS_COLLECTION)


def ParseRegistry(registry, region=None):
  return GetRegistry().Parse(
      registry,
      params={'projectsId': _PROJECT, 'locationsId': region},
      collection=REGISTRIES_COLLECTION)


def ParseDevice(device, registry=None, region=None):
  return GetRegistry().Parse(
      device,
      params={
          'projectsId': _PROJECT,
          'locationsId': region,
          'registriesId': registry
      },
      collection=DEVICES_COLLECTION)


def GetDeviceConfigRef(device_ref):
  return GetRegistry().Parse(
      device_ref.devicesId,
      params={
          'projectsId': device_ref.projectsId,
          'locationsId': device_ref.locationsId,
          'registriesId': device_ref.registriesId
      },
      collection=DEVICE_CONFIGS_COLLECTION)


def ParsePubsubTopic(topic):
  if topic is None:
    return None
  return GetRegistry().Parse(
      topic,
      params={'projectsId': _PROJECT}, collection='pubsub.projects.topics')


def ReadConfigData(args):
  """Read configuration data from the parsed arguments.

  See command_lib.iot.flags for the flag definitions.

  Args:
    args: a parsed argparse Namespace object containing config_data and
      config_file.

  Returns:
    str, the binary configuration data

  Raises:
    ValueError: unless exactly one of --config-data, --config-file given
  """
  if args.IsSpecified('config_data') and args.IsSpecified('config_file'):
    raise ValueError('Both --config-data and --config-file given.')
  if args.IsSpecified('config_data'):
    return args.config_data
  elif args.IsSpecified('config_file'):
    # Note: use 'rb' for Windows
    with open(args.config_file, 'rb') as f:
      return f.read()
  else:
    raise ValueError('Neither --config-data nor --config-file given.')
