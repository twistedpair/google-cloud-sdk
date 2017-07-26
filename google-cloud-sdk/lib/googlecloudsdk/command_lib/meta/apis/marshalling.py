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
from googlecloudsdk.core import resources
from googlecloudsdk.core.resource import resource_property


_TYPES = {
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


_RESOURCE_ARG_NAME = 'resource'


class ArgumentGenerator(object):
  """Class to generate and parse argparse flags from apitools message fields."""

  def __init__(self, method, raw=False):
    """Creates a new Argument Generator.

    Args:
      method: APIMethod, The method to generate arguments for.
      raw: bool, True to do no special processing of arguments for list
        commands. If False, typical List command flags will be added in and the
        equivalent API fields will be ignored.
    """
    self.method = method
    self.raw = raw
    self.ignored_fields = set()
    if not raw:
      if self.method.IsList():
        # Ignore the APIs filter flag in favor of ours.
        self.ignored_fields.add('filter')
        if self.method.IsPageableList():
          # Don't expose this directly, it will be used as part listing.
          self.ignored_fields.add('pageToken')
          batch_page_size_field = self.method.BatchPageSizeField()
          if batch_page_size_field:
            self.ignored_fields.add(batch_page_size_field)

  def GenerateArgs(self):
    """Generates all the CLI arguments required to call this method.

    Returns:
      {str, calliope.base.Action}, A map of field name to the argument.
    """
    args = {}
    args.update(self._GenerateListMethodFlags())
    args.update(self._GenerateMessageFieldsFlags(
        '', self.method.GetRequestType()))
    args.update(self._GenerateResourceFlags())
    args.update(self._GenerateResourceArg())
    return args

  def CreateRequest(self, namespace):
    """Generates the request object for the method call from the parsed args.

    Args:
      namespace: The argparse namespace.

    Returns:
      The apitools message to be send to the method.
    """
    request_type = self.method.GetRequestType()
    # Recursively create the message and sub-messages.
    fields = self._ParseMessageFieldsFlags(namespace, '', request_type)

    # For each actual method path field, add the attribute to the request.
    ref = self._ParseResourceArg(namespace)
    if ref:
      relative_name = ref.RelativeName()
      fields.update(
          {f: getattr(ref, f, relative_name) for f in self.method.params})
    return request_type(**fields)

  def _GenerateListMethodFlags(self):
    """Generates all the CLI flags for a List command.

    Returns:
      {str, calliope.base.Action}, A map of field name to the argument.
    """
    flags = {}
    if not self.raw and self.method.IsList():
      flags[base.FILTER_FLAG.name] = base.FILTER_FLAG
      flags[base.SORT_BY_FLAG.name] = base.SORT_BY_FLAG
      if self.method.IsPageableList() and self.method.ListItemField():
        # We can use YieldFromList() with a limit.
        flags[base.LIMIT_FLAG.name] = base.LIMIT_FLAG
        if self.method.BatchPageSizeField():
          # API supports page size.
          flags[base.PAGE_SIZE_FLAG.name] = base.PAGE_SIZE_FLAG
    return flags

  def Limit(self, namespace):
    """Gets the value of the limit flag (if present)."""
    if (not self.raw and
        self.method.IsPageableList() and
        self.method.ListItemField()):
      return getattr(namespace, 'limit')

  def PageSize(self, namespace):
    """Gets the value of the page size flag (if present)."""
    if (not self.raw and
        self.method.IsPageableList() and
        self.method.ListItemField() and
        self.method.BatchPageSizeField()):
      return getattr(namespace, 'page_size')

  def _GenerateResourceArg(self):
    """Gets the positional argument that represents the resource.

    Returns:
      {str, calliope.base.Argument}, The argument.
    """
    if not self.method.RequestCollection():
      log.warning('Not generating resource arg')
      return {}
    return {
        'resource': base.Argument(
            _RESOURCE_ARG_NAME,
            nargs='?',
            help='The GRI for the resource being operated on.')}

  def _ParseResourceArg(self, namespace):
    """Gets the resource ref for the resource specified as the positional arg.

    Args:
      namespace: The argparse namespace.

    Returns:
      The parsed resource ref or None if no resource arg was generated for this
      method.
    """
    not_generated = object()
    r = getattr(namespace, _RESOURCE_ARG_NAME, not_generated)
    if r is not_generated:
      return None
    return resources.REGISTRY.Parse(
        r,
        collection=self.method.RequestCollection().full_name,
        params=self._ParseResourceFlags(namespace))

  def _GenerateResourceFlags(self):
    """Get the flags to add to the parser that appear in the method path.

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    message = self.method.GetRequestType()
    field_helps = _FieldHelpDocs(message)
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

  def _ParseResourceFlags(self, namespace):
    """Parses the resource path flags and inserts defaults.

    Args:
      namespace: The argparse namespace.

    Returns:
      {str: value}, A mapping of field name to parsed value suitable for use
       by the resource parser.
    """
    resource_flags = {f: getattr(namespace, f)
                      for f in self.method.ResourceFieldNames()}
    params = self.method.GetDefaultParams()
    params.update({f: v for f, v in resource_flags.iteritems()
                   if v is not None})
    return params

  def _GenerateMessageFieldsFlags(self, prefix, message):
    """Get the arguments to add to the parser that appear in the method body.

    Args:
      prefix: str, A string to prepend to the name of the flag. This is used
        for flags representing fields of a submessage.
      message: The apitools message to generate the flags for.

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    args = {}
    field_helps = _FieldHelpDocs(message)
    for field in message.all_fields():
      name = self._FlagNameForField(prefix, field)
      if name in self.ignored_fields:
        continue
      if field.variant == messages.Variant.MESSAGE:
        field_help = field_helps.get(field.name, None)
        group = base.ArgumentGroup(
            name, description=(name + ': ' + field_help) if field_help else '')
        for arg in self._GenerateMessageFieldsFlags(
            name + '.', field.type).values():
          group.AddArgument(arg)
        args[name] = group
      else:
        args[name] = self._GenerateMessageFieldFlag(name, field, field_helps)
    return {k: v for k, v in args.iteritems() if v is not None}

  def _ParseMessageFieldsFlags(self, namespace, prefix, message):
    """Recursively generates the message and any sub-messages.

    Args:
      namespace: The argparse namespace.
      prefix: str, The flag prefix for the sub-message being generated.
      message: The apitools class for the message.

    Returns:
      The instantiated apitools Message with all fields filled in from flags.
    """
    kwargs = {}
    for field in message.all_fields():
      name = self._FlagNameForField(prefix, field)
      # Field is a sub-message, recursively generate it.
      if field.variant == messages.Variant.MESSAGE:
        sub_kwargs = self._ParseMessageFieldsFlags(
            namespace, name + '.', field.type)
        if sub_kwargs:
          # Only construct the sub-message if we have something to put in it.
          value = field.type(**sub_kwargs)
          # TODO(b/38000796): Handle repeated fields correctly.
          kwargs[field.name] = value if not field.repeated else [value]
      # Field is a scalar, just get the value.
      else:
        value = getattr(namespace, name, None)
        if value is not None:
          # TODO(b/38000796): Handle repeated fields correctly.
          kwargs[field.name] = value if not field.repeated else [value]
    return kwargs

  def _FlagNameForField(self, prefix, field):
    """Compute the flag name to generate for the given message field.

    Args:
      prefix: str, A prefix to put on the flag (when generating flags for
        sub-messages).
      field: MessageField, The apitools field to generate the flag for.

    Returns:
      str, The name of the flag to generate.
    """
    name = prefix + field.name
    if field.variant == messages.Variant.MESSAGE:
      if (name == self.method.request_field and
          name.lower().endswith('request')):
        name = 'request'
    return name

  def _GenerateMessageFieldFlag(self, name, field, field_helps):
    """Gets a flag for a single field in a message.

    Args:
      name: The name of the field.
      field: The apitools field object.
      field_helps: {str: str}, A mapping of field name to help text.

    Returns:
      {str: str}, A mapping of field name to help text.
    """
    help_text = field_helps.get(field.name, None)
    if _IsOutputField(help_text):
      return None
    variant = field.variant
    t = _TYPES.get(variant, None)
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


def _FieldHelpDocs(message):
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


def _IsOutputField(help_text):
  """Determines if the given field is output only based on help text."""
  return help_text and help_text.startswith('[Output Only]')
