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

from googlecloudsdk.calliope import base


SERVICE_ACCOUNT_HELP = (
    'This command requires a service account from a project that has enabled '
    'the Video Intelligence API. To learn more about how to use a service '
    'account with gcloud, please run '
    '`gcloud auth activate-service-account --help`.')


_REGIONS = ['us-east1', 'us-west1', 'europe-west1', 'asia-east1']


def AddVideoFlags(parser):
  """Adds flags common to gcloud ml video-intelligence commands to the parser.

  Adds positional INPUT_PATH and the following optional flags: --output-uri,
  --segments, --async, --region.

  Args:
    parser: the parser for the command line.
  """
  base.ASYNC_FLAG.AddToParser(parser)
  parser.add_argument(
      'input_path',
      help=('The path to the video to be analyzed. Must be a local path '
            'or a Google Cloud Storage URI.')
  )
  parser.add_argument(
      '--output-uri',
      metavar='OUTPUT_URI',
      help=('The location to which the results should be written. Must be '
            'a Google Cloud Storage URI.')
  )
  parser.add_argument(
      '--segments',
      metavar='SEGMENTS',
      help=('The segments from the video which you want to analyze (by '
            'default, the entire video will be treated as one segment). '
            'Must be in the format START1:END1[,START2:END2,...]. Start '
            'and end of segments are in microseconds (inclusive).')
  )
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
