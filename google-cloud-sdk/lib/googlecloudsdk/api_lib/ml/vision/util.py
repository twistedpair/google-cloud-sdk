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

import os
import re

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions

VISION_API = 'vision'
VISION_API_VERSION = 'v1'
IMAGE_URI_FORMAT = r'^(https{,1}?|gs)://'


def GetVisionClient(version=VISION_API_VERSION):
  return apis.GetClientInstance(VISION_API, version)


def GetVisionMessages(version=VISION_API_VERSION):
  return apis.GetMessagesModule(VISION_API, version)


class Error(exceptions.Error):
  """Error for gcloud ml vision commands."""


class ImagePathError(Error):
  """Error if an image path is improperly formatted."""


class AnnotateException(Error):
  """Raised if the image annotation resulted in an error."""


def GetImageFromPath(path):
  """Builds an Image message from a path.

  Args:
    path: the path arg given to the command.

  Raises:
    ImagePathError: if the image path does not exist and does not seem to be
        a remote URI.

  Returns:
    vision_v1_messages.Image: an image message containing information for the
        API on the image to analyze.
  """
  messages = GetVisionMessages()
  image = messages.Image()
  if os.path.isfile(path):
    with open(path, 'rb') as content_file:
      image.content = content_file.read()
  elif re.match(IMAGE_URI_FORMAT, path):
    image.source = messages.ImageSource(imageUri=path)
  else:
    raise ImagePathError(
        'The image path does not exist locally or is not properly formatted. '
        'A URI for a remote image must be a Google Cloud Storage image URI, '
        'which must be in the form `gs://bucket_name/object_name`, or a '
        'publicly accessible image HTTP/HTTPS URL. Please double-check your '
        'input and try again.')
  return image


def GetAnnotateRequest(request_type, image_path,
                       language_hints=None, max_results=None):
  """Builds an images.Annotate request from args given to a command.

  Args:
    request_type: str, type of request.
    image_path: str, the path to an image.
    language_hints: [str], a list of strings representing language hints.
    max_results: int, maximum number of results to get.

  Raises:
    ImagePathError: if the image path does not exist and does not seem to be
        a remote URI.

  Returns:
    messages.AnnotateRequest: a request for the API to annotate an image.
  """
  messages = GetVisionMessages()
  image = GetImageFromPath(image_path)
  feature = messages.Feature(
      type=messages.Feature.TypeValueValuesEnum.lookup_by_name(request_type))
  if max_results:
    feature.maxResults = int(max_results)
  request = messages.AnnotateImageRequest(
      features=[feature],
      image=image)
  if language_hints:
    request.imageContext = messages.ImageContext(languageHints=language_hints)
  # If this is updated to allow batch responses, update PossiblyRaiseException
  # to handle multiple responses.
  return messages.BatchAnnotateImagesRequest(requests=[request])


def PossiblyRaiseException(response):
  """Checks for errors in a batch response.

  Since we currently allow only one request per batch request, any error
  response means that the entire request failed.

  Args:
    response: BatchAnnotateImagesResponse, the response from the client.

  Raises:
    AnnotateException: error from annotation response.
  """
  for r in response.responses:
    if r.error:
      raise AnnotateException('Code: [{}] Message: [{}]'.format(
          r.error.code,
          r.error.message))
