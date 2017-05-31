# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Utilities related to adding flags for the gcloud meta api commands."""

import re

from apitools.base.protorpclite import messages

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core.resource import resource_property


class ArgumentGenerator(object):
  """Class to generate argparse flags from apitools message fields."""

  TYPES = {
      messages.Variant.DOUBLE: float,
      messages.Variant.FLOAT: float,

      messages.Variant.INT64: long,
      messages.Variant.UINT64: long,
      messages.Variant.SINT64: long,

      messages.Variant.INT32: int,
      messages.Variant.UINT32: int,
      messages.Variant.SINT32: int,

      messages.Variant.BOOL: bool,
      messages.Variant.STRING: str,

      # TODO(b/38000796): Do something with bytes.
      messages.Variant.BYTES: None,
      messages.Variant.ENUM: None,
      messages.Variant.MESSAGE: None,
  }

  def __init__(self, method):
    """Creates a new Argument Generator.

    Args:
      method: APIMethod, The method to generate arguments for.
    """
    self.method = method

  def ResourceArg(self):
    """Gets the positional argument that represents the resource.

    Returns:
      {str, calliope.base.Argument}, The argument.
    """
    if not self.method.RequestCollection():
      log.warning('Not generating resource arg')
      return {}
    return {
        'resource': base.Argument(
            'resource',
            nargs='?',
            help='The GRI for the resource being operated on.')}

  def ResourceFlags(self):
    """Get the arguments to add to the parser that appear in the method path.

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    message = self.method.GetRequestType()
    field_helps = self._FieldHelpDocs(message)
    default_help = 'For substitution into: ' + self.method.detailed_path

    args = {}
    for param in set(self.method.ResourceFieldNames()):
      args[param] = base.Argument(
          # TODO(b/38000796): Consider not using camel case for flags.
          '--' + param,
          metavar=resource_property.ConvertToAngrySnakeCase(param),
          category='RESOURCE',
          type=str,
          help=field_helps.get(param, default_help))
    return args

  def MessageFieldFlags(self):
    """Get the arguments to add to the parser that appear in the method body.

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    return self._MessageFieldFlags('', self.method.GetRequestType())

  @classmethod
  def FlagNameForField(cls, method, prefix, field):
    """Compute the flag name to generate for the given message field.

    Args:
      method: APIMethod, The method to generate arguments for.
      prefix: str, A prefix to put on the flag (when generating flags for
        sub-messages).
      field: MessageField, The apitools field to generate the flag for.

    Returns:
      str, The name of the flag to generate.
    """
    name = prefix + field.name
    if field.variant == messages.Variant.MESSAGE:
      if (name == method.request_field and
          name.lower().endswith('request')):
        name = 'request'
    return name

  def _MessageFieldFlags(self, prefix, message):
    """Get the arguments to add to the parser that appear in the method body.

    Args:
      prefix: str, A string to prepend to the name of the flag. This is used
        for flags representing fields of a submessage.
      message: The apitools message to generate the flags for.

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    args = {}
    field_helps = self._FieldHelpDocs(message)
    for field in message.all_fields():
      name = ArgumentGenerator.FlagNameForField(self.method, prefix, field)
      if field.variant == messages.Variant.MESSAGE:
        field_help = field_helps.get(field.name, None)
        group = base.ArgumentGroup(
            name, description=(name + ': ' + field_help) if field_help else '')
        for arg in self._MessageFieldFlags(name + '.', field.type).values():
          group.AddArgument(arg)
        args[name] = group
      else:
        args[name] = self._FlagForMessageField(name, field, field_helps)
    return {k: v for k, v in args.iteritems() if v is not None}

  def _FlagForMessageField(self, name, field, field_helps):
    """Gets a flag for a single field in a message.

    Args:
      name: The name of the field.
      field: The apitools field object.
      field_helps: {str: str}, A mapping of field name to help text.

    Returns:
      {str: str}, A mapping of field name to help text.
    """
    help_text = field_helps.get(field.name, None)
    if self._IsOutputField(help_text):
      return None
    variant = field.variant
    t = ArgumentGenerator.TYPES.get(variant, None)
    choices = None
    if variant == messages.Variant.ENUM:
      choices = field.type.names()
    return base.Argument(
        # TODO(b/38000796): Consider not using camel case for flags.
        '--' + name,
        metavar=resource_property.ConvertToAngrySnakeCase(field.name),
        category='MESSAGE',
        action='store',
        type=t,
        choices=choices,
        help=help_text,
    )

  def _FieldHelpDocs(self, message):
    """Gets the help text for the fields in the request message.

    Args:
      message: The apitools message.

    Returns:
      {str: str}, A mapping of field name to help text.
    """
    field_helps = {}
    current_field = None

    match = re.search(r'^\s+Fields:.*$', message.__doc__, re.MULTILINE)
    if not match:
      # Couldn't find any fields at all.
      return field_helps

    for line in message.__doc__[match.end():].splitlines():
      match = re.match(r'^\s+(\w+): (.*)$', line)
      if match:
        # This line is the start of a new field.
        current_field = match.group(1)
        field_helps[current_field] = match.group(2).strip()
      elif current_field:
        # Append additional text to the in progress field.
        current_text = field_helps.get(current_field, '')
        field_helps[current_field] = current_text + ' ' + line.strip()

    return field_helps

  def _IsOutputField(self, help_text):
    """Determines if the given field is output only based on help text."""
    return help_text and help_text.startswith('[Output Only]')
