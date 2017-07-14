# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Cloud resource list filter expression evaluator backend."""

import abc
import re

from googlecloudsdk.core.resource import resource_exceptions
from googlecloudsdk.core.resource import resource_property
from googlecloudsdk.core.util import times


def _Equals(value, operand):
  """Applies string equality check to operand."""
  # Downcase value for case insensitive match. operand is already downcased.
  try:
    value = value.lower()
  except AttributeError:
    pass
  if value == operand:
    return True
  try:
    if value == float(operand):
      return True
  except ValueError:
    pass
  try:
    if value == int(operand):
      return True
  except ValueError:
    pass
  if value is None:
    try:
      return operand in ['nil', 'none', 'null']
    except TypeError:
      pass
  return False


def _StripTrailingDotZeroes(number):
  """Returns the string representation of number with trailing .0* deleted."""
  return re.sub(r'\.0*$', '', str(float(number)))


def _Has(value, pattern):
  """Returns True if value HAS matches pattern.

  Args:
    value: The value to be matched by pattern.
    pattern: A list of strings of length 1 or 2. The length 1 list specifies a
      string that must be contained by value. A length 2 list specifies a
      [prefix, suffix] pair. prefix and/or suffix may be the empty string:
        prefix,suffix   value must start with prefix and end with suffix
        prefix,''       value must start with prefix
        '',suffix       value must end with suffix
        '',''           special case to match non-empty values

  Returns:
    True if pattern matches value.

  Examples:
    EXPRESSION  PATTERN         VALUE       MATCHES
    abc*xyz     ['abc', 'xyz']  abcpdqxyz   True
    abc*        ['abc', '']     abcpdqxyz   True
    abc         ['abc']         abcpdqxyz   True
    *abc        ['', 'abc']     abcpdqxyz   False
    pdq*        ['pdq', '']     abcpdqxyz   False
    pdq         ['pdq']         abcpdqxyz   True
    *pdq        ['', 'pdq']     abcpdqxyz   False
    xyz*        ['xyz', '']     abcpdqxyz   False
    xyz         ['xyz']         abcpdqxyz   True
    *xyz        ['', 'xyz']     abcpdqxyz   True
    *           ['', '']        abcpdqxyz   True
    *           ['', '']        <''>        False
    *           ['', '']        <None>      False
    *           ['', '']        <non-empty> True
  """
  # Downcase value for case insensitive match. pattern is already downcased.
  try:
    value = value.lower()
  except AttributeError:
    pass

  prefix = pattern[0]
  if len(pattern) == 1:
    # Test if value contains prefix.
    try:
      return prefix in value
    except TypeError:
      pass
    try:
      return _StripTrailingDotZeroes(prefix) in _StripTrailingDotZeroes(value)
    except (TypeError, ValueError):
      pass
    return False

  suffix = pattern[1]
  if not prefix and not suffix:
    # key:* (empty prefix and suffix) special-cased for non-empty string match.
    return bool(value)

  # prefix*suffix match
  if prefix and not value.startswith(prefix):
    return False
  if suffix and not value.endswith(suffix):
    return False
  return True


def _IsIn(matcher, value, operand):
  """Applies matcher to determine if value matches/contains operand.

  Both value and operand can be lists.

  Args:
    matcher: Boolean match function that takes value as an argument and
      returns True if the value matches/contains the expression operand.
    value: The key value or list of values.
    operand: Operand value or list of values.

  Returns:
    True if the value (or any element in value if it is a list) matches/contains
    operand (or any element in operand if it is a list).
  """
  values = value if isinstance(value, (dict, list, tuple)) else [value]
  operands = operand if isinstance(operand, (dict, list, tuple)) else [operand]
  for v in values:
    for o in operands:
      if matcher(v, o):
        return True
  return False


