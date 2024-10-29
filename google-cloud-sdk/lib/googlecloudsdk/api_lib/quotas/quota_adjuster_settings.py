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
"""Utilities for Cloud Quotas API QuotaAdjusterSettings."""

from googlecloudsdk.api_lib.quotas import message_util
from googlecloudsdk.api_lib.util import apis


_CONSUMER_LOCATION_RESOURCE = '%s/locations/global'


def _GetClientInstance(no_http=False):
  return apis.GetClientInstance('cloudquotas', 'v1', no_http=no_http)


def GetQuotaAdjusterSettings(args):
  """Retrieve the QuotaAdjusterSettings for a project, folder or organization.

  Args:
    args: argparse.Namespace, The arguments that this command was invoked with.

  Returns:
    The requested QuotaAdjusterSettings.
  """
  consumer = message_util.CreateConsumer(
      args.project, args.folder, args.organization
  )
  client = _GetClientInstance()
  messages = client.MESSAGES_MODULE
  name = _CONSUMER_LOCATION_RESOURCE % (consumer) + '/quotaAdjusterSettings'

  if args.project:
    request = (
        messages.CloudquotasProjectsLocationsGetQuotaAdjusterSettingsRequest(
            name=name
        )
    )
    return client.projects_locations.GetQuotaAdjusterSettings(request)

  if args.folder:
    request = (
        messages.CloudquotasFoldersLocationsGetQuotaAdjusterSettingsRequest(
            name=name
        )
    )
    return client.folders_locations.GetQuotaAdjusterSettings(request)

  if args.organization:
    request = messages.CloudquotasOrganizationsLocationsGetQuotaAdjusterSettingsRequest(
        name=name
    )
    return client.organizations_locations.GetQuotaAdjusterSettings(request)


def UpdateQuotaAdjusterSettings(args):
  """Updates the parameters of the QuotaAdjusterSettings.

  Args:
    args: argparse.Namespace, The arguments that this command was invoked with.

  Returns:
    The updated QuotaAdjusterSettings.
  """
  consumer = message_util.CreateConsumer(
      args.project, args.folder, args.organization
  )
  client = _GetClientInstance()
  messages = client.MESSAGES_MODULE
  name = _CONSUMER_LOCATION_RESOURCE % (consumer) + '/quotaAdjusterSettings'

  quota_adjuster_settings = messages.QuotaAdjusterSettings(
      name=name,
      enablement=messages.QuotaAdjusterSettings.EnablementValueValuesEnum(
          args.enablement.upper()
      ),
  )

  if args.project:
    request = (
        messages.CloudquotasProjectsLocationsUpdateQuotaAdjusterSettingsRequest(
            name=name,
            quotaAdjusterSettings=quota_adjuster_settings,
            validateOnly=args.validate_only,
        )
    )
    return client.projects_locations.UpdateQuotaAdjusterSettings(request)

  if args.folder:
    request = (
        messages.CloudquotasFoldersLocationsUpdateQuotaAdjusterSettingsRequest(
            name=name,
            quotaAdjusterSettings=quota_adjuster_settings,
            validateOnly=args.validate_only,
        )
    )
    return client.folders_locations.UpdateQuotaAdjusterSettings(request)

  if args.organization:
    request = messages.CloudquotasOrganizationsLocationsUpdateQuotaAdjusterSettingsRequest(
        name=name,
        quotaAdjusterSettings=quota_adjuster_settings,
        validateOnly=args.validate_only,
    )
    return client.organizations_locations.UpdateQuotaAdjusterSettings(request)
