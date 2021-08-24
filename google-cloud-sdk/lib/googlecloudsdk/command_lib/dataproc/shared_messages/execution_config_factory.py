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

"""Factory for ExecutionConfig message."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


class ExecutionConfigFactory(object):
  """Factory for ExecutionConfig message.

  Add ExecutionConfig related arguments to argument parser and create
  ExecutionConfig message from parsed arguments.
  """

  def __init__(self, dataproc):
    """Factory class for ExecutionConfig message.

    Args:
      dataproc: A api_lib.dataproc.Dataproc instance.
    """
    self.dataproc = dataproc

  def GetMessage(self, args):
    """Builds an ExecutionConfig instance.

    Build a ExecutionConfig instance according to user settings.
    Returns None if all fileds are None.

    Args:
      args: Parsed arguments.

    Returns:
      ExecutionConfig: A ExecutionConfig instance. None if all fields are
      None.
    """
    kwargs = {}

    if args.network_tags:
      # Repeated string field.
      # args.networkTags should be parsed as a list of string.
      kwargs['networkTags'] = args.network_tags

    if args.tags:
      kwargs['networkTags'] = args.tags

    if args.network_uri:
      kwargs['networkUri'] = args.network_uri

    if args.network:
      kwargs['networkUri'] = args.network

    if args.subnetwork_uri:
      kwargs['subnetworkUri'] = args.subnetwork_uri

    if args.subnet:
      kwargs['subnetworkUri'] = args.subnet

    if args.performance_tier:
      kwargs['performanceTier'] = (
          self.dataproc.messages.ExecutionConfig.PerformanceTierValueValuesEnum(
              args.performance_tier.upper()))

    if args.service_account:
      kwargs['serviceAccount'] = args.service_account

    if args.scopes:
      # Repeated string field.
      # args.scopes should be parsed as a list of string.
      kwargs['serviceAccountScopes'] = args.scopes

    if not kwargs:
      return None

    return self.dataproc.messages.ExecutionConfig(**kwargs)


# Supported performance tier choices.
_PERFORMANCE_TIER = ['economy', 'standard', 'high']


def AddArguments(parser):
  """Adds ExecutionConfig related arguments to parser."""
  base.ChoiceArgument(
      '--performance-tier',
      hidden=True,  # Not supported yet.
      choices=_PERFORMANCE_TIER,
      help_str=('Performance tier for a batch job performance. '
                'The default performance level is STANDARD.')
      ).AddToParser(parser)

  parser.add_argument(
      '--service-account',
      help='The IAM service account to be used for a batch job.')

  parser.add_argument(
      '--scopes',
      type=arg_parsers.ArgList(),
      metavar='SCOPES',
      default=[],
      help='IAM service account scope.')

  network_group = parser.add_mutually_exclusive_group()
  network_group.add_argument(
      '--network-uri',
      hidden=True,
      action=actions.DeprecationAction(
          '--network_uri',
          warn=('The `--network_uri` flag is deprecated. '
                'Use the `--network` flag instead.')),
      help='Network URI to connect network to.')
  network_group.add_argument(
      '--subnetwork-uri',
      hidden=True,
      action=actions.DeprecationAction(
          '--subnetwork_uri',
          warn=('The `--subnetwork_uri` flag is deprecated. '
                'Use the `--subnet` flag instead.')),
      help='Subnetwork URI to connect network to.')
  network_group.add_argument(
      '--network', help='Network URI to connect network to.')
  network_group.add_argument(
      '--subnet', help='Subnetwork URI to connect network to.')

  network_tags = parser.add_mutually_exclusive_group()
  network_tags.add_argument(
      '--network-tags',
      type=arg_parsers.ArgList(),
      metavar='TAGS',
      hidden=True,
      action=actions.DeprecationAction(
          '--network_tags',
          warn=('The `--network_tags` flag is deprecated. '
                'Use the `--tags` flag instead.')),
      default=[],
      help='Network tags for traffic control.')
  network_tags.add_argument(
      '--tags',
      type=arg_parsers.ArgList(),
      metavar='TAGS',
      default=[],
      help='Network tags for traffic control.')
