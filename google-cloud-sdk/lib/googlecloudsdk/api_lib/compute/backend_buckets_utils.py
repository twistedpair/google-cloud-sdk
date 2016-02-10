# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Code that's shared between multiple backend-buckets subcommands."""


def AddUpdatableArgs(parser):
  """Adds top-level backend bucket arguments that can be updated."""
  parser.add_argument(
      'name',
      help='The name of the backend bucket.')

  parser.add_argument(
      '--description',
      help='An optional, textual description for the backend bucket.')

  gcs_bucket_name = parser.add_argument(
      '--gcs-bucket-name',
      help=('The name of the GCS Bucket to use.'))
  gcs_bucket_name.detailed_help = """\
      The name of the Google Cloud Storage bucket to serve from.
      The storage bucket must be owned by the project's owner.
      """

  enable_cdn = parser.add_argument(
      '--enable-cdn',
      action='store_true',
      default=None,  # Tri-valued, None => don't change the setting.
      help='Enable cloud CDN.')
  enable_cdn.detailed_help = """\
      Enable Cloud CDN for the backend bucket. Cloud CDN can cache HTTP
      responses from a backend bucket at the edge of the network, close to
      users.
      """
