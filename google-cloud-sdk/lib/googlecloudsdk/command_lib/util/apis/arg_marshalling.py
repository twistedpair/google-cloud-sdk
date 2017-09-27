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

"""Classes that generate and parse arguments for apitools messages."""

from apitools.base.protorpclite import messages
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.apis import yaml_command_schema
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.resource import resource_property


class Error(Exception):
  """Base class for this module's exceptions."""
  pass


class MissingResourceArg(Error):
  """Exception for when there is no arg information for an API field."""

  def __init__(self, fields):
    super(MissingResourceArg, self).__init__(
        'You must provide argument information for API fields: [{}]'
        .format(', '.join(fields)))


class ExtraResourceArg(Error):
  """Exception for when there is no arg information for an API field."""

  def __init__(self, fields):
    super(ExtraResourceArg, self).__init__(
        'You provided argument information for resource API fields that do not '
        'exist: [{}]'
        .format(', '.join(fields)))


class DeclarativeArgumentGenerator(object):
  """An argument generator that operates off a declarative configuration.

  When using this generator, you must provide attributes for the arguments that
  should be generated. All resource arguments must be provided and arguments
  will only be generated for API fields for which attributes were provided.
  """
  IGNORED_FIELDS = {
      'project': 'project',
      'projectId': 'project',
      'projectsId': 'project',
  }
  DEFAULT_PARAMS = {'project': properties.VALUES.core.project.Get}

  def __init__(self, method, arg_info, resource_arg_info):
    """Creates a new Argument Generator.

    Args:
      method: APIMethod, The method to generate arguments for.
      arg_info: [yaml_command_schema.Argument], Information about
        request fields and how to map them into arguments.
      resource_arg_info: [yaml_command_schema.Argument], Information about
        request parameter fields that will be made into a resource argument.
    """
    self.method = method
    self.arg_info = arg_info
    self.resource_arg_info = resource_arg_info

  @property
  def resource_arg_name(self):
    """Gets the type of the resource being operated on.

    This is based off the name of the final positional parameter in the API
    request.

    Returns:
      The type of resource being operated on (i.e. instance, registry, disk,
      etc).
    """
    field_names = self.method.ResourceFieldNames()
    if not field_names:
      return None
    anchor_field = field_names[-1]
    for attributes in self.resource_arg_info:
      if attributes.api_field == anchor_field:
        return attributes.arg_name
    return None

  def GenerateArgs(self):
    """Generates all the CLI arguments required to call this method.

    Returns:
      {str, calliope.base.Action}, A map of field name to the argument.
    """
    args = {}
    args.update(self._GenerateArguments())
    args.update(self._GenerateResourceArg())
    return args

  def CreateRequest(self, namespace, static_fields=None,
                    resource_method_params=None):
    """Generates the request object for the method call from the parsed args.

    Args:
      namespace: The argparse namespace.
      static_fields: {str, value}, A mapping of API field name to value to
        insert into the message. This is a convenient way to insert extra data
        while the request is being constructed for fields that don't have
        corresponding arguments.
      resource_method_params: {str: str}, A mapping of API method parameter name
        to resource ref attribute name when the API method uses non-standard
        names.

    Returns:
      The apitools message to be send to the method.
    """
    static_fields = static_fields or {}
    resource_method_params = resource_method_params or {}
    message_type = self.method.GetRequestType()
    message = message_type()

    # Insert static fields into message.
    for field_path, value in static_fields.iteritems():
      field = arg_utils.GetFieldFromMessage(message_type, field_path)
      arg_utils.SetFieldInMessage(
          message, field_path, arg_utils.ConvertValue(field, value))

    # Parse api Fields into message.
    self._ParseArguments(message, namespace)
    # For each method path field, get the value from the resource reference.
    ref = self._ParseResourceArg(namespace)
    if ref:
      relative_name = ref.RelativeName()
      for p in self.method.params:
        value = getattr(ref, resource_method_params.get(p, p), relative_name)
        arg_utils.SetFieldInMessage(message, p, value)
    return message

  def GetRequestResourceRef(self, namespace):
    """Gets a resource reference for the resource being operated on.

    Args:
      namespace: The argparse namespace.

    Returns:
      resources.Resource, The parsed resource reference.
    """
    return self._ParseResourceArg(namespace)

  def GetResponseResourceRef(self, id_value, namespace):
    """Gets a resource reference for a resource returned by a list call.

    It parses the namespace to find a reference to the parent collection and
    then creates a reference to the child resource with the given id_value.

    Args:
      id_value: str, The id of the child resource that was returned.
      namespace: The argparse namespace.

    Returns:
      resources.Resource, The parsed resource reference.
    """
    parent_ref = self.GetRequestResourceRef(namespace)
    return resources.REGISTRY.Parse(
        id_value,
        collection=self.method.collection.full_name,
        params=parent_ref.AsDict())

  def Limit(self, namespace):
    """Gets the value of the limit flag (if present)."""
    return arg_utils.Limit(self.method, namespace)

  def PageSize(self, namespace):
    """Gets the value of the page size flag (if present)."""
    return arg_utils.PageSize(self.method, namespace)

  def _GenerateArguments(self):
    """Generates the arguments for the API fields of this method."""
    message = self.method.GetRequestType()
    args = self._CreateGroups()

    for attributes in self.arg_info:
      field_path = attributes.api_field
      field = arg_utils.GetFieldFromMessage(message, field_path)
      arg = arg_utils.GenerateFlag(field, attributes)
      if attributes.group:
        args[attributes.group.group_id].AddArgument(arg)
      else:
        args[arg.name] = arg
    return args

  def _CreateGroups(self):
    """Generate calliope argument groups for every registered mutex group."""
    groups = {
        a.group.group_id: base.ArgumentGroup(
            a.group.group_id, required=a.required)
        for a in self.arg_info if a.group}
    return groups

  def _CheckRegisteredResourceArgs(self):
    """Make sure the registered args match required args for the resource."""
    actual_field_names = set(self.method.ResourceFieldNames())
    registered_field_names = {a.api_field for a in self.resource_arg_info}
    extra = registered_field_names - actual_field_names
    if extra:
      raise ExtraResourceArg(extra)
    missing = actual_field_names - registered_field_names - set(
        DeclarativeArgumentGenerator.IGNORED_FIELDS.keys())
    if missing:
      raise MissingResourceArg(missing)

  def _GenerateResourceArg(self):
    """Generates the flags to add to the parser that appear in the method path.

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    field_names = self.method.ResourceFieldNames()
    if not field_names:
      return {}
    self._CheckRegisteredResourceArgs()

    args = {}
    anchor_field = field_names[-1]

    for attributes in self.resource_arg_info:
      is_anchor = attributes.api_field == anchor_field
      # If the request params match, this means this method takes the same
      # params as the get method and so the last item should be positional.
      # If it doesn't (like for a list command) then we are omitting the last
      # arg so all other should be flags and none should be made positional.
      is_positional = is_anchor and self.method.request_params_match_resource

      arg_name = attributes.arg_name
      arg = base.Argument(
          arg_name if is_positional else '--' + arg_name,
          metavar=resource_property.ConvertToAngrySnakeCase(
              attributes.arg_name),
          completer=attributes.completer,
          help=attributes.help_text)
      if is_anchor and not is_positional:
        arg.kwargs['required'] = True
      args[arg.name] = arg
    return args

  def _ParseArguments(self, message, namespace):
    """Parse all the arguments from the namespace into the message object.

    Args:
      message: A constructed apitools message object to inject the value into.
      namespace: The argparse namespace.
    """
    message_type = self.method.GetRequestType()
    for attributes in self.arg_info:
      value = arg_utils.GetFromNamespace(namespace, attributes.arg_name)
      if value is None:
        continue
      field = arg_utils.GetFieldFromMessage(message_type, attributes.api_field)
      value = arg_utils.ConvertValue(field, value, attributes)
      arg_utils.SetFieldInMessage(message, attributes.api_field, value)

  def _ParseResourceArg(self, namespace):
    """Gets the resource ref for the resource specified as the positional arg.

    Args:
      namespace: The argparse namespace.

    Returns:
      The parsed resource ref or None if no resource arg was generated for this
      method.
    """
    field_names = self.method.ResourceFieldNames()
    if not field_names:
      return
    field_mapping = dict(DeclarativeArgumentGenerator.IGNORED_FIELDS)
    field_mapping.update(
        {a.api_field: a.arg_name for a in self.resource_arg_info})

    anchor_field = field_names[-1]
    resource = arg_utils.GetFromNamespace(namespace,
                                          field_mapping[anchor_field])
    params = {}
    for field in field_names[:-1]:
      arg_name = field_mapping[field]
      value = arg_utils.GetFromNamespace(namespace, arg_name)
      params[field] = (value or
                       DeclarativeArgumentGenerator.DEFAULT_PARAMS.get(
                           arg_name, lambda: None)())
    return resources.REGISTRY.Parse(
        resource,
        collection=self.method.RequestCollection().full_name,
        params=params)


class AutoArgumentGenerator(object):
  """An argument generator to generate arguments for all fields in a message.

  When using this generator, you don't provide any manual configuration for
  arguments, it is all done automatically based on the request messages.

  There are two modes for this generator. In 'raw' mode, no modifications are
  done at all to the generated fields. In normal mode, certain list fields are
  not generated and instead our global list flags are used (and orchestrate
  the proper API fields automatically). In both cases, we generate additional
  resource arguments for path parameters.
  """
  FLAT_RESOURCE_ARG_NAME = 'resource'
  IGNORABLE_LIST_FIELDS = {'filter', 'pageToken', 'orderBy'}
  DEFAULT_PARAMS = {'project': properties.VALUES.core.project.Get,
                    'projectId': properties.VALUES.core.project.Get,
                    'projectsId': properties.VALUES.core.project.Get,}

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
    self.is_atomic = self.method.detailed_params != self.method.params

    self.ignored_fields = set()
    if not raw and self.method.IsPageableList():
      self.ignored_fields |= AutoArgumentGenerator.IGNORABLE_LIST_FIELDS
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
    args.update(self._GenerateArguments('', self.method.GetRequestType()))
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
    fields = self._ParseArguments(namespace, '', request_type)

    # For each actual method path field, add the attribute to the request.
    ref = self._ParseResourceArg(namespace)
    if ref:
      relative_name = ref.RelativeName()
      fields.update({f: getattr(ref, f, relative_name)
                     for f in self.method.params})
    return request_type(**fields)

  def Limit(self, namespace):
    """Gets the value of the limit flag (if present)."""
    if not self.raw:
      return arg_utils.Limit(self.method, namespace)

  def PageSize(self, namespace):
    """Gets the value of the page size flag (if present)."""
    if not self.raw:
      return arg_utils.PageSize(self.method, namespace)

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

  def _GenerateArguments(self, prefix, message):
    """Gets the arguments to add to the parser that appear in the method body.

    Args:
      prefix: str, A string to prepend to the name of the flag. This is used
        for flags representing fields of a submessage.
      message: The apitools message to generate the flags for.

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    args = {}
    field_helps = arg_utils.FieldHelpDocs(message)
    for field in message.all_fields():
      field_help = field_helps.get(field.name, None)
      name = self._GetArgName(field.name, field_help)
      if not name:
        continue
      name = prefix + name
      if field.variant == messages.Variant.MESSAGE:
        sub_args = self._GenerateArguments(name + '.', field.type)
        if sub_args:
          help_text = (name + ': ' + field_help) if field_help else ''
          group = base.ArgumentGroup(name, description=help_text)
          args[name] = group
          for arg in sub_args.values():
            group.AddArgument(arg)
      else:
        attributes = yaml_command_schema.Argument(name, name, field_help)
        arg = arg_utils.GenerateFlag(field, attributes, fix_bools=False,
                                     category='MESSAGE')
        args[arg.name] = arg
    return args

  def _GenerateResourceArg(self):
    """Gets the flags to add to the parser that appear in the method path.

    Returns:
      {str, calliope.base.Argument}, A map of field name to argument.
    """
    field_names = self.method.ResourceFieldNames()
    if not field_names:
      return {}
    field_helps = arg_utils.FieldHelpDocs(self.method.GetRequestType())
    default_help = 'For substitution into: ' + self.method.detailed_path

    args = {}
    # Make a dedicated positional in addition to the flags for each part of
    # the URI path.
    args[AutoArgumentGenerator.FLAT_RESOURCE_ARG_NAME] = base.Argument(
        AutoArgumentGenerator.FLAT_RESOURCE_ARG_NAME,
        nargs='?',
        help='The GRI for the resource being operated on.')

    for field in field_names:
      arg = base.Argument(
          '--' + field,
          metavar=resource_property.ConvertToAngrySnakeCase(field),
          category='RESOURCE',
          help=field_helps.get(field, default_help))
      args[arg.name] = arg
    return args

  def _ParseArguments(self, namespace, prefix, message):
    """Recursively generates the request message and any sub-messages.

    Args:
      namespace: The argparse namespace containing the all the parsed arguments.
      prefix: str, The flag prefix for the sub-message being generated.
      message: The apitools class for the message.

    Returns:
      The instantiated apitools Message with all fields filled in from flags.
    """
    kwargs = {}
    for field in message.all_fields():
      arg_name = self._GetArgName(field.name)
      if not arg_name:
        continue
      arg_name = prefix + arg_name
      # Field is a sub-message, recursively generate it.
      if field.variant == messages.Variant.MESSAGE:
        sub_kwargs = self._ParseArguments(namespace, arg_name + '.', field.type)
        if sub_kwargs:
          # Only construct the sub-message if we have something to put in it.
          value = field.type(**sub_kwargs)
          # TODO(b/38000796): Handle repeated fields correctly.
          kwargs[field.name] = value if not field.repeated else [value]
      # Field is a scalar, just get the value.
      else:
        value = arg_utils.GetFromNamespace(namespace, arg_name)
        if value is not None:
          kwargs[field.name] = arg_utils.ConvertValue(field, value)
    return kwargs

  def _ParseResourceArg(self, namespace):
    """Gets the resource ref for the resource specified as the positional arg.

    Args:
      namespace: The argparse namespace.

    Returns:
      The parsed resource ref or None if no resource arg was generated for this
      method.
    """
    field_names = self.method.ResourceFieldNames()
    if not field_names:
      return
    r = getattr(namespace, AutoArgumentGenerator.FLAT_RESOURCE_ARG_NAME)

    params = {}
    defaults = {}
    for f in field_names:
      value = getattr(namespace, f)
      if value:
        params[f] = value
      else:
        default = AutoArgumentGenerator.DEFAULT_PARAMS.get(f, lambda: None)()
        if default:
          defaults[f] = default

    if not r and not params and len(defaults) < len(field_names):
      # No values were explicitly given and there are not enough defaults for
      # the parse to work.
      return None

    defaults.update(params)
    return resources.REGISTRY.Parse(
        r, collection=self.method.RequestCollection().full_name,
        params=defaults)

  def _GetArgName(self, field_name, field_help=None):
    """Gets the name of the argument to generate for the field.

    Args:
      field_name: str, The name of the field.
      field_help: str, The help for the field in the API docs.

    Returns:
      str, The name of the argument to generate, or None if this field is output
      only or should be ignored.
    """
    if field_help and arg_utils.IsOutputField(field_help):
      return None
    if field_name in self.ignored_fields:
      return None
    if (field_name == self.method.request_field and
        field_name.lower().endswith('request')):
      return 'request'
    return field_name



