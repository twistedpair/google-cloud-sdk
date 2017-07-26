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
"""Shared flags for Cloud IoT commands."""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


def GetIdFlag(noun, action, metavar=None):
  return base.Argument(
      'id',
      metavar=metavar or '{}_ID'.format(noun.replace(' ', '_').upper()),
      help='ID of the {} {}.\n\n'.format(noun, action))


def _GetFlag(flag, noun=None, required=True, description=''):
  if description:
    description = ' ' + description
  return base.Argument(
      '--' + flag,
      required=required,
      help='The {}{}.'.format(noun or flag, description))


def GetRegionFlag(description='', required=True):
  return _GetFlag('region', noun='Cloud region', description=description,
                  required=required)


def _GetRegistryFlag(description='', required=True):
  return _GetFlag('registry', noun='device registry', description=description,
                  required=required)


def _GetDeviceFlag(description='', required=True):
  return _GetFlag('device', description=description, required=required)


def AddRegistryResourceFlags(parser, verb, positional=True):
  noun = 'device registry'
  if positional:
    GetIdFlag(noun, verb, 'REGISTRY_ID').AddToParser(parser)
  else:
    _GetRegistryFlag(verb).AddToParser(parser)
  GetRegionFlag('for the ' + noun, required=False).AddToParser(parser)


def AddDeviceResourceFlags(parser, verb, positional=True):
  noun = 'device'
  if positional:
    GetIdFlag(noun, verb).AddToParser(parser)
  else:
    _GetDeviceFlag(verb).AddToParser(parser)
  GetRegionFlag('for the ' + noun, required=False).AddToParser(parser)
  _GetRegistryFlag('for the ' + noun, required=False).AddToParser(parser)


def GetIndexFlag(noun, action):
  return base.Argument(
      'index',
      type=int,
      help='The index (zero-based) of the {} {}.'.format(noun, action))


def GetDeviceRegistrySettingsFlags(defaults=True):
  """Get flags for device registry commands.

  Args:
    defaults: bool, whether to populate default values (for instance, should be
        false for Patch commands).

  Returns:
    list of base.Argument, the flags common to and specific to device commands.
  """
  return [
      base.Argument(
          '--enable-mqtt-config',
          help='Whether to allow MQTT connections to this device registry.',
          default=True if defaults else None,
          action='store_true'),
      base.Argument(
          '--pubsub-topic',
          required=False,
          help=('The Google Cloud Pub/Sub topic on which to forward messages, '
                'such as telemetry events.')),
  ]


def GetIamPolicyFileFlag():
  return base.Argument(
      'policy_file',
      help='JSON or YAML file with the IAM policy')


def GetDeviceFlags(defaults=True):
  """Get flags for device commands.

  Args:
    defaults: bool, whether to populate default values (for instance, should be
        false for Patch commands).

  Returns:
    list of base.Argument, the flags common to and specific to device commands.
  """
  help_text = (
      'If disabled, connections from this device will fail.\n\n'
      'Can be used to temporarily prevent the device from '
      'connecting if, for example, the sensor is generating bad '
      'data and needs maintenance.\n\n')
  if not defaults:
    help_text += (
        '\n\n'
        'Use `--enable-device` to enable and `--no-enable-device` to disable.')
  return [
      base.Argument(
          '--enable-device',
          default=True if defaults else None,
          action='store_true',
          help=help_text)
  ]


_VALID_KEY_TYPES = {
    'rs256': ('An RSA public key wrapped in an X.509v3 certificate '
              '([RFC5280](https://www.ietf.org/rfc/rfc5280.txt)), '
              'base64-encoded, and wrapped by `-----BEGIN CERTIFICATE-----` '
              'and `-----END CERTIFICATE-----`.'),
    'es256': ('An ECDSA public key. The key must use P-256 and SHA-256, be '
              'base64-encoded, and wrapped by `-----BEGIN PUBLIC KEY-----` and '
              '`-----END PUBLIC KEY-----`.')
}


