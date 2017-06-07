# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Flags and helpers for the compute backend-buckets commands."""

from googlecloudsdk.command_lib.compute import flags as compute_flags
_GCS_BUCKET_DETAILED_HELP = """\
The name of the Google Cloud Storage bucket to serve from. The storage
        bucket must be owned by the project's owner."""

DEFAULT_LIST_FORMAT = """\
    table(
      name,
      bucketName:label=GCS_BUCKET_NAME,
      enableCdn
    )"""


def BackendBucketArgument(plural=False):
  return compute_flags.ResourceArgument(
      name='backend_bucket_name',
      resource_name='backend bucket',
      plural=plural,
      completion_resource_id='compute.backendBuckets',
      global_collection='compute.backendBuckets')

GCS_BUCKET_ARG = compute_flags.ResourceArgument(
    resource_name='backend bucket',
    completion_resource_id='compute.backendBuckets',
    name='--gcs-bucket-name',
    plural=False,
    required=False,
    global_collection='compute.backendBuckets',
    detailed_help=_GCS_BUCKET_DETAILED_HELP)

REQUIRED_GCS_BUCKET_ARG = compute_flags.ResourceArgument(
    resource_name='backend bucket',
    completion_resource_id='compute.backendBuckets',
    name='--gcs-bucket-name',
    plural=False,
    global_collection='compute.backendBuckets',
    detailed_help=_GCS_BUCKET_DETAILED_HELP)


def BackendBucketArgumentForUrlMap(required=True):
  return compute_flags.ResourceArgument(
      resource_name='backend bucket',
      name='--default-backend-bucket',
      required=required,
      completion_resource_id='compute.backendBuckets',
      global_collection='compute.backendBuckets')
