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
from googlecloudsdk.core import log
from googlecloudsdk.core.util import iso_duration
from googlecloudsdk.core.util import times

VIDEO_API = 'videointelligence'
VIDEO_API_VERSION_BETA = 'v1beta2'
OPERATIONS_VERSION = 'v1'

INPUT_ERROR_MESSAGE = ('[{}] is not a valid format for video input. Must be a '
                       'local path or a Google Cloud Storage URI '
                       '(format: gs://bucket/file).')

OUTPUT_ERROR_MESSAGE = ('[{}] is not a valid format for result output. Must be '
                        'a Google Cloud Storage URI '
                        '(format: gs://bucket/file).')

SEGMENT_ERROR_MESSAGE = ('Could not get video segments from [{0}]. '
                         'Please make sure you give the desired '
                         'segments in the form: START1:END1,START2:'
                         'END2, etc.: [{1}]')


class Error(exceptions.Error):
  """Base error class for this module."""


class SegmentError(Error):
  """Error for poorly formatted video segment messages."""


class VideoUriFormatError(Error):
  """Error if the video input URI is invalid."""


def GetApiClientInstance(version=VIDEO_API_VERSION_BETA, no_http=False):
  return apis.GetClientInstance(VIDEO_API, version, no_http=no_http)


def GetApiMessagesModule(client=None):
  client = client or GetApiClientInstance()
  return client.MESSAGES_MODULE


