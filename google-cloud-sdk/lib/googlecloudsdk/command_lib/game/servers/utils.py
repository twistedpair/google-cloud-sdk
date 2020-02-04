# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Utility functions for Cloud Game Servers update commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources

GAME_SERVICES_API = 'gameservices'
OPERATIONS_COLLECTION = 'gameservices.projects.locations.operations'


def AddFieldToUpdateMask(field, patch_request):
  update_mask = patch_request.updateMask
  if update_mask:
    if update_mask.count(field) == 0:
      patch_request.updateMask = update_mask + ',' + field
  else:
    patch_request.updateMask = field
  return patch_request


def GetApiMessage(api_version):
  return apis.GetMessagesModule(GAME_SERVICES_API, api_version)


def GetClient(api_version):
  return apis.GetClientInstance(GAME_SERVICES_API, api_version)


def GetApiVersionFromArgs(args):
  """Return API version based on args.

  Args:
    args: The argparse namespace.

  Returns:
    API version (e.g. v1alpha or v1beta).

  Raises:
    UnsupportedReleaseTrackError: If invalid release track from args
  """

  release_track = args.calliope_command.ReleaseTrack()
  if release_track == base.ReleaseTrack.ALPHA:
    return 'v1alpha'
  if release_track == base.ReleaseTrack.BETA:
    return 'v1beta'
  raise UnsupportedReleaseTrackError(release_track)


class UnsupportedReleaseTrackError(Exception):
  """Raised when requesting an api for an unsupported release track."""


def ParseClusters(api_version, key, val, messages=None):
  messages = messages or GetApiMessage(api_version)

  return messages.LabelSelector.LabelsValue.AdditionalProperty(
      key=key, value=val)


def ParseLabels(api_version, cluster_labels, messages=None):
  messages = messages or GetApiMessage(api_version)

  selectors = messages.LabelSelector.LabelsValue()
  selectors.additionalProperties = cluster_labels

  label_selector = messages.LabelSelector()
  label_selector.labels = selectors

  return label_selector


def _GetDefaultVersion():
  return apis.ResolveVersion(GAME_SERVICES_API)


def GetMessages(api_version=None):
  api_version = api_version or _GetDefaultVersion()
  return apis.GetMessagesModule(GAME_SERVICES_API, api_version)


def WaitForOperation(response, api_version):
  operation_ref = resources.REGISTRY.ParseRelativeName(
      response.name, collection=OPERATIONS_COLLECTION)
  return waiter.WaitFor(
      waiter.CloudOperationPollerNoResources(
          GetClient(api_version).projects_locations_operations), operation_ref,
      'Waiting for [{0}] to finish'.format(operation_ref.Name()))
