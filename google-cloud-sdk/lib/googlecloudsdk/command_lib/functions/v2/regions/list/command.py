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
"""List regions available to Google Cloud Functions."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager

from googlecloudsdk.api_lib.functions.v2 import util as api_util
from googlecloudsdk.core import properties


def Run(args, release_track):
  """Lists GCF v2 regions available with the given args.

  Args:
    args: an argparse namespace. All the arguments that were provided to this
      command invocation.
    release_track: base.ReleaseTrack, The release track (ga, beta, alpha)

  Returns:
    locations: List[cloudfunctions_v2alpha.Location], List of available GCF
      v2 regions
  """
  del args  # unused by list command
  client = api_util.GetClientInstance(release_track=release_track)

  return list_pager.YieldFromList(
      service=client.projects_locations,
      request=_BuildListRequest(release_track),
      field='locations',
      batch_size_attribute='pageSize')


def _BuildListRequest(release_track):
  """Builds list available regions reqeust.

  Args:
    release_track: base.ReleaseTrack, The release track (ga, beta, alpha)

  Returns:
    list_request: v2alpha.CloudfunctionsProjectsLocationsListRequest, The
      list regions request
  """
  messages = api_util.GetMessagesModule(release_track=release_track)
  project = properties.VALUES.core.project.GetOrFail()
  return messages.CloudfunctionsProjectsLocationsListRequest(
      name='projects/' + project)