class VideoClient(object):
  """Wrapper class for videointelligence apitools client."""

  def __init__(self, no_http=False):
    self.version = VIDEO_API_VERSION_BETA
    self.client = GetApiClientInstance(VIDEO_API_VERSION_BETA, no_http)
    self.messages = GetApiMessagesModule(self.client)

    # Add message module and client that are used only for interacting
    # with the operations service (requires different version).
    self.operations_client = GetApiClientInstance(OPERATIONS_VERSION)
    self.operations_messages = GetApiMessagesModule(self.operations_client)
    self._ShortenMessages()

  def GetMessageClass(self, msg_str):
    """Get API client message class for this client.

    Args:
      msg_str: str, the message name or suffix to retrieve from self.messages.

    Returns:
      the Api message class.
    """
    return GetApiMessage(msg_str=msg_str,
                         api_version=self.version,
                         msg_module=self.messages)

  def _ShortenMessages(self):
    """Shorten variables for convenience/line length."""
    self.segment_msg = self.GetMessageClass('VideoSegment')
    self.req_msg = self.GetMessageClass('AnnotateVideoRequest')
    self.context_msg = self.GetMessageClass('VideoContext')
    self.features_enum = self.req_msg.FeaturesValueListEntryValuesEnum
    self._SetContextConfigs()

  def _SetContextConfigs(self):
    """Initialize correct message objects to configure Video Context."""
    self.explicit_config = self.GetMessageClass(
        'ExplicitContentDetectionConfig')
    self.shot_config = self.GetMessageClass('ShotChangeDetectionConfig')
    self.detection_config = self.GetMessageClass('LabelDetectionConfig')
    self.detection_msg = self.detection_config.LabelDetectionModeValueValuesEnum

  def GetContext(self,
                 segment_messages=None,
                 label_detection_mode=None,
                 explicit_content_model=None,
                 shot_change_model=None):
    """Get VideoContext message from information about context.

    Args:
      segment_messages: [messages.
                         GoogleCloudVideointelligenceXXXVideoSegment]
                         | None,
                         the list of segment messages for the context, if any.
      label_detection_mode: str for the detection mode for label detection.
      explicit_content_model: str, Model to use for explicit content detection.
      shot_change_model: str, Model to use for shot change detection

    Raises:
      ValueError: label_detection_mode is not a string or
        a LabelDetectionModeValueValuesEnum value.
    Returns:
      the Context message.
    """
    detection_models = (label_detection_mode or
                        explicit_content_model or
                        shot_change_model)
    if not segment_messages and not detection_models:
      return None

    if label_detection_mode:
      if (not isinstance(label_detection_mode, basestring) and
          not isinstance(label_detection_mode, self.detection_msg)):
        raise ValueError('label_detection_mode must be a string or a valid '
                         'LabelDetectionModeValueValuesEnum value.')

    context = self.context_msg()

    if segment_messages:
      context.segments = segment_messages

    if label_detection_mode:
      label_detection_config = self.detection_config()
      mode = label_detection_mode.upper().replace('-', '_')
      if not mode.endswith('_MODE'):
        mode += '_MODE'
      label_detection_config.labelDetectionMode = self.detection_msg(mode)
      context.labelDetectionConfig = label_detection_config

    if explicit_content_model:
      explicit_content_config = self.explicit_config()
      explicit_content_config.model = explicit_content_model
      context.explicitContentDetectionConfig = explicit_content_config

    if shot_change_model:
      shot_config = self.shot_config()
      shot_config.model = shot_change_model
      context.shotChangeDetectionConfig = shot_config

    return context

  def _GetAnnotateRequest(self, request_type, video_source, output_uri=None,
                          segments=None, region=None, detection_mode=None,
                          explicit_content_model=None, shot_change_model=None):
    """Builds an images.Annotate request from args given to a command.

    Args:
      request_type: messages.
          GoogleCloudVideointelligenceXXXAnnotateVideoRequest.
          FeaturesValueListEntryValuesEnum, the type of analysis desired.
      video_source: content_source.RemoteSource, the location of the video.
      output_uri: str, the location of the output file for analysis to be
          written to, if desired.
      segments: str, the segments of video to be analyzed.
      region: str, the location ID to request analysis be done in.
      detection_mode: str, the detection mode if label detection is requested.
      explicit_content_model: str, Model to use for explicit content detection.
      shot_change_model: str, Model to use for shot change detection.

    Raises:
      SegmentError: if given segments aren't properly formatted.

    Returns:
      messages.AnnotateRequest: a request for the API to annotate an image.
    """
    segs = ValidateAndParseSegments(segments)
    request = self.req_msg(features=[self.features_enum(request_type)])
    if output_uri:
      request.outputUri = output_uri
    if region:
      request.locationId = region
    video_source.UpdateContent(request)
    context = self.GetContext(segment_messages=segs,
                              label_detection_mode=detection_mode,
                              explicit_content_model=explicit_content_model,
                              shot_change_model=shot_change_model)
    request.videoContext = context
    return request

  def RequestAnnotation(self, request_type, input_uri, output_uri=None,
                        segments=None, region=None, detection_mode=None,
                        explicit_content_model=None, shot_change_model=None):
    """Builds and sends a videos.Annotate request from args given to a command.

    Args:
      request_type: string, the type of analysis desired. Must be
        'LABEL_DETECTION', 'FACE_DETECTION', 'SHOT_CHANGE_DETECTION' or
        'EXPLICIT_CONTENT_DETECTION'
      input_uri: str, the location of the video.
      output_uri: str, the location of the output file for analysis to be
        written to, if desired.
      segments: str, the segments of video to be analyzed.
      region: str, the region where the analysis should be done.
      detection_mode: str, the detection mode if label detection is requested.
      explicit_content_model: str, Model to use for explicit content detection.
      shot_change_model: str, Model to use for shot change detection.

    Raises:
      VideoUriFormatError: if the input path or output URI are incorrectly
          formatted.
      SegmentError: if given segments aren't properly formatted.

    Returns:
      messages.GoogleLongrunningOperation, the result of the request.
    """
    output_uri = _ValidateOutputUri(output_uri)
    video_source = _ValidateAndParseInput(input_uri)
    request = self._GetAnnotateRequest(
        request_type, video_source, output_uri=output_uri,
        segments=segments, region=region, detection_mode=detection_mode,
        explicit_content_model=explicit_content_model,
        shot_change_model=shot_change_model)
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


def GetApiMessage(msg_str, api_version, msg_module=None):
  """Get API message class based on api version.

  Args:
    msg_str: str, the message name or suffix to retrieve from api messages
      module.
    api_version:  str, videointelligence api version to retrieve
      messages from.
    msg_module: obj, API messages module to retrieve messages from. If not
      supplied, then will use api_version to get messages module.

  Returns:
    the Api message class.
  """
  message_module = msg_module or GetApiMessagesModule(
      GetApiClientInstance(api_version, no_http=True))

  return getattr(message_module, 'GoogleCloudVideointelligence' +
                 api_version.capitalize() + msg_str)


