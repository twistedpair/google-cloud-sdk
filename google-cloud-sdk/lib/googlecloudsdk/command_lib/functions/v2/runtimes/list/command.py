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
"""List runtimes available to Google Cloud Functions."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.functions.v2 import client
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


def Run(args, release_track):
  """Lists GCF v2 runtimes available with the given args.

  Args:
    args: an argparse namespace. All the arguments that were provided to this
      command invocation.
    release_track: base.ReleaseTrack, The release track (ga, beta, alpha)

  Returns:
    List[cloudfunctions_v2alpha|beta.Runtime], List of available GCF
      v2 runtimes
  """
  del args
  if not properties.VALUES.functions.region.IsExplicitlySet():
    log.status.Print('Suggest using `--region us-west1`')
  region = properties.VALUES.functions.region.Get()

  gcf_client = client.FunctionsClient(release_track=release_track)

  # ListRuntimesResponse
  response = gcf_client.ListRuntimes(region)

  if response:
    return response.runtimes
  else:
    return []
