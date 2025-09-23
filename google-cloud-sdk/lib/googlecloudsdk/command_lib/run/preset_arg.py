# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Provides an ArgType for --preset flags.

This is a custom ArgType for the --preset flag that allows users to specify a
preset name with a dictionary of parameters for that preset.

Example:
  --preset my-preset:key1=value1,key2=value2
"""

import re

from googlecloudsdk.calliope import arg_parsers


class PresetArg(arg_parsers.ArgDict):
  """Interpret argument as a named dict.

  The string before the colon is the preset name and the string after is a
  dictionary of parameters for the preset.

    --preset my-preset:key1=value1,key2=value2
  """

  def __init__(self, key_type=None, value_type=None, cleanup_input=True):
    super().__init__(
        key_type=key_type, value_type=value_type, cleanup_input=cleanup_input
    )
    preset_param_pattern = '([^:]+)(:?)(.*)'
    self.preset_arg_matcher = re.compile(preset_param_pattern, re.DOTALL)

  def __call__(self, arg_value):  # pylint:disable=missing-docstring
    match = self.preset_arg_matcher.match(arg_value)
    if not match:
      raise arg_parsers.ArgumentTypeError(
          'Invalid preset value [{0}], expected format is'
          ' <preset_name>:<key1>=<value1>,<key2>=<value2>.'.format(arg_value)
      )
    preset_name = match.group(1)
    params_dict = super().__call__(match.group(3))
    return {'name': preset_name, 'params': params_dict}

  @property
  def hidden(self):
    return False

  def GetUsageMetavar(self, is_custom_metavar, metavar):
    del is_custom_metavar  # unused
    return metavar
