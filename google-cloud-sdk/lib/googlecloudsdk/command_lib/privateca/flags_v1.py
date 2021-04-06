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

from googlecloudsdk.api_lib.privateca import base as privateca_base
from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.privateca import text_utils

import six

# Flag definitions

_VALID_KEY_USAGES = [
    'digital_signature', 'content_commitment', 'key_encipherment',
    'data_encipherment', 'key_agreement', 'cert_sign', 'crl_sign',
    'encipher_only', 'decipher_only'
]
_VALID_EXTENDED_KEY_USAGES = [
    'server_auth', 'client_auth', 'code_signing', 'email_protection',
    'time_stamping', 'ocsp_signing'
]


def _StripVal(val):
  return six.text_type(val).strip()


def AddInlineX509ParametersFlags(parser, is_ca):
  """Adds flags for providing inline x509 parameters.

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
          metavar='KEY_USAGES',
          help='The list of key usages for this {}. This can only be provided if `--use-preset-profile` is not provided.'
          .format(resource_name),
          type=arg_parsers.ArgList(
              element_type=_StripVal, choices=_VALID_KEY_USAGES)))
  group.AddArgument(
      base.Argument(
          '--extended-key-usages',
          metavar='EXTENDED_KEY_USAGES',
          help='The list of extended key usages for this {}. This can only be provided if `--use-preset-profile` is not provided.'
          .format(resource_name),
          type=arg_parsers.ArgList(
              element_type=_StripVal, choices=_VALID_EXTENDED_KEY_USAGES)))
  group.AddArgument(
      base.Argument(
          '--max-chain-length',
          help='Maximum depth of subordinate CAs allowed under this CA for a CA certificate. This can only be provided if `--use-preset-profile` is not provided.',
          default=0))
  if not is_ca:
    group.AddArgument(
        base.Argument(
            '--is-ca-cert',
            help='Whether this certificate is for a CertificateAuthority or not. Indicates the Certificate Authority field in the x509 basic constraints extension.',
            required=False,
            default=False,
            action='store_true'))
  group.AddToParser(parser)


# Flag parsing


def ParseX509Parameters(args, is_ca):
  """Parses the X509 parameters flags into an API X509Parameters.

  Args:
    args: The parsed argument values.
    is_ca: Whether the current operation is on a CA. If so, certSign and crlSign
      key usages are added.

  Returns:
    An X509Parameters object.
  """
  # TODO(b/183243757): Check if a preset profile was used instead of
  # inline values.
  base_key_usages = args.key_usages or []
  if is_ca:
    # A CA should have these KeyUsages to be RFC 5280 compliant.
    base_key_usages.extend(['cert_sign', 'crl_sign'])
  key_usage_dict = {}
  for key_usage in base_key_usages:
    key_usage = text_utils.SnakeCaseToCamelCase(key_usage)
    key_usage_dict[key_usage] = True
  extended_key_usage_dict = {}
  for extended_key_usage in args.extended_key_usages or []:
    extended_key_usage = text_utils.SnakeCaseToCamelCase(extended_key_usage)
    extended_key_usage_dict[extended_key_usage] = True

  messages = privateca_base.GetMessagesModule('v1')
  return messages.X509Parameters(
      keyUsage=messages.KeyUsage(
          baseKeyUsage=messages_util.DictToMessageWithErrorCheck(
              key_usage_dict, messages.KeyUsageOptions),
          extendedKeyUsage=messages_util.DictToMessageWithErrorCheck(
              extended_key_usage_dict, messages.ExtendedKeyUsageOptions)),
      caOptions=messages.CaOptions(
          isCa=is_ca,
          maxIssuerPathLength=int(args.max_chain_length) if is_ca else None))
