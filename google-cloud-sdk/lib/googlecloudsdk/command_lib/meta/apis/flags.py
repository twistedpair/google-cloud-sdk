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

from apitools.base.protorpclite import messages

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as c_exc
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.command_lib.meta.apis import marshalling
from googlecloudsdk.command_lib.meta.apis import registry
from googlecloudsdk.core import resources


def APICompleter(**_):
  return [a.name for a in registry.GetAllAPIs()]


def CollectionCompleter(**_):
  return [c.full_name for c in registry.GetAPICollections()]


def MethodCompleter(prefix, parsed_args, **_):
  del prefix
  collection = getattr(parsed_args, 'collection', None)
  if not collection:
    return []
  return [m.name for m in registry.GetMethods(collection)]


API_VERSION_FLAG = base.Argument(
    '--api-version',
    help='The version of the given API to use. If not provided, the default '
         'version of the API will be used.')

COLLECTION_FLAG = base.Argument(
    '--collection',
    required=True,
    completer=CollectionCompleter,
    help='The name of the collection to specify the method for.')


class MethodDynamicPositionalAction(parser_extensions.DynamicPositionalAction):
  """A DynamicPositionalAction that adds flags for a given method to the parser.

  Based on the value given for method, it looks up the valid fields for that
  method call and adds those flags to the parser.
  """

  def __init__(self, *args, **kwargs):
    # Pop the dest so that the superclass doesn't try to automatically save the
    # value of the arg to the namespace. We explicitly save the method ref
    # instead.
    self._dest = kwargs.pop('dest')
    super(MethodDynamicPositionalAction, self).__init__(*args, **kwargs)

  def GenerateArgs(self, namespace, method_name):
    # Get the collection from the existing parsed args.
    full_collection_name = getattr(namespace, 'collection', None)
    api_version = getattr(namespace, 'api_version', None)
    if not full_collection_name:
      raise c_exc.RequiredArgumentException(
          '--collection',
          'The collection name must be specified before the API method.')

    # Look up the method and get all the args for it.
    # TODO(b/38000796): It's possible that api_version hasn't been parsed yet
    # so we are generating the wrong args.
    method = registry.GetMethod(full_collection_name, method_name,
                                api_version=api_version)
    arg_generator = marshalling.ArgumentGenerator(method)
    args = arg_generator.MessageFieldFlags()
    args.update(arg_generator.ResourceFlags())
    args.update(arg_generator.ResourceArg())

    method_ref = MethodRef(namespace, method)
    setattr(namespace, self._dest, method_ref)

    return args

  def Completions(self, prefix, parsed_args, **kwargs):
    return MethodCompleter(prefix, parsed_args, **kwargs)


class MethodRef(object):
  """Encapsulates a method specified on the command line with all its flags.

  Whereas the ArgumentGenerator generates all the flags that correspond to a
  method, this reference is used to encapsulate the parsing of all of it. A user
  doesn't need to be aware of which flags were added and manually extract them.
  This knows which flags exist and what method fields they correspond to.
  """

  def __init__(self, namespace, method):
    """Creates the MethodRef.

    Args:
      namespace: The argparse namespace that holds the parsed args.
      method: APIMethod, The method.
    """
    self.namespace = namespace
    self.method = method

  def Call(self):
    """Execute the method.

    Returns:
      The result of the method call.
    """
    # TODO(b/38000796): Should have special handling for list requests to do
    # paging automatically.
    return self.method.Call(self._GenerateRequest())

  def _GenerateRequest(self):
    """Generates the request object for the method call."""
    request_type = self.method.GetRequestType()
    # Recursively create the message and sub-messages.
    fields = self._CreateMessage('', request_type)

    # For each actual method path field, add the attribute to the request.
    ref = self._GetResourceRef()
    if ref:
      relative_name = ref.RelativeName()
      fields.update(
          {f: getattr(ref, f, relative_name) for f in self.method.params})
    return request_type(**fields)

  def _CreateMessage(self, prefix, message):
    """Recursively generates the message and any sub-messages.

    Args:
      prefix: str, The flag prefix for the sub-message being generated.
      message: The apitools class for the message.

    Returns:
      The instantiated apitools Message with all fields filled in from flags.
    """
    kwargs = {}
    for field in message.all_fields():
      name = marshalling.ArgumentGenerator.FlagNameForField(self.method, prefix,
                                                            field)
      # Field is a sub-message, recursively generate it.
      if field.variant == messages.Variant.MESSAGE:
        sub_kwargs = self._CreateMessage(name + '.', field.type)
        if sub_kwargs:
          # Only construct the sub-message if we have something to put in it.
          value = field.type(**sub_kwargs)
          # TODO(b/38000796): Handle repeated fields correctly.
          kwargs[field.name] = value if not field.repeated else [value]
      # Field is a scalar, just get the value.
      else:
        value = getattr(self.namespace, name, None)
        if value is not None:
          # TODO(b/38000796): Handle repeated fields correctly.
          kwargs[field.name] = value if not field.repeated else [value]
    return kwargs

  def _GetResourceRef(self):
    """Gets the resource ref for the resource specified as the positional arg.

    Returns:
      The parsed resource ref or None if no resource arg was generated for this
      method.
    """
    r = getattr(self.namespace, 'resource')
    if r is None:
      return None
    return resources.REGISTRY.Parse(
        r,
        collection=self.method.RequestCollection().full_name,
        params=self._GetResourceParams())

  def _GetResourceParams(self):
    """Gets the defaults for parsing the resource ref."""
    params = self.method.GetDefaultParams()
    resource_flags = {f: getattr(self.namespace, f)
                      for f in self.method.ResourceFieldNames()}
    params.update({f: v for f, v in resource_flags.iteritems()
                   if v is not None})
    return params
