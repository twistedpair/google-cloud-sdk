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
"""Utilities for videointelligence API."""

from googlecloudsdk.api_lib.ml.video import video_client
from googlecloudsdk.core import resources


def AnnotateVideo(feature, input_uri, output_uri=None, segments=None,
                  region=None, async=False, detection_mode=None):
  """Annotates video and waits for operation results if necessary.

  Args:
    feature: str, the name of the video analysis feature to request, depending
      on the command the user has called. Must be from options in
      GoogleCloudVideointelligenceV1beta1AnnotateVideoRequest.
      FeaturesValueListEntryValuesEnum.
    input_uri: str, the URI of the input content. Must be a
      Google Cloud Storage URI.
    output_uri: str, the URI for the results to be stored. Must be a Google
      Cloud Storage URI.
    segments: str | None, the segments of video to be analyzed in the form
      'start1:end1,start2:end2,...', if any.
    region: str | None, the Cloud Region to do analysis in, if any.
    async: bool, whether to return the operation right away (async) or wait for
      it to complete.
    detection_mode: str, the detection mode if the LABEL_DETECTION feature
      is being requested.

  Raises:
    SegmentError, if given segments aren't properly formatted.
    content_source.UnrecognizedContentError: if the input URI is incorrectly
      formatted.

  Returns:
    google.longrunning.Operation: the result of the video analysis
  """
  client = video_client.VideoClient()
  operation = client.RequestAnnotation(feature,
                                       input_uri,
                                       output_uri=output_uri,
                                       region=region,
                                       segments=segments,
                                       detection_mode=detection_mode)
  if async:
    return operation
  operation_ref = resources.REGISTRY.Parse(
      operation.name,
      collection='videointelligence.operations')
  return client.WaitOperation(operation_ref)
