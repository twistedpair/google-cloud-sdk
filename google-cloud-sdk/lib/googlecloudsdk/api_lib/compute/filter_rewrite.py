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

"""Compute resource filter expression rewrite backend.

Refer to the core.resource.resource_expr_rewrite docstring for expression
rewrite details.

Cloud SDK filter expressions are One Platform compliant. Compute API
filter expressions have limited functionality and are not compatible with
One Platform. This module rewrites client-side filter expressions to compute
server-side filter expressions. Both the client-side and server-side
expressions must be applied.

Compute API filter expressions have these operators:
  eq
  ne
and these operand types:
  string
  bool
  integer
  float

eq and ne on string operands treat the operand as a regular expression pattern.
Multiple terms can be AND'ed by enclosing adjacent terms in parenthesis.

Explicit AND, OR or NOT operators are not supported.

To use in compute Run(args) methods:

  from googlecloudsdk.api_lib.compute import filter_rewrite
    ...
  args.filter, backend_filter = filter_rewrite.Rewriter().Rewrite(args.filter)
    ...
    filter=backend_filter,
    ...
  )

When compute becomes One Platform compliant this module can be discarded and
the compute code can simply use

  Request(
    ...
    filter=args.filter,
    ...
  )
"""

import re

from googlecloudsdk.core.resource import resource_expr_rewrite


class Rewriter(resource_expr_rewrite.Backend):
  """Compute resource filter expression rewriter backend.

  This rewriter builds a list of tokens that is joined into a string at the
  very end. This makes it easy to apply the NOT and - logical inversion ops.
  """

  _INVERT = {'eq': 'ne', 'ne': 'eq'}

  def Rewrite(self, expression, defaults=None):
    frontend, backend_tokens = super(Rewriter, self).Rewrite(
        expression, defaults=defaults)
    backend = ' '.join(backend_tokens) if backend_tokens else None
    return frontend, backend

  def RewriteNOT(self, expr):
    if expr[0] == '(':
      return None
    expr[1] = self._INVERT[expr[1]]
    return expr

  def RewriteAND(self, left, right):
    return ['('] + left + [')', '('] + right + [')']

  def RewriteTerm(self, key, op, operand):
    """Rewrites <key op operand>."""
    if isinstance(operand, list):
      # foo:(bar,baz) needs OR
      return None

    try:
      float(operand)
      numeric = True
    except ValueError:
      if operand.lower() in ('true', 'false'):
        operand = operand.lower()
        numeric = True
      else:
        numeric = False

    if op == ':':
      op = 'eq'
      if not numeric:
        operand = '".*{operand}.*"'.format(operand=re.escape(operand))
    elif op in ('=', '!='):
      op = 'ne' if op.startswith('!') else 'eq'
      if not numeric:
        operand = '"{operand}"'.format(operand=re.escape(operand))
    elif op in ('~', '!~'):
      # All re match operands are strings.
      op = 'ne' if op.startswith('!') else 'eq'
      operand = '"{operand}"'.format(operand=operand.replace('"', '\\"'))
    else:
      return None

    return [key, op, operand]
