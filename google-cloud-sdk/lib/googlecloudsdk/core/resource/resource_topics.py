# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Common resource topic text."""

import textwrap

from googlecloudsdk.core.resource import resource_printer
from googlecloudsdk.core.resource import resource_registry
from googlecloudsdk.core.resource import resource_transform


def ResourceDescription(name):
  """Generates resource help DESCRIPTION help text for name.

  This puts common text for the key, formats and projections topics in one
  place.

  Args:
    name: One of ['filter', 'format', 'key', 'projection'].

  Raises:
    ValueError: If name is not one of the expected topic names.

  Returns:
    A detailed_help DESCRIPTION markdown string.
  """
  description = """\
  Most *gcloud* commands return a list of resources on success. By default they
  are pretty-printed on the standard output. The
  *--format=*_NAME_[_ATTRIBUTES_]*(*_PROJECTION_*)* flag changes the default
  output:

  _NAME_:: The format name.

  _ATTRIBUTES_:: Format specific attributes. {see_format}

  _PROJECTION_:: A list of resource keys that selects the data listed. \
{see_projection}

  _resource keys_:: Keys are names for resource resource items. {see_key}

  Most *gcloud* *list* commands have a *--filter=*_EXPRESSION_ flag that
  selects resources to be listed. {see_filter}
  """
  # topic <name> => gcloud topic <command>
  topics = {
      'filter': 'filters',
      'format': 'formats',
      'key': 'resource-keys',
      'projection': 'projections',
  }
  if name not in topics:
    raise ValueError('Expected one of [{topics}], got [{name}].'.format(
        topics=','.join(sorted(topics)), name=name))
  see = {}
  for topic, command in topics.iteritems():
    if topic == name:
      see[topic] = 'Resource {topic}s are described in detail below.'.format(
          topic=topic)
    else:
      see[topic] = 'For details run $ gcloud topic {command}.'.format(
          command=command)
  return textwrap.dedent(description).format(see_filter=see['filter'],
                                             see_format=see['format'],
                                             see_key=see['key'],
                                             see_projection=see['projection'])


_DOC_MAIN, _DOC_ARGS, _DOC_ATTRIBUTES, _DOC_EXAMPLE, _DOC_SKIP = range(5)


def _ParseFormatDocString(printer):
  """Parses the doc string for printer.

  Args:
    printer: The doc string will be parsed from this resource format printer.

  Returns:
    A (description, attributes) tuple:
      description - The format description.
      attributes - A list of (name, description) tuples, one tuple for each
        format-specific attribute.

  Example resource printer docstring parsed by this method:
    '''This line is skipped. Printer attributes and Example sections optional.

    These lines describe the format.
    Another description line.

    Printer attributes:
      attribute-1-name: The description for attribute-1-name.
      attribute-N-name: The description for attribute-N-name.

    Example:
      One or more example lines for the 'For example:' section.
    '''
  """
  descriptions = []
  attributes = []
  example = []
  if not printer.__doc__:
    return '', '', ''
  _, _, doc = printer.__doc__.partition('\n')
  collect = _DOC_MAIN
  attribute = None
  attribute_description = []
  for line in textwrap.dedent(doc).split('\n'):
    if not line.startswith(' ') and line.endswith(':'):
      # The start of a new section.
      if attribute:
        # The current attribute description is done.
        attributes.append((attribute, ' '.join(attribute_description)))
        attribute = None
      if line == 'Printer attributes:':
        # Now collecting Printer attributes: section lines.
        collect = _DOC_ATTRIBUTES
      elif line == 'Example:':
        # Now collecting Example: section lines.
        collect = _DOC_EXAMPLE
      else:
        collect = _DOC_SKIP
      continue

    if not line or collect == _DOC_SKIP:
      # Only interested in the description body and the Printer args: section.
      continue
    elif collect == _DOC_MAIN:
      # The main description line.
      descriptions.append(line.strip())
    elif line.startswith('    '):
      if collect == _DOC_ATTRIBUTES:
        # An attribute description line.
        attribute_description.append(line.strip())
    elif collect == _DOC_EXAMPLE and line.startswith('  '):
      # An example section line.
      example.append(line.strip())
    else:
      # The current attribute description is done.
      if attribute:
        attributes.append((attribute, ' '.join(attribute_description)))
      # A new attribute description.
      attribute, _, text = line.partition(':')
      attribute = attribute.strip()
      attribute = attribute.lstrip('*')
      attribute_description = [text.strip()]
  if attribute:
    attributes.append((attribute, ' '.join(attribute_description)))
  return ' '.join(descriptions), attributes, example


def FormatRegistryDescriptions():
  """Returns help markdown for all registered resource printer formats."""
  # Generate the printer markdown.
  descriptions = ['The formats and format specific attributes are:']
  for name, printer in sorted(resource_printer.GetFormatRegistry().iteritems()):
    description, attributes, example = _ParseFormatDocString(printer)
    descriptions.append('\n*{name}*::\n{description}'.format(
        name=name, description=description))
    if attributes:
      descriptions.append('+\nThe format attributes are:\n')
      for attribute, description in attributes:
        descriptions.append('*{attribute}*:::\n{description}'.format(
            attribute=attribute, description=description))
    if example:
      descriptions.append('+\nFor example`:`:::\n')
      descriptions.append(' '.join(example))

  # Generate the "attributes for all printers" markdown.
  description, attributes, example = _ParseFormatDocString(
      resource_printer.PrinterAttributes)
  if attributes:
    descriptions.append('\n{description}:\n'.format(
        description=description[:-1]))
    for attribute, description in attributes:
      descriptions.append('*{attribute}*:::\n{description}'.format(
          attribute=attribute, description=description))
  if example:
    descriptions.append('+\nFor example`:`:::\n')
    descriptions.append(' '.join(example))
  descriptions.append('')
  return '\n'.join(descriptions)


