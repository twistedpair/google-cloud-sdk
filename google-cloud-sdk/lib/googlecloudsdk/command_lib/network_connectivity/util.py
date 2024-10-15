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
"""Utilities for `gcloud network-connectivity`."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import argparse

from googlecloudsdk.core import exceptions


# Constants
PROJECTS_RESOURCE_PATH = "projects/"
LOCATION_FILTER_FMT = "location:projects/{0}/locations/{1}"
ROUTE_TYPE_FILTER = "-type:DYNAMIC_ROUTE"


class NetworkConnectivityError(exceptions.Error):
  """Top-level exception for all Network Connectivity errors."""


class InvalidInputError(NetworkConnectivityError):
  """Exception for invalid input."""


# Table format for spokes list
LIST_FORMAT = """
    table(
      name.basename(),
      name.segment(3):label=LOCATION,
      hub.basename(),
      group.basename(),
      format(
        "{0}{1}{2}{3}",
        linkedVpnTunnels.yesno(yes="VPN tunnel", no=""),
        linkedInterconnectAttachments.yesno(yes="VLAN attachment", no=""),
        linkedRouterApplianceInstances.yesno(yes="Router appliance", no=""),
        linkedVpcNetwork.yesno(yes="VPC network", no="")
      ):label=TYPE,
      firstof(linkedVpnTunnels.uris, linkedInterconnectAttachments.uris, linkedRouterApplianceInstances.instances, linkedVpcNetwork).len():label="RESOURCE COUNT",
      format(
        "{0}{1}",
        linkedVpcNetwork.yesno(yes="N/A", no=""),
        firstof(linkedVpnTunnels.siteToSiteDataTransfer, linkedInterconnectAttachments.siteToSiteDataTransfer, linkedRouterApplianceInstances.siteToSiteDataTransfer).yesno(yes="On", no="")
      ).yesno(no="Off"):label="DATA TRANSFER",
      description
    )
"""

LIST_SPOKES_FORMAT = """
    table(
      name.basename(),
      group.basename(),
      name.segment(1):label=PROJECT,
      name.segment(3):label=LOCATION,
      spokeType:label=TYPE,
      state,
      reasons.code.list():label="STATE REASON",
      format(
        "{0}{1}",
        linkedVpcNetwork.yesno(yes="N/A", no=""),
        firstof(linkedVpnTunnels.siteToSiteDataTransfer, linkedInterconnectAttachments.siteToSiteDataTransfer, linkedRouterApplianceInstances.siteToSiteDataTransfer).yesno(yes="On", no="")
      ).yesno(no="Off").if(view=detailed):label="DATA TRANSFER",
      description.if(view=detailed)
    )
"""


def AppendLocationsGlobalToParent(unused_ref, unused_args, request):
  """Add locations/global to parent path."""

  request.parent += "/locations/global"
  return request


def DeriveProjectFromResource(resource):
  """Returns the project from a resource string."""
  if PROJECTS_RESOURCE_PATH not in resource:
    raise InvalidInputError(
        "Resource must contain a project path, but received: {0}".format(
            resource
        )
    )
  project = resource[
      resource.index(PROJECTS_RESOURCE_PATH) + len(PROJECTS_RESOURCE_PATH) :
  ]
  project = project.split("/")[0]
  return project


def AppendEffectiveLocationFilter(unused_ref, args, request):
  """Append filter to limit listing dynamic routes at an effective location."""

  if args.IsSpecified("effective_location"):
    location = args.effective_location
    project = DeriveProjectFromResource(request.parent)
    location_filter = LOCATION_FILTER_FMT.format(project, location)
    request.filter = "{0} OR {1}".format(location_filter, ROUTE_TYPE_FILTER)
  return request


def SetGlobalLocation():
  """Set default location to global."""
  return "global"


def ClearOverlaps(unused_ref, args, patch_request):
  """Handles clear_overlaps flag."""

  if args.IsSpecified("clear_overlaps"):
    if patch_request.updateMask:
      patch_request.updateMask += ",overlaps"
    else:
      patch_request.updateMask = "overlaps"
  return patch_request


def ClearLabels(unused_ref, args, patch_request):
  """Handles clear_labels flag."""

  if args.IsSpecified("clear_labels"):
    if patch_request.updateMask:
      patch_request.updateMask += ",labels"
    else:
      patch_request.updateMask = "labels"
  return patch_request


def ValidateMigration(unused_ref, args, request):
  """Validates migration parameters."""
  if not args.IsSpecified("usage") or args.usage != "for-migration":
    if args.IsSpecified("migration_source") or args.IsSpecified(
        "migration_target"
    ):
      raise InvalidInputError(
          "migration_source and migration_target can only be specified when"
          " usage is set to for-migration."
      )
    else:
      return request
  # We are now in the for-migration usage case.
  if not args.IsSpecified("migration_source") or not args.IsSpecified(
      "migration_target"
  ):
    raise InvalidInputError(
        "Both migration_source and migration_target must be specified."
    )
  if args.IsSpecified("peering") and args.peering != "for-self":
    raise InvalidInputError(
        "Peering must be set to for-self when usage is set to for-migration."
    )
  if not args.migration_source:
    raise InvalidInputError("migration_source cannot be empty.")
  if not args.migration_target:
    raise InvalidInputError("migration_target cannot be empty.")
  if args.migration_source == args.migration_target:
    raise InvalidInputError(
        "migration_source and migration_target cannot be the same."
    )
  return request


class StoreGlobalAction(argparse._StoreConstAction):
  # pylint: disable=protected-access
  # pylint: disable=redefined-builtin
  """Return "global" if the --global argument is used."""

  def __init__(self,
               option_strings,
               dest,
               default="",
               required=False,
               help=None):
    super(StoreGlobalAction, self).__init__(
        option_strings=option_strings,
        dest=dest,
        const="global",
        default=default,
        required=required,
        help=help)
