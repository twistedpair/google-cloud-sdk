# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Helpers for parsing flags and arguments."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.api_lib.privateca import base as privateca_base
from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.privateca import text_utils
from googlecloudsdk.command_lib.util.apis import arg_utils
import ipaddress
import six


_EMAIL_SAN_REGEX = re.compile('^[^@]+@[^@]+$')
# Any number of labels (any character that is not a dot) concatenated by dots
_DNS_SAN_REGEX = re.compile(r'^([^.]+\.)*[^.]+$')

# Resource Flag definitions

# Other Flag definitions

PUBLISH_CA_CERT_CREATE_HELP = """
If this is set, the following will happen:
1) A new GCS bucket will be created in the same project.
2) The CA certificate will be written to a known location within that bucket.
3) The AIA extension in all issued certificates will point to the CA cert URL in that bucket.

Note that the same GCS bucket may be used for the CRLs if --publish-crl is set.
"""

PUBLISH_CA_CERT_UPDATE_HELP = """
If this is set, the following will happen:
1) A new GCS bucket will be created in the same project.
2) The CA certificate will be written to a known location within that bucket.
3) The AIA extension in all issued certificates will point to the CA cert URL in that bucket.

If this gets disabled, the AIA extension will not be written to any future certificates issued
by this CA. However, an existing GCS bucket will not be deleted, and the CA certificate will not
be removed from that bucket.

Note that the same GCS bucket may be used for the CRLs if --publish-crl is set.
"""

PUBLISH_CRL_CREATE_HELP = """
If this gets enabled, the following will happen:
1) If there is no existing GCS bucket for this CA, a new bucket will be created in the same project.
2) CRLs will be written to a known location within that bucket.
3) The CDP extension in all future issued certificates will point to the CRL URL in that bucket.

Note that the same GCS bucket may be used for the CA cert if --publish-ca-cert is set.
"""

PUBLISH_CRL_UPDATE_HELP = """
If this gets enabled, the following will happen:
1) If there is no existing GCS bucket for this CA, a new bucket will be created in the same project.
2) CRLs will be written to a known location within that bucket.
3) The CDP extension in all future issued certificates will point to the CRL URL in that bucket.

If this gets disabled, the CDP extension will not be written to any future certificates issued
by this CA, and new CRLs will not be published to that bucket (which affects existing certs).
However, an existing GCS bucket will not be deleted, and any existing CRLs will not be removed
from that bucket.

Note that the same GCS bucket may be used for the CA cert if --publish-ca-cert is set.
"""

_VALID_KEY_USAGES = [
    'digital_signature', 'content_commitment', 'key_encipherment',
    'data_encipherment', 'key_agreement', 'cert_sign', 'crl_sign',
    'encipher_only', 'decipher_only'
]
_VALID_EXTENDED_KEY_USAGES = [
    'server_auth', 'client_auth', 'code_signing', 'email_protection',
    'time_stamping', 'ocsp_signing'
]


def AddPublishCrlFlag(parser, use_update_help_text=False):
  help_text = PUBLISH_CRL_UPDATE_HELP if use_update_help_text else PUBLISH_CRL_CREATE_HELP
  base.Argument(
      '--publish-crl',
      help=help_text,
      action='store_true',
      required=False,
      default=True).AddToParser(parser)


def AddPublishCaCertFlag(parser, use_update_help_text=False):
  help_text = PUBLISH_CA_CERT_UPDATE_HELP if use_update_help_text else PUBLISH_CA_CERT_CREATE_HELP
  base.Argument(
      '--publish-ca-cert',
      help=help_text,
      action='store_true',
      required=False,
      default=True).AddToParser(parser)


def AddSubjectAlternativeNameFlags(parser):
  """Adds the Subject Alternative Name (san) flags.

  This will add --ip-san, --email-san, --dns-san, and --uri-san to the parser.

  Args:
    parser: The parser to add the flags to.
  """
  base.Argument(
      '--email-san',
      help='One or more space-separated email Subject Alternative Names.',
      nargs='*').AddToParser(parser)
  base.Argument(
      '--ip-san',
      help='One or more space-separated IP Subject Alternative Names.',
      nargs='*').AddToParser(parser)
  base.Argument(
      '--dns-san',
      help='One or more space-separated DNS Subject Alternative Names.',
      nargs='*').AddToParser(parser)
  base.Argument(
      '--uri-san',
      help='One or more space-separated URI Subject Alternative Names.',
      nargs='*').AddToParser(parser)