class Backend(object):
  """Cloud resource list filter expression evaluator backend.

  This is a backend for resource_filter.Parser(). The generated "evaluator" is a
  parsed resource expression tree with branching factor 2 for binary operator
  nodes, 1 for NOT and function nodes, and 0 for TRUE nodes. Evaluation for a
  resource object starts with expression_tree_root.Evaluate(obj) which
  recursively evaluates child nodes. The logic operators use left-right shortcut
  pruning, so an evaluation may not visit every node in the expression tree.
  """

  # The remaining methods return an initialized class object.

  def ExprTRUE(self):
    return _ExprTRUE(self)

  def ExprAND(self, left, right):
    return _ExprAND(self, left, right)

  def ExprOR(self, left, right):
    return _ExprOR(self, left, right)

  def ExprNOT(self, expr):
    return _ExprNOT(self, expr)

  def ExprGlobal(self, call):
    return _ExprGlobal(self, call)

  def ExprOperand(self, value):
    return _ExprOperand(self, value)

  def ExprLT(self, key, operand, transform=None):
    return _ExprLT(self, key, operand, transform)

  def ExprLE(self, key, operand, transform=None):
    return _ExprLE(self, key, operand, transform)

  def ExprHAS(self, key, operand, transform=None):
    """Case insensitive membership node.

    This is the pre-compile Expr for the ':' operator. It compiles into an
    _ExprHAS node for prefix*suffix matching.

    The * operator splits the operand into prefix and suffix matching strings.

    Args:
      key: Resource object key (list of str, int and/or None values).
      operand: The term ExprOperand operand.
      transform: Optional key value transform calls.

    Returns:
      _ExprHAS.
    """
    return _ExprHAS(self, key, operand, transform)

  def ExprEQ(self, key, operand, transform=None):
    """Case sensitive EQ node.

    Args:
      key: Resource object key (list of str, int and/or None values).
      operand: The term ExprOperand operand.
      transform: Optional key value transform calls.

    Returns:
      _ExprEQ.
    """
    return _ExprEQ(self, key, operand, transform)

  def ExprNE(self, key, operand, transform=None):
    return _ExprNE(self, key, operand, transform)

  def ExprGE(self, key, operand, transform=None):
    return _ExprGE(self, key, operand, transform)

  def ExprGT(self, key, operand, transform=None):
    return _ExprGT(self, key, operand, transform)

  def ExprRE(self, key, operand, transform=None):
    return _ExprRE(self, key, operand, transform)

  def ExprNotRE(self, key, operand, transform=None):
    return _ExprNotRE(self, key, operand, transform)


# _Expr* class instantiations are done by the Backend.Expr* methods.


class _Expr(object):
  """Expression base class."""

  __metaclass__ = abc.ABCMeta

  def __init__(self, backend):
    self.backend = backend

  @abc.abstractmethod
  def Evaluate(self, obj):
    """Returns the value of the subexpression applied to obj.

    Args:
      obj: The current resource object.

    Returns:
      True if the subexpression matches obj, False if it doesn't match, or
      None if the subexpression is not supported.
    """
    pass


class _ExprTRUE(_Expr):
  """TRUE node.

  Always evaluates True.
  """

  def Evaluate(self, unused_obj):
    return True


class _ExprLogical(_Expr):
  """Base logical operator node.

  Attributes:
    left: Left Expr operand.
    right: Right Expr operand.
  """

  def __init__(self, backend, left, right):
    super(_ExprLogical, self).__init__(backend)
    self._left = left
    self._right = right


class _ExprAND(_ExprLogical):
  """AND node.

  AND with left-to-right shortcut pruning.
  """

  def Evaluate(self, obj):
    if not self._left.Evaluate(obj):
      return False
    if not self._right.Evaluate(obj):
      return False
    return True


class _ExprOR(_ExprLogical):
  """OR node.

  OR with left-to-right shortcut pruning.
  """

  def Evaluate(self, obj):
    if self._left.Evaluate(obj):
      return True
    if self._right.Evaluate(obj):
      return True
    return False


class _ExprNOT(_Expr):
  """NOT node."""

  def __init__(self, backend, expr):
    super(_ExprNOT, self).__init__(backend)
    self._expr = expr

  def Evaluate(self, obj):
    return not self._expr.Evaluate(obj)


class _ExprGlobal(_Expr):
  """Global restriction function call node.

  Attributes:
    _call: The function call object.
  """

  def __init__(self, backend, call):
    super(_ExprGlobal, self).__init__(backend)
    self._call = call

  def Evaluate(self, obj):
    return self._call.Evaluate(obj)


class _ExprOperand(object):
  """Operand node.

  Converts an expession value token string to internal string and/or numeric
  values. If an operand has a numeric value then the actual key values are
  converted to numbers at Evaluate() time if possible for Apply(); if the
  conversion fails then the key and operand string values are passed to Apply().

  Attributes:
    list_value: A list of operands.
    numeric_value: The int or float number, or None if the token string does not
      convert to a number.
    string_value: The token string.
  """

  _NUMERIC_CONSTANTS = {
      'false': 0,
      'true': 1,
  }

  def __init__(self, backend, value, normalize=None):
    self.backend = backend
    self.list_value = None
    self.numeric_value = None
    self.string_value = None
    self.Initialize(value, normalize=normalize)

  def Initialize(self, value, normalize=None):
    """Initializes an operand string_value and numeric_value from value.

    Args:
      value: The operand expression string value.
      normalize: Optional normalization function.
    """
    if isinstance(value, list):
      self.list_value = []
      for val in value:
        self.list_value.append(
            _ExprOperand(self.backend, val, normalize=normalize))
    elif value and normalize:
      self.string_value = normalize(value)
    elif isinstance(value, basestring):
      self.string_value = value
      try:
        self.numeric_value = self._NUMERIC_CONSTANTS[value.lower()]
      except KeyError:
        try:
          self.numeric_value = int(value)
        except ValueError:
          try:
            self.numeric_value = float(value)
          except ValueError:
            pass
    else:
      self.string_value = unicode(value)
      self.numeric_value = value


