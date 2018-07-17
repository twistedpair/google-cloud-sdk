# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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

"""Utilities for handling YAML schemas for gcloud export/import commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import io
import re
import textwrap

from googlecloudsdk.core.resource import resource_projector
from googlecloudsdk.core.resource import yaml_printer

import six


_SPEC_DESCRIPTION = 'A gcloud export/import command YAML validation schema.'

_WIDTH = 80  # YAML list line width
_MINWRAP = 40  # The minimum text wrap width if nesting is too deep.
_INDENT = 2  # YAML nested object indentation
_DESCRIPTION_INDENT = len('description: ') - _INDENT
_YAML_WORKAROUND = '<YAML-WORKAROUND/>'

_OPTIONAL = 'Optional.'
_OUTPUT_ONLY = 'Output only.'
_REQUIRED = 'Required.'


def _WrapDescription(depth, text):
  """Returns description: |- text wrapped so it won't exceed _WIDTH at depth.

  The YAML representer doesn't seem to take the length of the current tag
  into account when deciding whether to inline strings or use |-. In this case
  the tag is always "description: ". This function detects when YAML would fail
  and adds temporary marker lines to produce the desired output. The marker
  lines are removed prior to final output.

  Args:
    depth: The nested dict depth.
    text: The text string to wrap.

  Returns:
    Text wrapped so it won't exceed _WIDTH at depth.
  """
  width = _WIDTH - (depth * _INDENT)
  lines = textwrap.wrap(text, max(_MINWRAP, width))
  if len(lines) != 1:
    return '\n'.join(lines)
  line = lines[0]
  nudge = width - (len(line) + _DESCRIPTION_INDENT)
  if nudge < 0:
    # nudge<0 means we are in the YAML bug zone and we nudge the representer to
    # fall through to the |- form by adding enough spaces and a marker. The
    # marker lines are removed prior to final output.
    return line + '\n' + nudge * ' ' + _YAML_WORKAROUND
  return line


def _NormalizeTypeName(name):
  """Returns the YAML-normalized type name for name."""
  s = six.text_type(name).lower()
  if re.match(r'^int\d*$', s):
    return 'integer'
  if s == 'bool':
    return 'boolean'
  return s


def _GetRequiredFields(fields):
  """Returns the list of required field names in fields.

  Args:
    fields: A message spec fields dict.

  Returns:
    The list of required field names in fields.
  """
  required = []
  for name, value in six.iteritems(fields):
    description = value['description']
    # NOTE: Protobufs use the special field name 'additionalProperties' to
    # encode additional self-defining properties. This allows an API to extend
    # proto data without changing the proto description, at the cost of being
    # stringy-typed. JSON schema uses the 'additionalProperties' bool property
    # to declare if only properties declared in the schema are allowed (false)
    # or if properties not in the schema are allowed (true).
    if name != 'additionalProperties' and description.startswith(_REQUIRED):
      required.append(name)
  return required


def _AddRequiredFields(spec, fields):
  required = _GetRequiredFields(fields)
  if required:
    spec['required'] = sorted(required)


def _AddFields(depth, parent, spec, fields):
  """Adds message fields to the YAML spec.

  Args:
      depth: The nested dict depth.
      parent: The parent spec (nested ordered dict to add fields to) of spec.
      spec: The nested ordered dict to add fields to.
      fields: A message spec fields dict to add to spec.
  """
  depth += 2
  for name, value in sorted(six.iteritems(fields)):
    description = value['description'].strip()
    if description.startswith(_OPTIONAL):
      description = description[len(_OPTIONAL):].strip()
    elif description.startswith(_REQUIRED):
      description = description[len(_REQUIRED):].strip()
    if description.startswith(_OUTPUT_ONLY):
      continue

    d = collections.OrderedDict()
    spec[name] = d
    d['description'] = _WrapDescription(depth, description)

    if value.get('repeated'):
      d['type'] = 'array'
      items = collections.OrderedDict()
      d['items'] = items
      d = items
      depth += 2

    subfields = value.get('fields')
    if subfields:
      d['type'] = 'object'
      properties = collections.OrderedDict()
      if False and name == 'additionalProperties':
        del spec[name]
        _AddFields(depth, d, properties, subfields)
        if properties:
          parent[name] = properties
      else:
        _AddRequiredFields(d, subfields)
        d['additionalProperties'] = False
        _AddFields(depth, d, properties, subfields)
        if properties:
          d['properties'] = properties
    else:
      type_name = _NormalizeTypeName(value.get('type', 'boolean'))
      if type_name == 'enum':
        enum = value.get('choices')
        d['type'] = 'string'
        d['enum'] = sorted([n for n, _ in six.iteritems(enum)])
      else:
        d['type'] = type_name


def _GenerateSchema(api, message_name, message_spec):
  """Generates the export/import YAML schema for message_spec in api.

  Args:
    api: An API registry object.
    message_name: The API message name for message_spec.
    message_spec: An arg_utils.GetRecursiveMessageSpec() message spec.

  Returns:
    The YAML schema ordered dict.
  """
  spec = collections.OrderedDict()
  spec['title'] = '{} {} {} export schema'.format(
      api.name, api.version, message_name)
  spec['description'] = _SPEC_DESCRIPTION
  spec['type'] = 'object'
  _AddRequiredFields(spec, message_spec)
  spec['additionalProperties'] = False
  properties = collections.OrderedDict()
  spec['properties'] = properties
  type_string = {'type': 'string'}

  # COMMENT ignored by import commands
  comment = collections.OrderedDict()
  properties['COMMENT'] = comment
  comment['type'] = 'object'
  comment['description'] = 'User specified info ignored by gcloud import.'
  comment['additionalProperties'] = False
  comment_properties = collections.OrderedDict()
  comment['properties'] = comment_properties
  comment_properties['template-id'] = collections.OrderedDict(type_string)
  comment_properties['region'] = collections.OrderedDict(type_string)
  comment_properties['description'] = collections.OrderedDict(type_string)
  comment_properties['date'] = collections.OrderedDict(type_string)
  comment_properties['version'] = collections.OrderedDict(type_string)

  # UNKNOWN marks incomplete export data
  unknown = collections.OrderedDict()
  properties['UNKNOWN'] = unknown
  unknown['type'] = 'array'
  unknown['description'] = 'Unknown API fields that cannot be imported.'
  unknown['items'] = type_string

  _AddFields(1, spec, properties, message_spec)
  return spec


def GetExportSchema(api, message_name, message_spec):
  """Returns the export/import YAML schema text for message_spec in api.

  Args:
    api: An API registry object.
    message_name: The message name in the api.
    message_spec: An arg_utils.GetRecursiveMessageSpec() message spec.

  Returns:
    The export/import YAML schema text for message_spec in api.
  """
  spec = _GenerateSchema(api, message_name, message_spec)
  tmp = io.StringIO()
  tmp.write('$schema: "http://json-schema.org/draft-06/schema#"\n\n')
  yaml_printer.YamlPrinter(
      name='yaml',
      projector=resource_projector.IdentityProjector(),
      out=tmp).Print(spec)
  return re.sub('\n *{}\n'.format(_YAML_WORKAROUND), '\n', tmp.getvalue())
