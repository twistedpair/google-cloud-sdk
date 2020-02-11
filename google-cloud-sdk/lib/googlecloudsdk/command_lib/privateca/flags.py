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

Defaults to enabled.
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

Defaults to enabled.
"""

PUBLISH_CRL_CREATE_HELP = """
If this gets enabled, the following will happen:
1) If there is no existing GCS bucket for this CA, a new bucket will be created in the same project.
2) CRLs will be written to a known location within that bucket.
3) The CDP extension in all future issued certificates will point to the CRL URL in that bucket.

Note that the same GCS bucket may be used for the CA cert if --publish-ca-cert is set.

Defaults to enabled.
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

Defaults to enabled.
"""


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
      help='An email Subject Alternative Name').AddToParser(parser)
  base.Argument(
      '--ip-san', help='An IP Subject Alternative Name').AddToParser(parser)
  base.Argument(
      '--dns-san', help='A DNS Subject Alternative Name').AddToParser(parser)
  base.Argument(
      '--uri-san', help='A URI Subject Alternative Name').AddToParser(parser)


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


# Flag parsing


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
      'C': 'country',
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
