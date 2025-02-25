# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the compute interconnects cross site networks commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags


@base.UniverseCompatible
@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class CrossSiteNetworksCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(CrossSiteNetworksCompleter, self).__init__(
        collection='compute.crossSiteNetworks',
        list_command='compute interconnects cross-site-networks list --uri',
        **kwargs
    )


def CrossSiteNetworkArgument(required=True, plural=False):
  return compute_flags.ResourceArgument(
      resource_name='crossSiteNetwork',
      completer=CrossSiteNetworksCompleter,
      plural=plural,
      required=required,
      global_collection='compute.crossSiteNetworks',
  )


def CrossSiteNetworkArgumentForOtherResource(required=True):
  return compute_flags.ResourceArgument(
      name='--cross-site-network',
      resource_name='crossSiteNetwork',
      completer=CrossSiteNetworksCompleter,
      plural=False,
      required=required,
      global_collection='compute.crossSiteNetworks',
  )


def AddDescription(parser):
  """Adds description flag to the argparse.ArgumentParser."""
  parser.add_argument(
      '--description',
      help='An optional, textual description for the cross site network.',
  )