def _KeyTypeValidator(type_):
  if type_ not in _VALID_KEY_TYPES:
    raise arg_parsers.ArgumentTypeError(
        'Invalid key type [{}]. Must be one of [{}]'.format(
            type_, ', '.join(_VALID_KEY_TYPES)))
  return type_


def AddDeviceCredentialFlagsToParser(parser, combine_flags=True,
                                     only_modifiable=False):
  """Get credentials-related flags.

  Adds one of the following:

    * --public-key path=PATH,type=TYPE,expiration-time=EXPIRATION_TIME
    * --path=PATH --type=TYPE --expiration-time=EXPIRATION_TIME

  depending on the value of combine_flags.

  Args:
    parser: argparse parser to which to add these flags.
    combine_flags: bool, whether to combine these flags into one --public-key
      flag or to leave them separate.
    only_modifiable: bool, whether to include all flags or just those that can
      be modified after creation.
  """
  flags = []
  if not only_modifiable:
    flags.extend([
        base.Argument('--path', required=True, type=str,
                      help='The path on disk to the file containing the key.'),
        base.Argument('--type', required=True, type=_KeyTypeValidator,
                      choices=_VALID_KEY_TYPES,
                      help='The type of the key.')
    ])
  flags.append(
      base.Argument('--expiration-time', type=arg_parsers.Datetime.Parse,
                    help=('The expiration time for the key in ISO 8601 '
                          '(ex. `2017-01-01T00:00Z`) format.')))
  if combine_flags:
    sub_argument_help = []
    spec = {}
    for flag in flags:
      name = flag.name.lstrip('-')
      required = flag.kwargs.get('required')
      choices = flag.kwargs.get('choices')
      choices_str = ''
      if choices:
        choices_str = ', '.join(map('`{}`'.format, sorted(choices)))
        choices_str = ' One of [{}].'.format(choices_str)
      help_ = flag.kwargs['help']
      spec[name] = flag.kwargs['type']
      sub_argument_help.append(
          '* *{name}*: {required}.{choices} {help}'.format(
              name=name, required=('Required' if required else 'Optional'),
              choices=choices_str, help=help_))
    key_type_help = []
    for key_type, description in reversed(sorted(_VALID_KEY_TYPES.items())):
      key_type_help.append('* `{}`: {}'.format(key_type, description))
    base.Argument(
        '--public-key',
        dest='public_keys',
        metavar='path=PATH,type=TYPE,[expiration-time=EXPIRATION-TIME]',
        type=arg_parsers.ArgDict(spec=spec),
        action='append',
        help="""\
Specify a public key.

Supports two key types:

{key_type_help}

The key specification is given via the following sub-arguments:

{sub_argument_help}

For example:

    --public-key \\
        path=/path/to/id_rsa.pem,type=rs256,expiration-time=2017-01-01T00:00-05

This flag may be provide multiple times to provide multiple keys (maximum 3).
""".format(key_type_help='\n'.join(key_type_help),
           sub_argument_help='\n'.join(sub_argument_help))).AddToParser(parser)
  else:
    for flag in flags:
      flag.AddToParser(parser)


def AddDeviceConfigFlagsToParser(parser):
  """Add flags for the `configs update` command."""
  base.Argument(
      '--version-to-update',
      type=int,
      help="""\
          The version number to update. If this value is `0` or unspecified, it
          will not check the version number of the server and will always update
          the current version; otherwise, this update will fail if the version
          number provided does not match the latest version on the server. This
          is used to detect conflicts with simultaneous updates.
          """).AddToParser(parser)
  data_group = parser.add_mutually_exclusive_group(required=True)
  base.Argument(
      '--config-file',
      help='Path to a local file containing the data for this configuration.'
  ).AddToParser(data_group)
  base.Argument(
      '--config-data',
      help=('The data for this configuration, as a string. For any values '
            'that contain special characters (in the context of your shell), '
            'use the `--config-file` flag instead.')
  ).AddToParser(data_group)
