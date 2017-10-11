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
"""Flags and utilities for `gcloud ml video` commands."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


SERVICE_ACCOUNT_HELP = (
    'This command requires a service account from a project that has enabled '
    'the Video Intelligence API. To learn more about how to use a service '
    'account with gcloud, please run '
    '`gcloud auth activate-service-account --help`.')


_REGIONS = ['us-east1', 'us-west1', 'europe-west1', 'asia-east1']


IMAGE_PATH_FLAG = base.Argument(
    'input_path',
    help=('The path to the video to be analyzed. Must be a local path '
          'or a Google Cloud Storage URI.'))


def AddVideoFlags(parser):
  """Adds flags common to gcloud ml video-intelligence commands to the parser.

  Adds positional INPUT_PATH and the following optional flags: --output-uri,
  --segments, --async, --region.

  Args:
    parser: the parser for the command line.
  """
  base.ASYNC_FLAG.AddToParser(parser)
  IMAGE_PATH_FLAG.AddToParser(parser)
  parser.add_argument(
      '--output-uri',
      metavar='OUTPUT_URI',
      help=('The location to which the results should be written. Must be '
            'a Google Cloud Storage URI.')
  )
  parser.add_argument(
      '--segments',
      metavar='SEGMENTS',
      type=arg_parsers.ArgList(),
      help=("""\
      The segments from the video which you want to analyze (by default, the
      entire video will be treated as one segment). Must be in the format
      START1:END1[,START2:END2,...] (inclusive). START and END of segments must
      be a properly formatted duration string of the form `HhMmSs` where:

      *  H is the number of hours from beginning of video
      *  M is the number of minutes from the beginning of video
      *  S is the number of seconds from the beginning of the video

      H, M and S can be specified as ints or floats for fractional units
      (to microsecond resolution). Unit chars (e.g. `h`, `m` or `s`) are
      required. Microseconds can be specified using fractional seconds
      e.g. 0.000569s == 569 microseconds.

      Examples:
      0s:23.554048s,24s:29.528064s

      0:1m40s,3m50s:5m10.232265s
      """))
  parser.add_argument(
      '--region',
      metavar='REGION',
      choices=_REGIONS,
      help=('Optional cloud region where annotation should take place. '
            'If no region is specified, a region will be determined '
            'based on video file location.'))


def AddDetectionModeFlag(parser):
  """Add --detection-mode to given parser."""
  parser.add_argument(
      '--detection-mode',
      metavar='DETECTION_MODE',
      choices=['shot', 'frame', 'shot-and-frame'],
      default='shot',
      help='The mode of label detection requested.')


def AdditionalFlagsHook():
  """The Python hook for yaml commands to add the image flag."""
  return [IMAGE_PATH_FLAG]