def _StripUnusedNotation(string):
  """Returns string with Pythonic unused notation stripped."""
  if string.startswith('_'):
    return string.lstrip('_')
  unused = 'unused_'
  if string.startswith(unused):
    return string[len(unused):]
  return string


def _ParseTransformDocString(func):
  """Parses the doc string for func.

  Args:
    func: The doc string will be parsed from this function.

  Returns:
    A (description, prototype, args) tuple:
      description - The function description.
      prototype - The function prototype string.
      args - A list of (name, description) tuples, one tuple for each arg.

  Example transform function docstring parsed by this method:
    '''Transform description. Example sections optional.

    These lines are skipped.
    Another skipped line.

    Args:
      r: The resource arg is always sepcified but omitted from the docs.
      arg-2-name[=default-2]: The description for arg-2-name.
      arg-N-name[=default-N]: The description for arg-N-name.
      kwargs: Omitted from the description.

    Example:
      One or more example lines for the 'For example:' section.
    '''
  """
  hidden_args = ('kwargs', 'projection', 'r')
  if not func.__doc__:
    return '', '', '', ''
  description, _, doc = func.__doc__.partition('\n')
  collect = _DOC_MAIN
  arg = None
  descriptions = [description]
  example = []
  args = []
  arg_description = []
  for line in textwrap.dedent(doc).split('\n'):
    if line == 'Args:':
      # Now collecting Args: section lines.
      collect = _DOC_ARGS
    elif line == 'Example:':
      # Now collecting Example: section lines.
      collect = _DOC_EXAMPLE
    elif not line or collect == _DOC_SKIP:
      # Only interested in the main description and the Args: section.
      continue
    elif collect == _DOC_MAIN:
      # The main description line.
      descriptions.append(line.strip())
    elif line.startswith('    '):
      # An arg description line.
      arg_description.append(line.strip())
    elif collect == _DOC_EXAMPLE and line.startswith('  '):
      # An example description line.
      example.append(line.strip())
    else:
      # The current arg description is done.
      if arg:
        arg = _StripUnusedNotation(arg)
      if arg and arg not in hidden_args:
        args.append((arg, ' '.join(arg_description)))
      if not line.startswith(' ') and line.endswith(':'):
        # The start of a new section.
        collect = _DOC_SKIP
        continue
      # A new arg description.
      arg, _, text = line.partition(':')
      arg = arg.strip()
      arg = arg.lstrip('*')
      arg_description = [text.strip()]

  # Collect the formal arg list with defaults for the function prototype.
  import inspect  # pylint: disable=g-import-not-at-top, For startup efficiency.
  argspec = inspect.getargspec(func)
  default_index_start = len(argspec.args) - len(argspec.defaults or [])
  formals = []
  for formal_index, formal in enumerate(argspec.args):
    if formal:
      formal = _StripUnusedNotation(formal)
    if formal in hidden_args:
      continue
    default_index = formal_index - default_index_start
    default = argspec.defaults[default_index] if default_index >= 0 else None
    if default is not None:
      default_display = repr(default).replace("'", '"')
      if default_display == 'False':
        default_display = 'false'
      elif default_display == 'True':
        default_display = 'true'
      formals.append('{formal}={default_display}'.format(
          formal=formal, default_display=default_display))
    else:
      formals.append(formal)
  if argspec.varargs:
    formals.append(argspec.varargs)
  prototype = '({formals})'.format(formals=', '.join(formals))

  return ' '.join(descriptions), prototype, args, example


def _TransformsDescriptions(transforms):
  """Generates resource transform help text markdown for transforms.

  Args:
    transforms: The transform name=>method symbol table.

  Returns:
    The resource transform help text markdown for transforms.
  """
  descriptions = []
  for name, transform in sorted(transforms.iteritems()):
    description, prototype, args, example = _ParseTransformDocString(transform)
    if not description:
      continue
    descriptions.append('\n*{name}*{prototype}::\n{description}\n'.format(
        name=name, prototype=prototype, description=description))
    if args:
      descriptions.append('+\n+\nThe arguments are:\n\n')
      for arg, description in args:
        descriptions.append('*```{arg}```*:::\n{description}\n'.format(
            arg=arg, description=description))
    if example:
      descriptions.append('+\nFor example`:`:::\n\n{example}\n'.format(
          example=' '.join(example)))
  return ''.join(descriptions)


def TransformRegistryDescriptions():
  """Returns help markdown for all registered resource transforms."""
  apis = set([x.split('.')[0]
              for x in resource_registry.RESOURCE_REGISTRY.keys()])
  descriptions = []
  for api in ['builtin'] + sorted(apis):
    transforms = resource_transform.GetTransforms(api)
    if transforms:
      descriptions.append(
          '\nThe {api} transform functions are:\n{desc}\n'.format(
              api=api, desc=_TransformsDescriptions(transforms)))
  return ''.join(descriptions)
