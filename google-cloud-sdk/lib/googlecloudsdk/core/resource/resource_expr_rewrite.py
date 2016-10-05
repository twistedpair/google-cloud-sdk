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

"""Cloud resource filter expression rewrite backend.

It is possible for a rewritten expression to collapse to None. This means that
there is no equivalent server-side expression, i.e., no server-side pruning is
possible.

These rewrites can only prune expressions that will be False client-side.
In this sense a rewrite => None means "the client side will figure it out".
This results in a backend expression that can be applied server-side to prune
the resources passed back to the client-side, where the full filter expression
is applied. The result will be the same whether or not the backend filter is
applied. The only difference would be the number of resources transmitted
from the server back to the client.

None is the value for keys and operators not supported by the backend.
ExprTRUE, ExprAND, ExprOR and ExprNOT do expression rewrites based on None:

  TRUE => None
  None AND x => x
  x AND None => x
  x OR None => None
  None OR x => None
  NOT None => None
"""

from googlecloudsdk.core.resource import resource_lex


class _Expr(object):
  """An expression rewrite object that evaluates to the rewritten expression."""

  def __init__(self, expr):
    self.expr = expr

  def Rewrite(self):
    """Returns the server side string rewrite of the filter expression."""
    return self.expr


class Backend(object):
  """Cloud resource filter expression rewrite backend."""

  def RewriteAND(self, unused_left, unused_right):
    """Rewrites <left AND right>."""
    return None

  def RewriteOR(self, unused_left, unused_right):
    """Rewrites <left OR right>."""
    return None

  def RewriteNOT(self, unused_expr):
    """Rewrites <NOT expr>."""
    return None

  def RewriteGlobal(self, unused_call):
    """Rewrites global restriction <call>."""
    return None

  def RewriteTerm(self, unused_key, unused_op, unused_operand):
    """Rewrites <key op operand>."""
    return None

  @staticmethod
  def Quote(value):
    """Returns value enclosed in '...' if necessary."""
    try:
      return str(int(value))
    except ValueError:
      pass
    try:
      return str(float(value))
    except ValueError:
      pass
    return repr(value)

  def Term(self, key, op, operand, transform, args):
    if transform or args:
      return _Expr(None)
    return _Expr(self.RewriteTerm(resource_lex.GetKeyName(key), op, operand))

  def ExprTRUE(self):
    return _Expr(None)

  def ExprAND(self, left, right):
    # None AND x => x
    if left.Rewrite() is None:
      return right
    # x AND None => x
    if right.Rewrite() is None:
      return left
    return _Expr(self.RewriteAND(left.Rewrite(), right.Rewrite()))

  def ExprOR(self, left, right):
    # None OR x => None
    # x OR None => None
    if left.Rewrite() is None or right.Rewrite() is None:
      return _Expr(None)
    return _Expr(self.RewriteOR(left.Rewrite(), right.Rewrite()))

  def ExprNOT(self, expr):
    if expr.Rewrite() is None:
      return _Expr(None)
    return _Expr(self.RewriteNOT(expr.Rewrite()))

  def ExprGlobal(self, call):
    return _Expr(self.RewriteGlobal(call))

  def ExprOperand(self, value):
    return value

  def ExprLT(self, key, operand, transform=None, args=None):
    return self.Term(key, '<', operand, transform, args)

  def ExprLE(self, key, operand, transform=None, args=None):
    return self.Term(key, '<=', operand, transform, args)

  def ExprHAS(self, key, operand, transform=None, args=None):
    return self.Term(key, ':', operand, transform, args)

  def ExprEQ(self, key, operand, transform=None, args=None):
    return self.Term(key, '=', operand, transform, args)

  def ExprNE(self, key, operand, transform=None, args=None):
    return self.Term(key, '!=', operand, transform, args)

  def ExprGE(self, key, operand, transform=None, args=None):
    return self.Term(key, '>=', operand, transform, args)

  def ExprGT(self, key, operand, transform=None, args=None):
    return self.Term(key, '>', operand, transform, args)

  def ExprRE(self, key, operand, transform=None, args=None):
    return self.Term(key, '~', operand, transform, args)

  def ExprNotRE(self, key, operand, transform=None, args=None):
    return self.Term(key, '!~', operand, transform, args)
