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

"""Cloud resource filter expression list filter rewrite backend.

None is the value for keys and operators not supported by the backend.
ExprTRUE, ExprAND, ExprOR and ExprNOT do expression rewrites based on None:

  TRUE => None
  (AND None x) => x
  (AND x None) => x
  (OR None x) => None
  (OR x None) => None
  (NOT None) => None

These rewrites can only prune expressions that will not be True client-side.
In this sense a rewrite => None means "the client side will figure it out".
This results in a backend expression that can be applied server-side to prune
the resources passed back to the client-side, where the full filter expression
is applied. The result will be the same whether or not the backend filter is
applied. The only difference would be the number of resources transmitted
from the server back to the client.

It is possible for a rewritten expression to collapse to None. This means that
there is no equivalent server-side expression, i.e., no server-side pruning is
possible.
"""

import abc
import re

from googlecloudsdk.core.resource import resource_lex


class Backend(object):
  """Cloud resource filter expression list filter rewrite backend.

  Evaluate() returns the list filter string equivalent of the filter expression.

  Attributes:
    op_space: Rewritten operators offset by space if True.
    supported_key: supported_key(key) returns True if the parse key is supported
      by the backend. None means all keys are supported.
    supported_op: supported_op(name) returns True if the op name string is
      supported by the backend. None means all ops are supported. Note that '"'
      is used to check if "..." quoted operands are supported and '(' is used to
      check if (...) is supported.
    supported_operand: supported_operand(value) returns True if the operand
      value is supported by the backend. None means all operands are supported.
  """

  def __init__(self, op_space=False, supported_key=None, supported_op=None,
               supported_operand=None):
    self.sp = ' ' if op_space else ''
    self.supported_key = supported_key or (lambda x: True)
    self.supported_op = supported_op or (lambda x: True)
    self.supported_operand = supported_operand or (lambda x: True)
    if self.supported_op('('):
      self.left_paren = '(' + self.sp
      self.right_paren = self.sp + ')'
    else:
      self.left_paren = ''
      self.right_paren = ''

  def Equals(self, op):
    """Returns the equivalent equality op for op or None if not supported.

    Args:
      op: The original equality op.

    Returns:
      The equivalent equality op for op or None if not supported.
    """
    for eq in (op, ':', '='):
      if self.supported_op(eq):
        return eq
    return None

  def InvertUndefinedComparison(self, comparison, inverse, value, operand):
    """Returns the rewrite for the `value comparison operand' term.

    If comparison is not supported then the negation of `value inverse operand'
    is attempted.

    Args:
      comparison: The comparison operator.
      inverse: The comparison operator inverse.
      value: The operation value.
      operand: The operation operand.

    Returns:
      The expression rewrite, None if it is not supported.
    """
    if self.supported_op(comparison):
      return self.Term(comparison, value, operand)
    if not self.supported_op('NOT'):
      return None
    term = self.Term(inverse, value, operand)
    if not term:
      return None
    negate = self.Negate(term)
    if not negate:
      return None
    # `value operator operand' term precedence is higher than the negation op.
    return '{negate}{term}'.format(negate=negate, term=term)

  def Negate(self, operand=None):
    """Returns the operator string that negates operand.

    Args:
      operand: A rewritten operand string.

    Returns:
      The operator string that negates operand, None if there is no suitable
      negation operator.
    """
    # The LF '-' prefix operator does not apply to parenthesized expressions.
    if (not operand or not operand.startswith('(')) and self.supported_op('-'):
      return '-'
    if self.supported_op('NOT'):
      return 'NOT '
    return None

  def Quote(self, value):
    """Returns value or "value" if necessary.

    Args:
      value: The value string to be quoted.

    Returns:
      value or "value" if necessary.
    """
    if self.supported_op('"') and re.search(r'[^][^$\w*.+?-]', value):
      value = value.replace('\\', '\\\\')
      value = value.replace('"', '\\"')
      value = '"{value}"'.format(value=value)
    return value

  def Term(self, op, value, operand):
    """Returns the rewrite for the `value op operand' term.

    Args:
      op: The operation operator.
      value: The operation value term.
      operand: The operation operand term.

    Returns:
      The operation rewrite, None if it is not supported.
    """
    if not op or not self.supported_op(op):
      return None
    return '{value}{sp}{op}{sp}{operand}'.format(
        value=value, op=op, sp=self.sp, operand=operand)

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

  def ExprLT(self, key, operand, transform=None, args=None):
    return _ExprLT(self, key, operand, transform, args)

  def ExprLE(self, key, operand, transform=None, args=None):
    return _ExprLE(self, key, operand, transform, args)

  def ExprHAS(self, key, operand, transform=None, args=None):
    return _ExprHAS(self, key, operand, transform, args)

  def ExprEQ(self, key, operand, transform=None, args=None):
    return _ExprEQ(self, key, operand, transform, args)

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
      The subexpression rewrite string, or None if the subexpression is not
      supported.
    """
    pass


class _ExprTRUE(_Expr):
  """TRUE node.

  Always evaluates True.
  """

  def Evaluate(self, unused_obj):
    # TRUE => None
    return None


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
    """Rewrites an AND node."""
    left = self._left.Evaluate(obj)
    right = self._right.Evaluate(obj)
    # None AND x => x
    if left is None:
      return right
    # x AND None => x
    if right is None:
      return left
    if self.backend.supported_op('AND'):
      op = ' AND '
    elif self.backend.supported_op(''):
      op = ' '
    else:
      return None
    # Defer to LF bass-ackwards OR >> AND precedence.
    return '{left_paren}{left}{op}{right}{right_paren}'.format(
        left_paren=self.backend.left_paren, left=left, op=op, right=right,
        right_paren=self.backend.right_paren)


class _ExprOR(_ExprLogical):
  """OR node.

  OR with left-to-right shortcut pruning.
  """

  def Evaluate(self, obj):
    """Rewrites an OR node."""
    if not self.backend.supported_op('OR'):
      return None
    left = self._left.Evaluate(obj)
    right = self._right.Evaluate(obj)
    # None OR x => None
    # x OR None => None
    if left is None or right is None:
      return None
    if not self.backend.left_paren:
      if ' AND ' in left or ' AND ' in right:
        # With no (...) LF bass-ackwards OR >> AND precedence cannot be
        # overridden.
        return None
    return '{left_paren}{left} OR {right}{right_paren}'.format(
        left_paren=self.backend.left_paren, left=left,
        right=right, right_paren=self.backend.right_paren)


class _ExprNOT(_Expr):
  """NOT node."""

  def __init__(self, backend, expr):
    super(_ExprNOT, self).__init__(backend)
    self._expr = expr

  def Evaluate(self, obj):
    """Rewrites a NOT node."""
    term = self._expr.Evaluate(obj)
    if not term:
      return None
    negate = self.backend.Negate(term)
    if not negate:
      return None
    return '{negate}{term}'.format(negate=negate, term=term)


class _ExprGlobal(_Expr):
  """Global restriction function call node.

  Attributes:
    call: The fucntion call object.
  """

  def __init__(self, backend, call):
    super(_ExprGlobal, self).__init__(backend)
    self._call = call

  def Evaluate(self, obj):
    """Global restriction (function)."""
    return self._call.Evaluate(obj)


class _ExprOperand(object):
  """Operand node.

  Converts an expression value token string to a rewrite expression string.

  Attributes:
    value: One of these, checked in order:
      * integer number string representation
      * floating point number string representation
      * quoted string literal
  """

  def __init__(self, backend, value):
    try:
      self.value = str(int(value))
    except ValueError:
      try:
        self.value = str(float(value))
      except ValueError:
        self.value = backend.Quote(value)


class _ExprOperator(_Expr):
  """Base term (<key operator operand>) node.

  ExprOperator subclasses must define the function Apply(self, value, operand)
  that returns the result of <value> <op> <operand>.

  Attributes:
    _key: Resource object key (list of str, int and/or None values).
    _operand: The term ExprOperand operand.
    _supported: True if key is supported by the self.backend.
  """

  __metaclass__ = abc.ABCMeta

  def __init__(self, backend, key, operand, transform, args):
    """Initializer.

    Args:
      backend: The parser backend object.
      key: Resource object key (list of str, int and/or None values).
      operand: The term ExprOperand operand.
      transform: Optional key value transform function.
      args: Optional list of transform actual args.
    """
    super(_ExprOperator, self).__init__(backend)
    self._supported = (not transform and not args and
                       self.backend.supported_key(key) and
                       self.backend.supported_operand(operand.value))
    if self._supported:
      self._key = resource_lex.GetKeyName(key)
      if '"' in self._key and not self.backend.supported_op('"'):
        self._supported = False
      self._operand = operand

  def Evaluate(self, unused_obj):
    """Rewrites an term node."""
    if not self._supported:
      return None
    return self.Apply(self._key, self._operand.value)

  @abc.abstractmethod
  def Apply(self, value, operand):
    """Returns the value of applying a <value> <operator> <operand> term.

    Args:
      value: The term key value.
      operand: The term operand value.

    Returns:
      The rewrite string value of applying a <value> <operator> <operand> term
      or None if any of <value> <operator> <operand> are unsupported.
    """
    pass


class _ExprLT(_ExprOperator):
  """LT node."""

  def Apply(self, value, operand):
    return self.backend.Term('<', value, operand)


class _ExprLE(_ExprOperator):
  """LE node."""

  def Apply(self, value, operand):
    return self.backend.Term('<=', value, operand)


class _ExprHAS(_ExprOperator):
  """Case insensitive membership node."""

  def Apply(self, value, operand):
    return self.backend.Term(self.backend.Equals(':'), value, operand)


class _ExprEQ(_ExprOperator):
  """Case sensitive EQ node."""

  def Apply(self, value, operand):
    return self.backend.Term(self.backend.Equals('='), value, operand)


class _ExprNE(_ExprOperator):
  """NE node."""

  def Apply(self, value, operand):
    """Returns the rewrite for `value != operand'."""
    return self.backend.InvertUndefinedComparison(
        '!=', self.backend.Equals('='), value, operand)


class _ExprGE(_ExprOperator):
  """GE node."""

  def Apply(self, value, operand):
    return self.backend.Term('>=', value, operand)


class _ExprGT(_ExprOperator):
  """GT node."""

  def Apply(self, value, operand):
    return self.backend.Term('>', value, operand)


class _ExprRE(_ExprOperator):
  """Unanchored RE match node."""

  def Apply(self, value, operand):
    return self.backend.Term('~', value, operand)


class _ExprNotRE(_ExprOperator):
  """Unanchored RE not match node."""

  def Apply(self, value, operand):
    """Returns the rewrite for `value !~ operand'."""
    return self.backend.InvertUndefinedComparison('!~', '~', value, operand)