def _StripVal(val):
  return six.text_type(val).strip()


def AddSubjectFlag(parser, required=False):
  base.Argument(
      '--subject',
      required=required,
      help='X.501 name of the certificate subject. Example:'
      '--subject \"C=US,ST=California,L=Mountain View,O=Google LLC,CN=google.com\"',
      type=arg_parsers.ArgDict(
          required_keys=['CN'], key_type=_StripVal,
          value_type=_StripVal)).AddToParser(parser)


def AddValidityFlag(parser,
                    resource_name,
                    default_value='P10Y',
                    default_value_text='10 years'):
  base.Argument(
      '--validity',
      help='The validity of this {}, as an ISO8601 duration. Defaults to {}.'
      .format(resource_name, default_value_text),
      default=default_value).AddToParser(parser)


def AddIssuancePolicyFlag(parser, resource_name):
  base.Argument(
      '--issuance-policy',
      help="A yaml file describing this {}'s issuance policy.".format(
          resource_name)).AddToParser(parser)


def AddInlineReusableConfigFlags(parser, is_ca):
  """Adds flags for providing inline reusable config values.

  Args:
    parser: The parser to add the flags to.
    is_ca: Whether the current operation is on a CA. This influences the help
           text, and whether the --max-chain-length flag is added.
  """
  resource_name = 'CA' if is_ca else 'certificate'
  group = base.ArgumentGroup()
  group.AddArgument(
      base.Argument(
          '--key-usages',
          help='The list of key usages for this {}.'.format(resource_name),
          type=arg_parsers.ArgList(
              element_type=_StripVal, choices=_VALID_KEY_USAGES)))
  group.AddArgument(
      base.Argument(
          '--extended-key-usages',
          help='The list of extended key usages for this {}'.format(
              resource_name),
          type=arg_parsers.ArgList(
              element_type=_StripVal, choices=_VALID_EXTENDED_KEY_USAGES)))
  if is_ca:
    group.AddArgument(base.Argument(
        '--max-chain-length',
        help='Maximum depth of subordinate CAs allowed under this CA.'))
  group.AddToParser(parser)

# Flag parsing


def ParseReusableConfig(args, required=False):
  """Parses the reusable config flags into an API ReusableConfigWrapper.

  Args:
    args: The parsed argument values.
    required: Whether a reusable config is required.

  Returns:
    A ReusableConfigWrapper object.
  """
  resource = args.CONCEPTS.reusable_config.Parse()
  has_inline = args.IsSpecified('key_usages') or args.IsSpecified(
      'extended_key_usages') or args.IsSpecified('max_chain_length')

  messages = privateca_base.GetMessagesModule()

  if resource and has_inline:
    raise exceptions.InvalidArgumentException(
        '--reusable-config',
        '--reusable-config may not be specified if one or more of '
        '--key-usages, --extended-key-usages or --max-chain-length are '
        'specified.')

  if resource:
    return messages.ReusableConfigWrapper(
        reusableConfig=resource.RelativeName())

  if not has_inline:
    if required:
      raise exceptions.InvalidArgumentException(
          '--reusable-config',
          'Either --reusable-config or one or more of --key-usages, '
          '--extended-key-usages and --max-chain-length must be specified.')
    return messages.ReusableConfigWrapper()

  key_usage_dict = {}
  for key_usage in args.key_usages or []:
    key_usage = text_utils.SnakeCaseToCamelCase(key_usage)
    key_usage_dict[key_usage] = True
  extended_key_usage_dict = {}
  for extended_key_usage in args.extended_key_usages or []:
    extended_key_usage = text_utils.SnakeCaseToCamelCase(extended_key_usage)
    extended_key_usage_dict[extended_key_usage] = True
  max_issuer_length = (int(args.max_chain_length)
                       if args.IsSpecified('max_chain_length') else None)

  return messages.ReusableConfigWrapper(
      reusableConfigValues=messages.ReusableConfigValues(
          keyUsage=messages.KeyUsage(
              baseKeyUsage=messages_util.DictToMessageWithErrorCheck(
                  key_usage_dict, messages.KeyUsageOptions),
              extendedKeyUsage=messages_util.DictToMessageWithErrorCheck(
                  extended_key_usage_dict, messages.ExtendedKeyUsageOptions)),
          caOptions=messages.CaOptions(
              maxIssuerPathLength=max_issuer_length)))


