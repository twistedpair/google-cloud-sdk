# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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
"""Rollout plans utility functions."""

import json
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files


def LoadWavesFromFileAndAddToRequest(file_path, messages):
  """Loads waves from the specified file, parses, and converts to messages."""
  try:
    content = files.ReadFileContents(file_path)
  except files.Error as e:
    raise calliope_exceptions.BadFileException(
        f'Failed to read contents of file [{file_path}]: {e}'
    )

  try:
    if file_path.lower().endswith('.json'):
      waves_data = json.loads(content)
    else:  # Assume YAML
      waves_data = yaml.load(content)
  except Exception as e:
    raise calliope_exceptions.BadFileException(
        f'Failed to parse contents of file [{file_path}]: {e}'
    )

  if not isinstance(waves_data, list):
    raise ValueError('The waves file must contain a LIST of wave definitions.')

  try:
    wave_messages = [
        _DictToWaveMessage(wave_dict, messages) for wave_dict in waves_data
    ]
  except Exception as e:
    raise ValueError(f'Error converting file content to API messages: {e}')

  return wave_messages


def _DictToWaveMessage(wave_dict, messages):
  """Recursively converts a dict to a messages.RolloutPlanWave object."""
  msg = messages.RolloutPlanWave()
  if 'displayName' in wave_dict:
    msg.displayName = wave_dict['displayName']

  # Selectors
  if 'selectors' in wave_dict:
    msg.selectors = []
    for sel_dict in wave_dict.get('selectors', []):
      sel_msg = messages.RolloutPlanWaveSelector()
      if 'locationSelector' in sel_dict:
        loc_sel = messages.RolloutPlanWaveSelectorLocationSelector(
            includedLocations=sel_dict['locationSelector'].get(
                'includedLocations', []
            )
        )
        sel_msg.locationSelector = loc_sel
      msg.selectors.append(sel_msg)

  # Validation
  if 'validation' in wave_dict:
    val_dict = wave_dict['validation']
    val_msg = messages.RolloutPlanWaveValidation()
    if 'type' in val_dict:
      val_msg.type = val_dict['type']
    if (
        val_dict.get('type') == 'time'
        and 'timeBasedValidationMetadata' in val_dict
    ):
      meta_dict = val_dict['timeBasedValidationMetadata']
      meta_msg = messages.RolloutPlanWaveValidationTimeBasedValidationMetadata()
      if 'waitDuration' in meta_dict:
        duration_input = meta_dict['waitDuration']
        if isinstance(duration_input, dict) and 'seconds' in duration_input:
          meta_msg.waitDuration = str(duration_input['seconds']) + 's'
        elif isinstance(duration_input, str):
          meta_msg.waitDuration = duration_input
        else:
          raise ValueError(f'Invalid format for waitDuration: {duration_input}')
      val_msg.timeBasedValidationMetadata = meta_msg
    msg.validation = val_msg
  return msg
