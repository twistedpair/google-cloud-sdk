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
"""List event types available to Google Cloud Functions v2."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.eventarc import types


# TODO(b/195970381): Temporarily added until `gcloud eventarc attributes types
# list` publicly adds GCS types.
_GCS_TYPES = [
    types.EventType(
        'google.cloud.storage.object.v1.finalized',
        'Sent when a new object (or a new generation of an existing object).',
        'bucket'),
    types.EventType(
        'google.cloud.storage.object.v1.archived',
        'Sent when a live version of an (object versioned) object is archived or deleted.',
        'bucket'),
    types.EventType(
        'google.cloud.storage.object.v1.deleted',
        'Sent when an object has been permanently deleted.',
        'bucket'),
    types.EventType('google.cloud.storage.object.v1.metadataUpdated',
                    'Sent when the metadata of an existing object changes.',
                    'bucket'),
]


def Run(args, release_track):
  """Lists GCF v2 available event_types.

  Args:
    args: an argparse namespace. All the arguments that were provided to this
      command invocation.
    release_track: base.ReleaseTrack, The release track (ga, beta, alpha)

  Returns:
    event_types: List[EventType], The list of supported event types.
  """
  del args
  del release_track

  return types.EVENT_TYPES + _GCS_TYPES
