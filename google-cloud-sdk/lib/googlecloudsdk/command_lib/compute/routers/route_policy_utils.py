# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Code that's shared between multiple router route policies subcommands."""

from googlecloudsdk.core import exceptions as core_exceptions


class RoutePolicyError(core_exceptions.Error):
  """Error superclass for all router route policies surface-related errors."""


class PolicyTermNotFoundError(RoutePolicyError):
  """Error raised when a policy term is not found."""

  def __init__(self, term_priority):
    msg = 'Policy term [{term_priority}] not found.'.format(
        term_priority=term_priority
    )
    super(PolicyTermNotFoundError, self).__init__(msg)


def FindPolicyTermOrRaise(resource, term_priority):
  """Searches for and returns a term in the route policy resource.

  Args:
    resource: The route policy resource to find term for.
    term_priority: The priority of the term to find.

  Returns:
    The term with the given priority, if found.

  Raises:
    PolicyTermNotFoundError: If no term with the given priority is found.
  """
  for term in resource.terms:
    if term.priority == term_priority:
      return term
  raise PolicyTermNotFoundError(term_priority)


class NamedSetError(core_exceptions.Error):
  """Error superclass for all router named set surface-related errors."""


class NamedSetElementNotFoundError(NamedSetError):
  """Error raised when a named set element is not found."""

  def __init__(self, element):
    msg = 'Named set element {element} not found.'.format(element=element)
    super(NamedSetElementNotFoundError, self).__init__(msg)


def FindNamedSetElementOrRise(resource, element_cel):
  """Searches for and returns an element in the named set resource.

  Args:
    resource: The named set resource to find element for.
    element_cel: The CEL expression of the element to find.

  Returns:
    The element with the given CEL expression, if found.

  Raises:
    NamedSetElementNotFoundError: If no element with the given CEL expression is
    found.
  """
  for element in resource.elements:
    if element.expression == element_cel:
      return element
  raise NamedSetElementNotFoundError(element_cel)
