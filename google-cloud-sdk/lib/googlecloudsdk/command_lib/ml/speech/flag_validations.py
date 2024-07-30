# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Validation functions for speech commands flags."""

import os
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.calliope import exceptions


EXPLICIT_ENCODING_OPTIONS = ('LINEAR16', 'MULAW', 'ALAW')
ENCODING_OPTIONS = frozenset(EXPLICIT_ENCODING_OPTIONS) | {'AUTO'}


def ValidateSpeakerDiarization(args):
  """Validates speaker diarization flag input."""
  if (
      args.min_speaker_count is not None and args.max_speaker_count is not None
  ) and (args.min_speaker_count > args.max_speaker_count):
    raise exceptions.InvalidArgumentException(
        '--max-speaker-count',
        '[--max-speaker-count] must be equal to or larger than'
        ' min-speaker-count.',
    )


def ValidateAudioSource(args, batch=False):
  """Validates audio source flag input."""
  if storage_util.ObjectReference.IsStorageUrl(args.audio):
    return

  if batch:
    raise exceptions.InvalidArgumentException(
        '--audio',
        'Invalid audio source [{}]. The source must be a Google Cloud'
        ' Storage URL (such as gs://bucket/object).'.format(args.audio),
    )

  if not os.path.isfile(args.audio):
    raise exceptions.InvalidArgumentException(
        '--audio',
        'Invalid audio source [{}]. The source must either be a local '
        'path or a Google Cloud Storage URL '
        '(such as gs://bucket/object).'.format(args.audio),
    )


def ValidateDecodingConfig(args):
  """Validates encoding flag input."""
  if args.encoding is None:
    return
  if args.encoding not in ENCODING_OPTIONS:
    raise exceptions.InvalidArgumentException(
        '--encoding',
        '[--encoding] must be set to one of '
        + ', '.join(sorted(ENCODING_OPTIONS)),
    )
  if args.encoding == 'AUTO':
    if args.sample_rate is not None or args.audio_channel_count is not None:
      raise exceptions.InvalidArgumentException(
          '--sample-rate'
          if args.sample_rate is not None
          else '--audio-channel-count',
          'AUTO encoding does not support setting sample rate or audio'
          ' channel count.',
      )
  else:
    if args.sample_rate is None:
      raise exceptions.InvalidArgumentException(
          '--sample-rate',
          '[--sample-rate] must be specified when configuring explicit'
          ' encoding options '
          + ', '.join(sorted(EXPLICIT_ENCODING_OPTIONS))
          + '.',
      )
    if args.audio_channel_count is None:
      raise exceptions.InvalidArgumentException(
          '--audio-channel-count',
          (
              '[--audio-channel-count] must be specified when configuring'
              ' explicit encoding options '
              + ', '.join(sorted(EXPLICIT_ENCODING_OPTIONS))
          ),
      )

