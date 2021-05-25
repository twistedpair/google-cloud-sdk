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
"""Calls cloud run service of a Google Cloud Function."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.functions.v2 import util as v2_api_util
from googlecloudsdk.core import requests as core_requests


def Run(args, release_track):
  """Call a v2 Google Cloud Function."""
  v2_client = v2_api_util.GetClientInstance(release_track=release_track)
  v2_messages = v2_client.MESSAGES_MODULE

  function_ref = args.CONCEPTS.name.Parse()

  # cloudfunctions_v2alpha_messages.Function
  function = v2_client.projects_locations_functions.Get(
      v2_messages.CloudfunctionsProjectsLocationsFunctionsGetRequest(
          name=function_ref.RelativeName()))

  cloud_run_uri = function.serviceConfig.uri

  requests_session = core_requests.GetSession()

  # TODO(b/186873100) Convert to using CloudEvents format.
  response = requests_session.post(
      cloud_run_uri, args.data, headers={'Content-Type': 'application/json'})

  response.raise_for_status()

  return response.content