class _ExprOperator(_Expr):
  """Base term (<key operator operand>) node.

  ExprOperator subclasses must define the function Apply(self, value, operand)
  that returns the result of <value> <op> <operand>.

  Attributes:
    _key: Resource object key (list of str, int and/or None values).
    _normalize: The resource value normalization function.
    _operand: The term ExprOperand operand.
    _transform: Optional key value transform calls.
  """

  __metaclass__ = abc.ABCMeta

  def __init__(self, backend, key, operand, transform):
    super(_ExprOperator, self).__init__(backend)
    self._key = key
    self._operand = operand
    self._transform = transform
    if transform:
      self._normalize = lambda x: x
    else:
      self._normalize = self.InitializeNormalization

  def InitializeNormalization(self, value):
    """Checks the first non-empty resource value to see if it can be normalized.

    This method is called at most once on the first non-empty resource value.
    After that a new normalization method is set for the remainder of the
    resource values.

    Resource values are most likely well defined protobuf string encodings. The
    RE patterns match against those.

    Args:
      value: A resource value to normalize.

    Returns:
      The normalized value.
    """
    self._normalize = lambda x: x

    # Check for datetime. Dates may have trailing timzone indicators. We don't
    # match them but ParseDateTime will handle them.
    if re.match(r'\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d', value):
      try:
        value = times.ParseDateTime(value)
        # Make sure the value and operand times are both tz aware or tz naive.
        # Otherwise datetime comparisons will fail.
        tzinfo = times.LOCAL if value.tzinfo else None
        self._operand.Initialize(
            self._operand.list_value or self._operand.string_value,
            normalize=lambda x: times.ParseDateTime(x, tzinfo=tzinfo))
        self._normalize = times.ParseDateTime
      except ValueError:
        pass

    # More type checks go here.

    return value

  def Evaluate(self, obj):
    """Evaluate a term node.

    Args:
      obj: The resource object to evaluate.
    Returns:
      The value of the operator applied to the key value and operand.
    """
    value = resource_property.Get(obj, self._key)
    if self._transform:
      value = self._transform.Evaluate(value)
    # Arbitrary choice: value == []  =>  values = [[]]
    resource_values = value if value and isinstance(value, list) else [value]
    values = []
    for value in resource_values:
      if value:
        try:
          value = self._normalize(value)
        except (TypeError, ValueError):
          pass
      values.append(value)

    if self._operand.list_value:
      operands = self._operand.list_value
    else:
      operands = [self._operand]

    # Check for any match in all value X operand combinations.
    for value in values:
      for operand in operands:
        # Each try/except attempts a different combination of value/operand
        # numeric and string conversions.

        if operand.numeric_value is not None:
          try:
            if self.Apply(float(value), operand.numeric_value):
              return True
            # Both value and operand are numbers - don't try as strings below.
            continue
          except (TypeError, ValueError):
            pass

        try:
          if self.Apply(value, operand.string_value):
            return True
        except (AttributeError, ValueError):
          pass
        except TypeError:
          if not isinstance(value, (basestring, dict, list)):
            try:
              if self.Apply(unicode(value), operand.string_value):
                return True
            except TypeError:
              pass

    return False

  @abc.abstractmethod
  def Apply(self, value, operand):
    """Returns the value of applying a <value> <operator> <operand> term.

    Args:
      value: The term key value.
      operand: The term operand value.

    Returns:
      The Boolean value of applying a <value> <operator> <operand> term.
    """
    pass


class _ExprLT(_ExprOperator):
  """LT node."""

  def Apply(self, value, operand):
    return value < operand


class _ExprLE(_ExprOperator):
  """LE node."""

  def Apply(self, value, operand):
    return value <= operand


