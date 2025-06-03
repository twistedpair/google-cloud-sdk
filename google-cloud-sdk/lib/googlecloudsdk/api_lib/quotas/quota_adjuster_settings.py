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
from googlecloudsdk.calliope import base


_CONSUMER_LOCATION_RESOURCE = '%s/locations/global'

VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v1alpha',
    base.ReleaseTrack.BETA: 'v1beta',
    base.ReleaseTrack.GA: 'v1',
}


def _GetClientInstance(release_track, no_http=False):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetClientInstance('cloudquotas', api_version, no_http=no_http)


def GetQuotaAdjusterSettings(args, release_track=base.ReleaseTrack.ALPHA):
  """Retrieve the QuotaAdjusterSettings for a project.

  Args:
    args: argparse.Namespace, The arguments that this command was invoked with.
    release_track: base.ReleaseTrack, The release track to use.

  Returns:
    The requested QuotaAdjusterSettings.
  """
  consumer = message_util.CreateProjectConsumer(args.project)
  client = _GetClientInstance(release_track)
  messages = client.MESSAGES_MODULE
  name = _CONSUMER_LOCATION_RESOURCE % (consumer) + '/quotaAdjusterSettings'

  if args.project:
    request = (
        messages.CloudquotasProjectsLocationsQuotaAdjusterSettingsGetQuotaAdjusterSettingsRequest(
            name=name
        )
    )
    return client.projects_locations_quotaAdjusterSettings.GetQuotaAdjusterSettings(
        request
    )


def UpdateQuotaAdjusterSettings(args, release_track=base.ReleaseTrack.ALPHA):
  """Updates the QuotaAdjusterSettings of a project.

  Args:
    args: argparse.Namespace, The arguments that this command was invoked with.
    release_track: base.ReleaseTrack, The release track to use.

  Returns:
    The updated QuotaAdjusterSettings.
  """
  consumer = message_util.CreateProjectConsumer(args.project)
  client = _GetClientInstance(release_track)
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
        messages.CloudquotasProjectsLocationsQuotaAdjusterSettingsUpdateQuotaAdjusterSettingsRequest(
            name=name,
            quotaAdjusterSettings=quota_adjuster_settings,
            validateOnly=args.validate_only,
        )
    )
    return client.projects_locations_quotaAdjusterSettings.UpdateQuotaAdjusterSettings(
        request
    )
