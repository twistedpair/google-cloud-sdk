# -*- coding: utf-8 -*- #
# Copyright 2021 Google Inc. All Rights Reserved.
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
"""Client for interaction with Dataplex."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import resources
import six


def GetClientInstance():
  return apis.GetClientInstance('dataplex', 'v1')


def GetMessageModule():
  return apis.GetMessagesModule('dataplex', 'v1')


def WaitForOperation(operation, resource):
  """Waits for the given google.longrunning.Operation to complete."""
  operation_ref = resources.REGISTRY.Parse(
      operation.name, collection='dataplex.projects.locations.operations')
  poller = waiter.CloudOperationPoller(
      resource,
      GetClientInstance().projects_locations_operations)
  return waiter.WaitFor(
      poller, operation_ref,
      'Waiting for [{0}] to finish'.format(operation_ref.RelativeName()))


def CreateLabels(dataplex_resource, args):
  if getattr(args, 'labels', None):
    return dataplex_resource.LabelsValue(additionalProperties=[
        dataplex_resource.LabelsValue.AdditionalProperty(key=key, value=value)
        for key, value in sorted(six.iteritems(args.labels))
    ])
  return None
