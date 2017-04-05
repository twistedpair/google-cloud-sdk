# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Utilities for gcloud ml vision commands."""

from googlecloudsdk.api_lib.ml.vision import util


def RunVisionCommand(feature, image_path, max_results=None,
                     language_hints=None):
  """Runs gcloud ml vision commands.

  Args:
    feature: str, the type of feature being annotated.
    image_path: str, the path to an image.
    max_results: int, maximum number of results to get.
    language_hints: [str], a list of strings representing language hints.

  Raises:
    ImagePathError: if given image path does not exist and does not seem to be
        a remote URI.
    AnnotateException: if the annotation response contains an error.

  Returns:
    The results of the Annotate request.
  """

  client = util.GetVisionClient()
  request = util.GetAnnotateRequest(feature, image_path,
                                    language_hints=language_hints,
                                    max_results=max_results)
  response = client.images.Annotate(request)
  util.PossiblyRaiseException(response)
  return response


VISION_AUTH_HELP = ("""\
To use the Google Cloud Vision API, use a service account belonging to a
project that has Google Cloud Vision enabled. Please see
https://cloud.google.com/vision/docs/common/auth#set_up_a_service_account
for directions on setting up an account to use with the API. After setting up
the account, download the key file and run:

  $ gcloud auth activate-service-account --key-file=$KEY_FILE
""")
