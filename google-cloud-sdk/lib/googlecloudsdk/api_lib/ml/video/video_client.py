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
"""Utilities for gcloud ml video-intelligence commands."""

import base64

from googlecloudsdk.api_lib.ml import content_source
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import exceptions

VIDEO_API = 'videointelligence'
VIDEO_API_VERSION = 'v1beta1'
OPERATIONS_VERSION = 'v1'

INPUT_ERROR_MESSAGE = ('[{}] is not a valid format for video input. Must be a '
                       'local path or a Google Cloud Storage URI '
                       '(format: gs://bucket/file).')

OUTPUT_ERROR_MESSAGE = ('[{}] is not a valid format for result output. Must be '
                        'a Google Cloud Storage URI '
                        '(format: gs://bucket/file).')


class Error(exceptions.Error):
  """Base error class for this module."""


class SegmentError(Error):
  """Error for poorly formatted video segment messages."""


class VideoUriFormatError(Error):
  """Error if the video input URI is invalid."""


def GetVideoMessages(version=VIDEO_API_VERSION):
  return apis.GetMessagesModule(VIDEO_API, version)


class VideoClient(object):
  """Wrapper for videointelligence apitools client."""

  def __init__(self):
    self.messages = apis.GetMessagesModule(VIDEO_API, VIDEO_API_VERSION)
    self.client = apis.GetClientInstance(VIDEO_API, VIDEO_API_VERSION)

    # Shorten variables for convenience/line length.
    msgs = self.messages
    self.segment_msg = msgs.GoogleCloudVideointelligenceV1beta1VideoSegment
    self.req_msg = msgs.GoogleCloudVideointelligenceV1beta1AnnotateVideoRequest
    self.context_msg = msgs.GoogleCloudVideointelligenceV1beta1VideoContext
    self.detection_msg = self.context_msg.LabelDetectionModeValueValuesEnum
    self.features_enum = self.req_msg.FeaturesValueListEntryValuesEnum

    # Add message module and client that are used only for interacting
    # with the operations service (requires different version).
    self.operations_messages = apis.GetMessagesModule(
        VIDEO_API, OPERATIONS_VERSION)
    self.operations_client = apis.GetClientInstance(
        VIDEO_API, OPERATIONS_VERSION)

  def _ValidateAndParseSegments(self, given_segments):
    """Get VideoSegment messages from string of form START1:END1,START2:END2....

    Args:
      given_segments: str, the string representing the segments.

    Raises:
      SegmentError: if the string is malformed.

    Returns:
      [GoogleCloudVideointelligenceV1beta1VideoSegment], the messages
        representing the segments.
    """
    segment_messages = []
    segments = [s.split(':') for s in given_segments.split(',')]
    for segment in segments:
      if len(segment) != 2:
        raise SegmentError('Could not get video segments from [{}]. '
                           'Please make sure you give the desired '
                           'segments in the form: START1:END1,START2:'
                           'END2, etc.'.format(given_segments))
      start, end = int(segment[0]), int(segment[1])
      segment_messages.append(
          self.segment_msg(
              startTimeOffset=start,
              endTimeOffset=end))
    return segment_messages

  def _ValidateAndParseInput(self, input_path):
    """Validates input path and returns content_source.ContentSource object.

    Args:
      input_path: str, the location of the video.

    Raises:
      VideoUriFormatError: if the video path is invalid.

    Returns:
      (content_source.ContentSource) the source object.
    """
    try:
      video_source = content_source.ContentSource.FromContentPath(
          input_path,
          VIDEO_API,
          url_validator=storage_util.ObjectReference.IsStorageUrl,
          encode=base64.b64encode
      )
    except content_source.UnrecognizedContentSourceError:
      raise VideoUriFormatError(INPUT_ERROR_MESSAGE.format(input_path))
    return video_source

  def _ValidateOutputUri(self, output_uri):
    """Validates given output URI against validator function.

    Args:
      output_uri: str, the output URI for the analysis.

    Raises:
      VideoUriFormatError: if the URI is not valid.
    """
    if output_uri and not storage_util.ObjectReference.IsStorageUrl(output_uri):
      raise VideoUriFormatError(OUTPUT_ERROR_MESSAGE.format(output_uri))

  def _GetContext(self, segment_messages, detection_mode):
    """Get VideoContext message from information about context.

    Args:
      segment_messages: [messages.
                         GoogleCloudVideointelligenceV1beta1VideoSegment]
                         | None,
                         the list of segment messages for the context, if any.
      detection_mode: str, the detection mode for label detection.

    Returns:
      the Context message.
    """
    context = self.context_msg()
    if segment_messages:
      context.segments = segment_messages
    if detection_mode:
      mode = detection_mode.upper().replace('-', '_') + '_MODE'
      context.labelDetectionMode = self.detection_msg(mode)
    return context

  def _GetAnnotateRequest(self, request_type, video_source, output_uri=None,
                          segments=None, region=None, detection_mode=None):
    """Builds an images.Annotate request from args given to a command.

    Args:
      request_type: messages.
          GoogleCloudVideointelligenceV1beta1AnnotateVideoRequest.
          FeaturesValueListEntryValuesEnum, the type of analysis desired.
      video_source: content_source.RemoteSource, the location of the video.
      output_uri: str, the location of the output file for analysis to be
          written to, if desired.
      segments: str, the segments of video to be analyzed.
      region: str, the location ID to request analysis be done in.
      detection_mode: str, the detection mode if label detection is requested.

    Raises:
      SegmentError: if given segments aren't properly formatted.

    Returns:
      messages.AnnotateRequest: a request for the API to annotate an image.
    """
    segs = self._ValidateAndParseSegments(segments) if segments else None
    request = self.req_msg(features=[self.features_enum(request_type)])
    if output_uri:
      request.outputUri = output_uri
    if region:
      request.locationId = region
    video_source.UpdateContent(request)
    context = self._GetContext(segs, detection_mode)
    request.videoContext = context
    return request

  def RequestAnnotation(self, request_type, input_uri, output_uri=None,
                        segments=None, region=None, detection_mode=None):
    """Builds and sends a videos.Annotate request from args given to a command.

    Args:
      request_type: string, the type of analysis desired. Must be
        'LABEL_DETECTION', 'FACE_DETECTION', or 'SHOT_CHANGE_DETECTION'.
      input_uri: str, the location of the video.
      output_uri: str, the location of the output file for analysis to be
        written to, if desired.
      segments: str, the segments of video to be analyzed.
      region: str, the region where the analysis should be done.
      detection_mode: str, the detection mode if label detection is requested.

    Raises:
      VideoUriFormatError: if the input path or output URI are incorrectly
          formatted.
      SegmentError: if given segments aren't properly formatted.

    Returns:
      messages.GoogleLongrunningOperation, the result of the request.
    """
    self._ValidateOutputUri(output_uri)
    video_source = self._ValidateAndParseInput(input_uri)
    request = self._GetAnnotateRequest(
        request_type, video_source, output_uri=output_uri,
        segments=segments, region=region, detection_mode=detection_mode)
    return self.client.videos.Annotate(request)

  def GetOperation(self, operation_ref):
    """Gets description of a long-running operation.

    Args:
      operation_ref: the operation reference.

    Returns:
      messages.GoogleLongrunningOperation, the operation.
    """
    return self.operations_client.operations.Get(
        self.operations_messages.VideointelligenceOperationsGetRequest(
            name=operation_ref.operationsId))

  def WaitOperation(self, operation_ref):
    """Waits for a long-running operation.

    Args:
      operation_ref: the operation reference.

    Raises:
      waiter.OperationError: if the operation contains an error.

    Returns:
      messages.AnnotateVideoResponse, the final result of the operation.
    """
    message = 'Waiting for operation [{}] to complete'.format(
        operation_ref.operationsId)
    return waiter.WaitFor(
        waiter.CloudOperationPollerNoResources(
            self.operations_client.operations,
            # TODO(b/62478975): remove this workaround when operation resources
            # are compatible with gcloud parsing.
            get_name_func=lambda x: x.operationsId),
        operation_ref,
        message,
        exponential_sleep_multiplier=2.0,
        sleep_ms=500,
        wait_ceiling_ms=20000)
