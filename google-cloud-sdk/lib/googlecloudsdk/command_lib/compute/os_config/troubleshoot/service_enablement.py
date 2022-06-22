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
"""Utility function for the OS Config Troubleshooter to check service enablement."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import traceback
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.services import enable_api
from googlecloudsdk.api_lib.services import exceptions
from googlecloudsdk.command_lib.compute.os_config.troubleshoot import utils


def Check(instance_ref, release_track):
  """Checks if the OS Config API is enabled for the specified instance."""
  continue_flag = False
  response_message = '> Is OS Config Service enabled? '

  try:
    service_enabled = enable_api.IsServiceEnabled(instance_ref.project,
                                                  'osconfig.googleapis.com')
    if service_enabled:
      response_message += 'Yes\n'
      continue_flag = True
    else:
      # Format the release_track.
      release_track_str = '' if release_track is None else release_track + ' '
      response_message += (
          'No\n'
          'OS Config is not enabled for this instance. To enable, run\n\n'
          '$ gcloud ' + release_track_str + 'services enable '
          'osconfig.googleapis.com'
          )
  except (exceptions.GetServicePermissionDeniedException,
          apitools_exceptions.HttpError) as err:
    response_message += (
        'Unknown\n'
        'The troubleshooter encountered ' + type(err).__name__ + ' while'
        ' checking your instance.\n\n' + traceback.format_exc()
        )
  return utils.Response(continue_flag, response_message)