class _ExprHAS(_ExprOperator):
  """Membership HAS match node."""

  def __init__(self, backend, key, operand, transform):
    super(_ExprHAS, self).__init__(backend, key, operand, transform)
    self._patterns = []
    if self._operand.list_value is not None:
      for operand in self._operand.list_value:
        if operand.string_value:
          operand.string_value = unicode(operand.string_value).lower()
          self._AddPattern(operand.string_value)
    elif self._operand.string_value:
      self._AddPattern(unicode(self._operand.string_value).lower())

  def _AddPattern(self, pattern):
    """Adds a HAS match pattern to self._patterns.

    The pattern is a list of strings of length 1 or 2:
      [string]: The subject string must contain string ignoring case.
      [prefix, suffix]: The subject string must start with prefix and end with
        suffix ignoring case.

    Args:
      pattern: A string containing at most one * glob character.

    Raises:
      resource_exceptions.ExpressionSyntaxError if the pattern contains more
        than one * glob character.
    """
    if '*' in pattern:
      parts = unicode(pattern).lower().split('*')
      if len(parts) > 2:
        raise resource_exceptions.ExpressionSyntaxError(
            'Zero or one * expected in : patterns.')
      self._patterns.append(parts)
    else:
      self._patterns.append([pattern])

  def Apply(self, value, operand):
    """Checks if value HAS matches operand ignoring case differences.

    Args:
      value: The number, string, dict or list object value.
      operand: Non-pattern operand for equality check. The ':' HAS operator
        operand can be a prefix*suffix pattern or a literal value. Literal
        values are first checked by the _Equals method to handle numeric
        constant matching. String literals and patterns are then matched by the
        _Has method.

    Returns:
      True if value HAS matches operand (or any value in operand if it is a
      list) ignoring case differences.
    """
    return _IsIn(_Equals, value, operand) or _IsIn(_Has, value, self._patterns)


class _ExprEQ(_ExprOperator):
  """Membership equality match node."""

  def __init__(self, backend, key, operand, transform):
    super(_ExprEQ, self).__init__(backend, key, operand, transform)
    if self._operand.list_value is not None:
      for operand in self._operand.list_value:
        if operand.string_value:
          operand.string_value = unicode(operand.string_value).lower()
    elif self._operand.string_value:
      self._operand.string_value = unicode(self._operand.string_value).lower()

  def Apply(self, value, operand):
    """Checks if value is equal to operand.

    Args:
      value: The number, string, dict or list object value.
      operand: Number or string or list of Number or String.

    Returns:
      True if value is equal to operand (or any value in operand if it is a
      list).
    """
    return _IsIn(_Equals, value, operand)


class _ExprMatch(_ExprOperator):
  """Anchored prefix*suffix match node."""

  def __init__(self, backend, key, operand, transform, prefix, suffix):
    """Initializes the anchored prefix and suffix patterns.

    Args:
      backend: The parser backend object.
      key: Resource object key (list of str, int and/or None values).
      operand: The term ExprOperand operand.
      transform: Optional key value transform calls.
      prefix: The anchored prefix pattern string.
      suffix: The anchored suffix pattern string.
    """
    super(_ExprMatch, self).__init__(backend, key, operand, transform)
    self._prefix = prefix
    self._suffix = suffix

  def Apply(self, value, unused_operand):
    return ((not self._prefix or value.startswith(self._prefix)) and
            (not self._suffix or value.endswith(self._suffix)))


class _ExprNE(_ExprOperator):
  """NE node."""

  def Apply(self, value, operand):
    try:
      return operand != value.lower()
    except AttributeError:
      return value != operand


class _ExprGE(_ExprOperator):
  """GE node."""

  def Apply(self, value, operand):
    return value >= operand


class _ExprGT(_ExprOperator):
  """GT node."""

  def Apply(self, value, operand):
    return value > operand


class _ExprRE(_ExprOperator):
  """Unanchored RE match node."""

  def __init__(self, backend, key, operand, transform):
    super(_ExprRE, self).__init__(backend, key, operand, transform)
    self.pattern = re.compile(self._operand.string_value)

  def Apply(self, value, unused_operand):
    if not isinstance(value, basestring):
      # This exception is caught by Evaluate().
      raise TypeError('RE match subject value must be a string.')
    return self.pattern.search(value) is not None


class _ExprNotRE(_ExprOperator):
  """Unanchored RE not match node."""

  def __init__(self, backend, key, operand, transform):
    super(_ExprNotRE, self).__init__(backend, key, operand, transform)
    self.pattern = re.compile(self._operand.string_value)

  def Apply(self, value, unused_operand):
    if not isinstance(value, basestring):
      # This exception is caught by Evaluate().
      raise TypeError('RE match subject value must be a string.')
    return self.pattern.search(value) is None
