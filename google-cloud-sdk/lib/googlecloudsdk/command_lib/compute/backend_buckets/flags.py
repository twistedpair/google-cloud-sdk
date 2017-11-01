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

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags


_GCS_BUCKET_DETAILED_HELP = """\
The name of the Google Cloud Storage bucket to serve from. The storage
        bucket must be in the same project."""

DEFAULT_LIST_FORMAT = """\
    table(
      name,
      bucketName:label=GCS_BUCKET_NAME,
      enableCdn
    )"""


class BackendBucketsCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(BackendBucketsCompleter, self).__init__(
        collection='compute.backendBuckets',
        list_command='compute backend-buckets list --uri',
        **kwargs)


def BackendBucketArgument(plural=False):
  return compute_flags.ResourceArgument(
      name='backend_bucket_name',
      resource_name='backend bucket',
      plural=plural,
      completer=BackendBucketsCompleter,
      global_collection='compute.backendBuckets')

GCS_BUCKET_ARG = compute_flags.ResourceArgument(
    resource_name='backend bucket',
    completer=BackendBucketsCompleter,
    name='--gcs-bucket-name',
    plural=False,
    required=False,
    global_collection='compute.backendBuckets',
    detailed_help=_GCS_BUCKET_DETAILED_HELP)

REQUIRED_GCS_BUCKET_ARG = compute_flags.ResourceArgument(
    resource_name='backend bucket',
    completer=BackendBucketsCompleter,
    name='--gcs-bucket-name',
    plural=False,
    global_collection='compute.backendBuckets',
    detailed_help=_GCS_BUCKET_DETAILED_HELP)


def BackendBucketArgumentForUrlMap(required=True):
  return compute_flags.ResourceArgument(
      resource_name='backend bucket',
      name='--default-backend-bucket',
      required=required,
      completer=BackendBucketsCompleter,
      global_collection='compute.backendBuckets')


def AddCdnSignedUrlKeyName(parser):
  """Adds the Cloud CDN Signed URL key name argument to the argparse."""
  parser.add_argument(
      '--key-name', required=True, help='Name of the Cloud CDN Signed URL key.')


def AddCdnSignedUrlKeyFile(parser):
  """Adds the Cloud CDN Signed URL key file argument to the argparse."""
  parser.add_argument(
      '--key-file',
      required=True,
      metavar='LOCAL_FILE_PATH',
      help="""\
      The file containing the base64 encoded 128-bit secret key for Cloud CDN
      Signed URL. It is vital that the key is strongly random. One way to
      generate such a key is with the following command:

          head -c 16 /dev/random | base64 | tr +/ -_ > [KEY_FILE_NAME]

      """)


def AddSignedUrlCacheMaxAge(parser, unspecified_help=None):
  """Adds the Cloud CDN Signed URL cache max age argument to the argparse."""
  if unspecified_help is None:
    unspecified_help = ' If unspecified, the default value is 3600s.'
  parser.add_argument(
      '--signed-url-cache-max-age',
      type=arg_parsers.Duration(),
      help="""\
      The amount of time up to which the response to a signed URL request
      will be cached in the CDN. After this time period, the Signed URL will
      be revalidated before being served. Cloud CDN will internally act as
      though all responses from this backend had a
      `Cache-Control: public, max-age=[TTL]` header, regardless of any
      existing Cache-Control header. The actual headers served in responses
      will not be altered.{}

      For example, specifying `12h` will cause the responses to signed URL
      requests to be cached in the CDN up to 12 hours. Valid units for this flag
      are `s` for seconds, `m` for minutes, `h` for hours, and `d` for
      days.
      """.format(unspecified_help))
