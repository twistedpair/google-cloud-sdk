# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Helpers for flags in commands working with Anthos Multi-Cloud on Attached."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers


def AddPlatformVersion(parser, required=True):
  parser.add_argument(
      '--platform-version',
      required=required,
      help='Platform version to use for the cluster.')


def GetPlatformVersion(args):
  return getattr(args, 'platform_version', None)


def AddIssuerUrl(parser, required=False):
  parser.add_argument(
      '--issuer-url',
      required=required,
      help=('Issuer url of the cluster to attach.'))


def GetIssuerUrl(args):
  return getattr(args, 'issuer_url', None)


def AddOidcJwks(parser):
  parser.add_argument(
      '--oidc-jwks',
      help=('OIDC JWKS of the cluster to attach.'))


def GetOidcJwks(args):
  return getattr(args, 'oidc_jwks', None)


def AddAuthority(parser):
  """Adds Authority flags.

  Args:
    parser: The argparse.parser to add the arguments to.
  """

  group = parser.add_group('Authority', required=True)
  AddIssuerUrl(group, required=True)
  AddOidcJwks(group)


def AddDistribution(parser, required=False):
  help_text = """
Set the base platform type of the cluster to attach.

Examples:

  $ {command} --distribution=aks
  $ {command} --distribution=eks
"""
  parser.add_argument(
      '--distribution',
      required=required,
      help=help_text)


def GetDistribution(args):
  return getattr(args, 'distribution', None)


def AddAdminUsers(parser):
  help_txt = """
Users that can perform operations as a cluster administrator.

There is no way to completely remove admin users after setting.
"""

  parser.add_argument(
      '--admin-users',
      type=arg_parsers.ArgList(),
      metavar='USER',
      required=False,
      help=help_txt)


def GetAdminUsers(args):
  if not hasattr(args, 'admin_users'):
    return None
  if args.admin_users:
    return args.admin_users
  return None
