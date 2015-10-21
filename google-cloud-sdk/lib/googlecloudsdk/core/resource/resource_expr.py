# Copyright 2015 Google Inc. All Rights Reserved.

"""Cloud resource list filter expression evaluator backend."""

import abc
import re

from googlecloudsdk.core.resource import resource_property


def _IsIn(matcher, value):
  """Applies matcher to determine if the expression operand is in value.

  Args:
    matcher: Boolean match function that takes value as an argument and
      returns True if the expression operand is in value.
    value: The value to match against.

  Returns:
    True if the expression operand is in value.
  """
  if matcher(value):
    return True
  try:
    for index in value:
      if matcher(index):
        return True
  except TypeError:
    pass
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

  def ExprGlobal(self, func, args):
    return _ExprGlobal(self, func, args)

  def ExprOperand(self, value):
    return _ExprOperand(self, value)

  def ExprLT(self, key, operand, transform=None, args=None):
    return _ExprLT(self, key, operand, transform, args)

  def ExprLE(self, key, operand, transform=None, args=None):
    return _ExprLE(self, key, operand, transform, args)

  def ExprHAS(self, key, operand, transform=None, args=None):
    """Case insensitive membership node.

    This is the pre-compile Expr for the ':' operator. It compiles into either
    an _ExprInMatch node for prefix*suffix matching or an _ExprIn node for
    membership.

    The * operator splits the operand into prefix and suffix matching strings.

    Args:
      key: Resource object key (list of str, int and/or None values).
      operand: The term ExprOperand operand.
      transform: Optional key value transform function.
      args: Optional key value transform function actual args.

    Returns:
      _ExprInMatch if operand is an anchored pattern, _ExprIn otherwise.
    """
    if '*' not in operand.string_value:
      return _ExprIn(self, key, operand, transform, args)
    pattern = operand.string_value.lower()
    i = pattern.find('*')
    prefix = pattern[:i]
    suffix = pattern[i + 1:]
    return _ExprInMatch(self, key, operand, transform, args, prefix, suffix)

  def ExprEQ(self, key, operand, transform=None, args=None):
    """Case sensitive EQ node.

    Checks for prefix*suffix operand.

    The * operator splits the operand into prefix and suffix matching strings.

    Args:
      key: Resource object key (list of str, int and/or None values).
      operand: The term ExprOperand operand.
      transform: Optional key value transform function.
      args: Optional key value transform function actual args.

    Returns:
      _ExprMatch if operand is an anchored pattern, _ExprEqual otherwise.
    """
    if '*' not in operand.string_value:
      return _ExprEqual(self, key, operand, transform, args)
    pattern = operand.string_value
    i = pattern.find('*')
    prefix = pattern[:i]
    suffix = pattern[i + 1:]
    return _ExprMatch(self, key, operand, transform, args, prefix, suffix)

  def ExprNE(self, key, operand, transform=None, args=None):
    return _ExprNE(self, key, operand, transform, args)

  def ExprGE(self, key, operand, transform=None, args=None):
    return _ExprGE(self, key, operand, transform, args)

  def ExprGT(self, key, operand, transform=None, args=None):
    return _ExprGT(self, key, operand, transform, args)

  def ExprRE(self, key, operand, transform=None, args=None):
    return _ExprRE(self, key, operand, transform, args)

  def ExprNotRE(self, key, operand, transform=None, args=None):
    return _ExprNotRE(self, key, operand, transform, args)


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
    func: The function implementation Expr. Must match this description:
          func(obj, args)

          Args:
            obj: The current resource object.
            args: The possibly empty list of arguments.

          Returns:
            True on success.
    args: List of function call actual arguments.
  """

  def __init__(self, backend, func, args):
    super(_ExprGlobal, self).__init__(backend)
    self._func = func
    self._args = args

  def Evaluate(self, unused_obj):
    return self._func(*self._args)


class _ExprOperand(object):
  """Operand node.

  Converts an expession value token string to internal string and/or numeric
  values. If an operand has a numeric value then the actual key values are
  converted to numbers at Evaluate() time if possible for Apply(); if the
  conversion fails then the key and operand string values are passed to Apply().

  Attributes:
    numeric_value: The int or float number, or None if the token string does not
      convert to a number.
    string_value: The token string.
  """

  def __init__(self, backend, value):
    self.backend = backend
    if isinstance(value, basestring):
      self.string_value = value
      try:
        self.numeric_value = int(value)
      except ValueError:
        try:
          self.numeric_value = float(value)
        except ValueError:
          self.numeric_value = None
    else:
      self.string_value = str(value)
      self.numeric_value = value


class _ExprOperator(_Expr):
  """Base term (<key operator operand>) node.

  ExprOperator subclasses must define the function Apply(self, value, operand)
  that returns the result of <value> <op> <operand>.

  Attributes:
    _key: Resource object key (list of str, int and/or None values).
    _operand: The term ExprOperand operand.
    _transform: Optional key value transform function.
    _args: Optional list of transform actual args.
  """

  __metaclass__ = abc.ABCMeta

  def __init__(self, backend, key, operand, transform, args):
    super(_ExprOperator, self).__init__(backend)
    self._key = key
    self._operand = operand
    self._transform = transform
    self._args = args

  def Evaluate(self, obj):
    """Evaluate a term node.

    Args:
      obj: The resource object to evaluate.
    Returns:
      The value of the operator applied to the key value and operand.
    """
    value = resource_property.Get(obj, self._key)
    if self._transform:
      try:
        if self._key:
          value = self._transform(value, *self._args)
        else:
          value = self._transform(*self._args)
      except (AttributeError, TypeError, ValueError):
        value = None
    # Each try/except attempts a different combination of value/operand
    # numeric and string conversions.
    if self._operand.numeric_value is not None:
      try:
        return self.Apply(float(value), self._operand.numeric_value)
      except (TypeError, ValueError):
        pass
    try:
      return self.Apply(value, self._operand.string_value)
    except (AttributeError, ValueError):
      return False
    except TypeError:
      if isinstance(value, basestring):
        return False
    try:
      return self.Apply(str(value), self._operand.string_value)
    except TypeError:
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


class _ExprInMatch(_ExprOperator):
  """Membership and anchored prefix*suffix match node."""

  def __init__(self, backend, key, operand, transform, args, prefix, suffix):
    """Initializes the anchored prefix and suffix patterns.

    Args:
      backend: The parser backend object.
      key: Resource object key (list of str, int and/or None values).
      operand: The term ExprOperand operand.
      transform: Optional key value transform function.
      args: Optional key value transform function actual args.
      prefix: The anchored prefix pattern string.
      suffix: The anchored suffix pattern string.
    """
    super(_ExprInMatch, self).__init__(backend, key, operand, transform, args)
    self._prefix = prefix
    self._suffix = suffix

  def Apply(self, value, unused_operand):
    """Applies the : anchored case insensitive match operation."""

    def _InMatch(value):
      """Applies case insensitive string prefix/suffix match to value."""
      if value is None:
        return False
      v = str(value).lower()
      return ((not self._prefix or v.startswith(self._prefix)) and
              (not self._suffix or v.endswith(self._suffix)))

    return _IsIn(_InMatch, value)


class _ExprIn(_ExprOperator):
  """Membership case-insensitive match node."""

  def __init__(self, backend, key, operand, transform, args):
    super(_ExprIn, self).__init__(backend, key, operand, transform, args)
    self._operand.string_value = self._operand.string_value.lower()

  def Apply(self, value, operand):
    """Checks if operand is a member of value ignoring case differences.

    Args:
      value: The number, string, dict or list object value.
      operand: Number or string operand.

    Returns:
      True if operand is a member of value ignoring case differences.
    """

    def _InEq(subject):
      """Applies case insensitive string contains check to subject."""
      if operand == subject:
        return True
      try:
        if operand == subject.lower():
          return True
      except AttributeError:
        pass
      try:
        if operand in subject:
          return True
      except TypeError:
        pass
      try:
        if operand in subject.lower():
          return True
      except AttributeError:
        pass
      try:
        if int(operand) in subject:
          return True
      except ValueError:
        pass
      try:
        if float(operand) in subject:
          return True
      except ValueError:
        pass
      return False

    return _IsIn(_InEq, value)


class _ExprMatch(_ExprOperator):
  """Anchored prefix*suffix match node."""

  def __init__(self, backend, key, operand, transform, args, prefix, suffix):
    """Initializes the anchored prefix and suffix patterns.

    Args:
      backend: The parser backend object.
      key: Resource object key (list of str, int and/or None values).
      operand: The term ExprOperand operand.
      transform: Optional key value transform function.
      args: Optional key value transform function actual args.
      prefix: The anchored prefix pattern string.
      suffix: The anchored suffix pattern string.
    """
    super(_ExprMatch, self).__init__(backend, key, operand, transform, args)
    self._prefix = prefix
    self._suffix = suffix

  def Apply(self, value, unused_operand):
    return ((not self._prefix or value.startswith(self._prefix)) and
            (not self._suffix or value.endswith(self._suffix)))


class _ExprEqual(_ExprOperator):
  """Case sensitive EQ node with no match optimization."""

  def Apply(self, value, operand):
    return operand == value


class _ExprNE(_ExprOperator):
  """NE node."""

  def Apply(self, value, operand):
    try:
      return operand != value.lower()
    except AttributeError:
      return operand != value


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

  def __init__(self, backend, key, operand, transform, args):
    super(_ExprRE, self).__init__(backend, key, operand, transform, args)
    self.pattern = re.compile(self._operand.string_value)

  def Apply(self, value, unused_operand):
    if not isinstance(value, basestring):
      # This exception is caught by Evaluate().
      raise TypeError('RE match subject value must be a string.')
    return self.pattern.search(value) is not None


class _ExprNotRE(_ExprOperator):
  """Unanchored RE not match node."""

  def __init__(self, backend, key, operand, transform, args):
    super(_ExprNotRE, self).__init__(backend, key, operand, transform, args)
    self.pattern = re.compile(self._operand.string_value)

  def Apply(self, value, unused_operand):
    if not isinstance(value, basestring):
      # This exception is caught by Evaluate().
      raise TypeError('RE match subject value must be a string.')
    return self.pattern.search(value) is None