def ValidateAndParseSegments(given_segments):
  """Get VideoSegment messages from string of form START1:END1,START2:END2....

  Args:
    given_segments: [str], the list of strings representing the segments.

  Raises:
    SegmentError: if the string is malformed.

  Returns:
    [GoogleCloudVideointelligenceXXXVideoSegment], the messages
      representing the segments or None if no segments are specified.
  """
  if not given_segments:
    return None

  segment_msg = GetApiMessage('VideoSegment', VIDEO_API_VERSION_BETA)
  segment_messages = []
  segments = [s.split(':') for s in given_segments]
  for segment in segments:
    if len(segment) != 2:
      raise SegmentError(SEGMENT_ERROR_MESSAGE.format(
          ','.join(given_segments), 'Missing start/end segment'))
    start, end = segment[0], segment[1]
    # v1beta2 requires segments as a duration string representing the
    # count of seconds and fractions of seconds to nanosecond resolution
    # e.g. offset "42.596413s". To perserve backward compatibility with v1beta1
    # we will parse any segment timestamp with out a duration unit as an
    # int representing microseconds.
    try:
      start_duration = _ParseSegmentTimestamp(start)
      end_duration = _ParseSegmentTimestamp(end)
    except ValueError as ve:
      raise SegmentError(SEGMENT_ERROR_MESSAGE.format(
          ','.join(given_segments), ve))

  sec_fmt = '{}s'
  segment_messages.append(segment_msg(
      endTimeOffset=sec_fmt.format(end_duration.total_seconds),
      startTimeOffset=sec_fmt.format(start_duration.total_seconds)))
  return segment_messages


def _ParseSegmentTimestamp(timestamp_string):
  """Parse duration formatted segment timestamp into a Duration object.

  Assumes string with no duration unit specified (e.g. 's' or 'm' etc.) is
  an int representing microseconds.

  Args:
    timestamp_string: str, string to convert

  Raises:
    ValueError: timestamp_string is not a properly formatted duration, not a
    int or int value is <0

  Returns:
    Duration object represented by timestamp_string
  """
  # Assume timestamp_string passed as int number of microseconds if no unit
  # e.g. 4566, 100, etc.
  try:
    microseconds = int(timestamp_string)
  except ValueError:
    try:
      duration = times.ParseDuration(timestamp_string)
      if duration.total_seconds < 0:
        raise times.DurationValueError()
      return duration
    except (times.DurationSyntaxError, times.DurationValueError):
      raise ValueError('Could not parse timestamp string [{}]. Timestamp must '
                       'be a properly formatted duration string with time '
                       'amount and units (e.g. 1m3.456s, 2m, 14.4353s)'.format(
                           timestamp_string))
  else:
    log.warn("Time unit missing ('s', 'm','h') for segment timestamp [{}], "
             "parsed as microseconds.".format(timestamp_string))

  if microseconds < 0:
    raise ValueError('Could not parse duration string [{}]. Timestamp must be'
                     'greater than >= 0)'.format(timestamp_string))

  return iso_duration.Duration(microseconds=microseconds)


def _ValidateOutputUri(output_uri):
  """Validates given output URI against validator function.

  Args:
    output_uri: str, the output URI for the analysis.

  Raises:
    VideoUriFormatError: if the URI is not valid.

  Returns:
    str, The same output_uri.
  """
  if output_uri and not storage_util.ObjectReference.IsStorageUrl(output_uri):
    raise VideoUriFormatError(OUTPUT_ERROR_MESSAGE.format(output_uri))
  return output_uri


def _ValidateAndParseInput(input_path):
  """Validates input path and returns content_source.ContentSource object.

  Args:
    input_path: str, the location of the video.

  Raises:
    VideoUriFormatError: if the video path is invalid.

  Returns:
    (content_source.ContentSoallurce) the source object.
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


def _UpdateRequestWithInput(unused_ref, args, request):
  """The Python hook for yaml commands to inject content into the request."""
  video_source = _ValidateAndParseInput(args.input_path)
  video_source.UpdateContent(request)
  return request
