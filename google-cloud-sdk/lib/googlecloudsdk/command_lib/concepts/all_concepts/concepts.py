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

"""Classes to specify concept and resource specs.

To use a concept, give it at least help text and a name (or use
the default name if the concept provides one) and add it to a concept manager.
During command.Run, the parsed concept will be available under
args.CONCEPT_ARGS. For example:

from googlecloudsdk.command_lib.concepts import concept_managers

  def Args(self, parser):
    manager = concept_managers.ConceptManager()
    concept = concepts.SimpleArg('foo', help_text='Provide the value of foo.')
    manager.AddConcept(concept)
    manager.AddToParser(parser)

  def Run(self, args):
    return args.CONCEPT_ARGS.foo
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import deps as deps_lib
from googlecloudsdk.command_lib.concepts import base
from googlecloudsdk.command_lib.concepts import exceptions
from googlecloudsdk.command_lib.concepts import names

import six


class SimpleArg(base.Concept):
  """A single attribute concept."""

  def __init__(self, name, fallthroughs=None, positional=False, completer=None,
               metavar=None, **kwargs):
    """Initializes the concept."""
    self.fallthroughs = fallthroughs or []
    self.positional = positional
    self.completer = completer
    self.metavar = metavar
    super(SimpleArg, self).__init__(name, **kwargs)

  def Attribute(self):
    return base.Attribute(concept=self,
                          fallthroughs=self.fallthroughs,
                          help=self.BuildHelpText(),
                          required=self._ArgIsRequired(),
                          hidden=self.hidden,
                          completer=self.completer,
                          metavar=self.metavar)

  def Parse(self, dependencies):
    """Parses the concept.

    Args:
      dependencies: googlecloudsdk.command_lib.concepts.dependency_managers
        .DependencyView, the dependency namespace for the concept.

    Raises:
      exceptions.MissingRequiredArgumentException, if no value is provided and
        one is required.

    Returns:
      str, the value given to the argument.
    """
    try:
      return dependencies.value
    except deps_lib.AttributeNotFoundError as e:
      if self.required:
        raise exceptions.MissingRequiredArgumentException(
            self.GetPresentationName(), six.text_type(e))
      return None

  def BuildHelpText(self):
    """Builds help text for the attribute. No post-processing."""
    return self.help_text

  def GetPresentationName(self):
    """Gets presentation name for the attribute, either positional or flag."""
    if self.positional:
      return names.ConvertToPositionalName(self.name)
    return names.ConvertToFlagName(self.name)

  def _ArgIsRequired(self):
    """Determines whether command line argument for attribute is required.

    Returns:
      bool: True, if the command line argument is required to be provided,
        meaning that the attribute is required and that there are no
        fallthroughs. There may still be a parsing error if the argument isn't
        provided and none of the fallthroughs work.
    """
    return self.required and not bool(self.fallthroughs)


class DayOfTheWeek(SimpleArg):
  """Day of the week concept."""

  _DAYS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']

  def __init__(self, name='day', **kwargs):
    super(DayOfTheWeek, self).__init__(name, **kwargs)

  def Parse(self, dependencies):
    """Parses the concept.

    Args:
      dependencies: googlecloudsdk.command_lib.concepts.dependency_managers
        .DependencyView, the dependency namespace for the concept.

    Raises:
      exceptions.MissingRequiredArgumentException, if no value is provided and
        one is required.
      exceptions.ParseError, if the value provided is incorrect.

    Returns:
      str | None, the day of the week, abbreviated to the first three letters in
        upper-case format, or None if no day was given and the attribute
        is not required.
    """
    given = super(DayOfTheWeek, self).Parse(dependencies)
    if given is None:
      return given
    fixed = given.upper()[:3]
    if fixed not in self._DAYS:
      raise exceptions.ParseError(
          self.GetPresentationName(),
          'Value for day of the week should be one of: [{}]. '
          'You gave: [{}]'.format(', '.join(self._DAYS), given))
    return fixed

  def BuildHelpText(self):
    """Builds help text for the attribute, with validation information."""
    return (
        '{} Must be a string representing a day of the week in English, such '
        'as \'MON\' or \'FRI\'. Case is ignored, and any characters after the '
        'first three characters are ignored.'.format(
            self.help_text))

