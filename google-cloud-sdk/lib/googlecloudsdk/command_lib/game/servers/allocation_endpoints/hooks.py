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
"""Command hooks for Cloud Game Servers Allocation Endpoints."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import properties


PARENT_TEMPLATE = 'projects/{}/locations/{}'


# TODO(b/202898722): There is an template issue with the API. This hook is a
# workaround
def AddDefaultLocationToAllocationEndpointRequest(ref, unused_arguments, req):
  """Python hook to set default global location in allocation endpoint requests."""
  del ref
  project = properties.VALUES.core.project.Get(required=True)
  # Use global for the location value
  location = 'global'
  req.parent = PARENT_TEMPLATE.format(project, location)
  return req


def SetEndpointUpdateServiceAccounts(ref, arguments, req):
  """Modify the update request to add, remove, or clear endpoint service accounts."""
  del ref

  service_accounts = req.allocationEndpoint.serviceAccounts
  if arguments.clear_service_accounts:
    service_accounts = []
  if arguments.IsSpecified('remove_service_accounts'):
    to_remove = set(arguments.remove_service_accounts or [])
    service_accounts = [acc for acc in service_accounts if acc not in to_remove]
  if arguments.IsSpecified('add_service_accounts'):
    service_accounts += arguments.add_service_accounts

  req.allocationEndpoint.serviceAccounts = service_accounts
  return req


def SetUpdateMask(ref, arguments, req):
  """Constructs updateMask for endpoint patch requests."""
  del ref

  service_accounts_mask = 'serviceAccounts'
  labels_mask = 'labels'
  update_mask = set()

  if (arguments.clear_service_accounts or
      arguments.IsSpecified('remove_service_accounts') or
      arguments.IsSpecified('add_service_accounts')):
    update_mask.add(service_accounts_mask)

  if arguments.clear_labels:
    update_mask.add(labels_mask)

  labels_update_mask_prefix = labels_mask + '.'
  if labels_mask not in update_mask:
    if arguments.update_labels:
      for key in arguments.update_labels:
        update_mask.add(labels_update_mask_prefix + key)
    if arguments.remove_labels:
      for key in arguments.remove_labels:
        update_mask.add(labels_update_mask_prefix + key)

  req.updateMask = ','.join(sorted(update_mask))
  return req
