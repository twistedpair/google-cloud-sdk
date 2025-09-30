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
"""Custom printer for Cloud Run presets."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import textwrap

from googlecloudsdk.core.resource import custom_printer_base as cp

PRESETS_PRINTER_FORMAT = 'presets'
_NAME_COL_WIDTH = 21
_DESC_COL_WIDTH = 38
_REQ_COL_WIDTH = 7
_INFO_INDENT_WIDTH = 16
_MAX_WIDTH = 80

PRESETS_ENUM_MAP = {
    'KIND_UNSPECIFIED': 'Unspecified',
    'CATEGORY_UNSPECIFIED': 'Unspecified',
    'CATEGORY_QUICKSTART': 'Quickstart',
    'CATEGORY_ADDON': 'Add-on',
    'CATEGORY_OPTIMIZATION': 'Optimization',
}


def _format_enum(enum_string):
  """Formats a generic enum string into a title."""
  if not enum_string:
    return ''
  if enum_string in PRESETS_ENUM_MAP:
    return PRESETS_ENUM_MAP[enum_string]
  return enum_string.replace('_', ' ').title()


def _format_kind_list(kind_list):
  """Formats a list of kind enum strings for display."""
  if not kind_list:
    return 'None'
  return ', '.join(_format_enum(kind) for kind in kind_list)


class PresetsPrinter(cp.CustomPrinterBase):
  """Prints a Cloud Run preset in a custom human-readable format."""

  def Transform(self, preset):
    """Transforms a preset into a structured output."""
    return cp.Lines([
        cp.Lines([' ']),
        self._get_preset_info(preset),
        cp.Lines([' ']),
        self._get_preset_inputs(preset),
        cp.Lines([' ']),
        self._get_key_preset_config(preset),
        cp.Lines([' ']),
        self._get_usage(preset),
        cp.Lines([' ']),
    ])

  def _get_preset_info(self, preset):
    """Formats the preset info section."""
    fields = [
        ('Name:', str(preset.get('name', ''))),
        ('Category:', _format_enum(preset.get('category', ''))),
        (
            'Applies to:',
            _format_kind_list(preset.get('supported_resources', [])),
        ),
        ('Description:', str(preset.get('description', ''))),
        ('Preset Version:', str(preset.get('version', ''))),
    ]

    lines = []
    for label, value in fields:
      if not value:
        continue
      wrapped_lines = textwrap.wrap(
          value, width=_MAX_WIDTH - _INFO_INDENT_WIDTH
      )
      first_line = wrapped_lines[0] if wrapped_lines else ''
      lines.append(label.ljust(_INFO_INDENT_WIDTH) + first_line)
      for line in wrapped_lines[1:]:
        lines.append(' ' * _INFO_INDENT_WIDTH + line)

    return cp.Section([cp.Lines(lines)])

  def _format_row(self, name, desc, required):
    """Helper to format a single row with specific padding."""
    return (
        '  '
        + name.ljust(_NAME_COL_WIDTH)
        + ' '
        + desc.ljust(_DESC_COL_WIDTH)
        + ' '
        + required.ljust(_REQ_COL_WIDTH)
    )

  def _get_preset_inputs_header(self):
    """Returns the header for the preset inputs section."""
    return [
        'Inputs:',
        ' ',
        self._format_row('Name', 'Description', 'Required'),
        self._format_row(
            '-' * _NAME_COL_WIDTH, '-' * _DESC_COL_WIDTH, '-' * _REQ_COL_WIDTH
        ),
    ]

  def _get_preset_inputs(self, preset):
    """Formats the preset inputs section."""
    parameters = preset.get('parameters', [])
    if not parameters:
      return None

    inputs = self._get_preset_inputs_header()
    for param in parameters:
      name = param.get('name', '')
      desc = param.get('description', '')
      required = 'Yes' if param.get('required', False) else 'No'

      wrapped_desc = textwrap.wrap(desc, width=_DESC_COL_WIDTH)
      first_desc_line = wrapped_desc[0] if wrapped_desc else ''
      inputs.append(self._format_row(name, first_desc_line, required))
      for line in wrapped_desc[1:]:
        inputs.append(self._format_row('', line, ''))

    return cp.Section([cp.Lines(inputs)])

  def _get_key_preset_config(self, preset):
    """Formats the key preset configuration section."""
    config_values = preset.get('config_values', {})
    if not config_values:
      return None
    labeled_data = cp.Labeled(config_values.items())
    return cp.Section([
        cp.Labeled(
            [('Key Preset Configuration', cp.Lines([' ', labeled_data, ' ']))]
        )
    ])

  def _get_usage(self, preset):
    """Formats the preset gcloud usage section."""
    usage_lines = preset.get('example_gcloud_usage', [])
    if not usage_lines:
      return None

    if isinstance(usage_lines, str):
      usage_lines = [usage_lines]

    full_usage_string = [' ']
    full_usage_string.extend(usage_lines)
    full_usage_string.append(' ')
    return cp.Section(
        [cp.Labeled([('Usage', cp.Lines(full_usage_string))])]
    )