def ParseSubject(subject_args):
  """Parses a dictionary with subject attributes into a API Subject type and common name.

  Args:
    subject_args: A string->string dict with subject attributes and values.

  Returns:
    A tuple with (common_name, Subject) where common name is a string and
    Subject is the Subject type represented in the api.
  """
  common_name = subject_args['CN']
  remap_args = {
      'C': 'countryCode',
      'ST': 'province',
      'L': 'locality',
      'O': 'organization',
      'OU': 'organizationalUnit'
  }

  mapped_args = {}
  for key, val in subject_args.items():
    if key == 'CN':
      continue
    if key in remap_args:
      mapped_args[remap_args[key]] = val
    else:
      mapped_args[key] = val

  try:
    return common_name, messages_util.DictToMessageWithErrorCheck(
        mapped_args,
        privateca_base.GetMessagesModule().Subject)
  except messages_util.DecodeError:
    raise exceptions.InvalidArgumentException(
        '--subject', 'Unrecognized subject attribute.')

# Flag validation helpers


def ValidateEmailSanFlag(san):
  if not re.match(_EMAIL_SAN_REGEX, san):
    raise exceptions.InvalidArgumentException('--email-san',
                                              'Invalid email address.')


def ValidateDnsSanFlag(san):
  if not re.match(_DNS_SAN_REGEX, san):
    raise exceptions.InvalidArgumentException('--dns-san',
                                              'Invalid domain name value')


def ValidateIpSanFlag(san):
  try:
    ipaddress.ip_address(san)
  except ValueError:
    raise exceptions.InvalidArgumentException('--ip-san',
                                              'Invalid IP address value.')


def AddLocationFlag(parser, resource_name, flag_name='--location'):
  """Add location flag to parser.

  Args:
    parser: The argparse parser to add the flag to.
    resource_name: The name of resource that the location refers to e.g.
      'certificate authority'
    flag_name: The name of the flag.
  """
  base.Argument(
      flag_name,
      help='Location of the {}.'.format(resource_name)).AddToParser(parser)


_REVOCATION_MAPPING = {
    'REVOCATION_REASON_UNSPECIFIED': 'unspecified',
    'KEY_COMPROMISE': 'key-compromise',
    'CERTIFICATE_AUTHORITY_COMPROMISE': 'certificate-authority-compromise',
    'AFFILIATION_CHANGED': 'affiliation-changed',
    'SUPERSEDED': 'superseded',
    'CESSATION_OF_OPERATION': 'cessation-of-operation',
    'CERTIFICATE_HOLD': 'certificate-hold',
    'PRIVILEGE_WITHDRAWN': 'privilege-withdrawn',
    'ATTRIBUTE_AUTHORITY_COMPROMISE': 'attribute-authority-compromise'
}

_REVOCATION_REASON_MAPPER = arg_utils.ChoiceEnumMapper(
    arg_name='--reason',
    default='unspecified',
    help_str='Revocation reason to include in the CRL.',
    message_enum=privateca_base.GetMessagesModule().RevokeCertificateRequest
    .ReasonValueValuesEnum,
    custom_mappings=_REVOCATION_MAPPING)


def AddRevocationReasonFlag(parser):
  """Add a revocation reason enum flag to the parser.

  Args:
    parser: The argparse parser to add the flag to.
  """
  _REVOCATION_REASON_MAPPER.choice_arg.AddToParser(parser)


def ParseRevocationChoiceToEnum(choice):
  """Return the apitools revocation reason enum value from the string choice.

  Args:
    choice: The string value of the revocation reason.

  Returns:
    The revocation enum value for the choice text.
  """
  return _REVOCATION_REASON_MAPPER.GetEnumForChoice(choice)
