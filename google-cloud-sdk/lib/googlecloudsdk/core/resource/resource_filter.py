# Copyright 2015 Google Inc. All Rights Reserved.

"""Cloud resource list filter expression parser.

Left-factorized BNF Grammar:

  expr        : adjterm adjtail            # gcloud: LF has andterm here

  adjtail     : nil
              | expr

  adjterm     : orterm ortail

  ortail      : nil
              | or adjterm

  orterm      : andterm andtail

  andtail     : nil
              | and orterm

  andterm     : term
              | not term

  term        : key operator operand
              | '-'key operator operand
              | function '(' args ')'
              | '(' expr ')'

  key         : member keytail

  keytail     : nil
              | '.' key
              | '.' function '(' args ')'   # gcloud: LF extension

  member      : name
              | name [ integer ]            # gcloud: LF extension
              | name [ ]                    # gcloud: LF extension

  args        : nil
              | arglist

  arglist     | operand arglisttail

  arglisttail : nil
              | ',' arglist

  and       := 'AND'
  not       := 'NOT'
  or        := 'OR'
  operator  := ':' | '=' | '<' | '<=' | '>=' | '>' | '!=' | '~' | '!~'
  function  := < name in symbol table >
  name      := < resource identifier name >
  operand   := < token terminated by <space> | '(' | ')' | <EndOfInput> >
  integer   := < positive or negative integer >

Example:
  expression = filter-expression-string
  resources = [JSON-serilaizable-object]

  query = resource_filter.Compile(expression)
  for resource in resources:
    if query.Evaluate(resource):
      ProcessMatchedResource(resource)
"""

from googlecloudsdk.core.resource import resource_exceptions
from googlecloudsdk.core.resource import resource_expr
from googlecloudsdk.core.resource import resource_lex


class _Parser(object):
  """List filter expression parser.

  A filter expression is compiled by passing the expression string to the
  Parser(), which calls the Backend() code generator to produce an Evaluate()
  method. The default resource_expr.Backend() generates a Boolean
  Evaluate(resource) that returns True if resource matches the filter
  expression. Other backends may generate an Evaluate(None) that rewrites the
  filter expression to a different syntax, for example, to convert a filter
  expression to a server-side expression in the server API filtering syntax.

  Attributes:
    _LOGICAL: List of logical operator names.
    _backend: The expression tree generator module.
    _lex: The resource_lex.Lexer filter expression lexer.
    _operator: Dictionary of all search term operators.
    _operator_char_1: The first char of all search term operators.
    _operator_char_2: The second char of all search term operators.
    _parenthesize: A LIFO stack of _OP_* sets for each (...) level. Used to
      determine when AND and OR are combined in the same parenthesis group.
    _symbols: Filter function symbol table dict indexed by function name.
  """
  _OP_AND, _OP_OR = range(2)

  _LOGICAL = ['AND', 'NOT', 'OR']

  def __init__(self, symbols=None, backend=None):
    self._symbols = {}
    if symbols:
      self._symbols.update(symbols)
    self._backend = backend or resource_expr.Backend()
    self._operator_char_1 = ''
    self._operator_char_2 = ''
    self._operator = {
        ':': self._backend.ExprHAS, '=': self._backend.ExprEQ,
        '!=': self._backend.ExprNE, '<': self._backend.ExprLT,
        '<=': self._backend.ExprLE, '>=': self._backend.ExprGE,
        '>': self._backend.ExprGT, '~': self._backend.ExprRE,
        '!~': self._backend.ExprNotRE}
    # Operator names are length 1 or 2. This loop precomputes _operator_char_1
    # and _operator_char_2 for _ParseOperator to determine both valid and
    # invalid operator names.
    for operator in self._operator:
      c = operator[0]
      if c not in self._operator_char_1:
        self._operator_char_1 += c
      if len(operator) < 2:
        continue
      c = operator[1]
      if c not in self._operator_char_2:
        self._operator_char_2 += c
    self._lex = None
    self._parenthesize = [set()]

  def _CheckParenthesization(self, op):
    """Checks that AND and OR do not appear in the same parenthesis group.

    This method is called each time an AND or OR operator is seen in an
    expression. self._parenthesize[] keeps track of AND and OR operators seen in
    the nested parenthesis groups. ExpressionSyntaxError is raised if both AND
    and OR appear in the same parenthesis group. The top expression with no
    parentheses is considered a parenthesis group.

    The One-Platform list filter spec on which this parser is based has an
    unconventional OR higher than AND logical operator precedence. Allowing that
    in the Cloud SDK would lead to user confusion and many bug reports. To avoid
    that and still be true to the spec this method forces expressions containing
    AND and OR combinations to be fully parenthesized so that the desired
    precedence is explicit and unambiguous.

    Args:
      op: self._OP_AND or self._OP_OR.

    Raises:
      ExpressionSyntaxError: AND and OR appear in the same parenthesis group.
    """
    self._parenthesize[-1].add(op)
    if len(self._parenthesize[-1]) > 1:
      raise resource_exceptions.ExpressionSyntaxError(
          'Parenthesis grouping is required when AND and OR are '
          'are combined [{0}].'.format(self._lex.Annotate()))

  def _ParseKey(self):
    """Parses a key with optional trailing transform.

    Raises:
      ExpressionSyntaxError: Missing term, unknown transform function.

    Returns:
      (key, transform, args):
        key: The key expression, None means transform is a global restriction.
        transform: A transform function if not None. If key is None then the
          transform is a global restriction.
        args: The transform actual args, None if transform is None or of there
          are no args.
    """
    here = self._lex.GetPosition()
    key = self._lex.Key()
    if key and key[0] in self._LOGICAL:
      raise resource_exceptions.ExpressionSyntaxError(
          'Term expected [{0}].'.format(self._lex.Annotate(here)))
    if not self._lex.IsCharacter('(', eoi_ok=True):
      return key, None, None

    # A global restriction function or key transform.
    args = self._lex.Args(convert=True)
    name = key.pop()
    if name not in self._symbols:
      # Symbol table lookup could be delayed until evaluation time, but
      # catching errors early on is good practice in the Cloud SDK. Otherwise:
      # - a filter expression applied client-side could fetch part or all of
      #   a server resource before failing
      # - a filter expression applied server-side would add another
      #   client-server failure case to handle
      # Doing the symbol table lookup here makes the return value of Compile()
      # a hermetic unit. This will make it easier to:
      # - apply optimizations based on function semantics
      # - apply client-side vs server-side expression splitting
      raise resource_exceptions.ExpressionSyntaxError(
          'Unknown transform function [{0}].'.format(self._lex.Annotate(here)))
    return key, self._symbols[name], args

  def _ParseOperator(self):
    """Parses an operator token.

    All operators match the RE [_operator_char_1][_operator_char_2]. Invalid
    operators are 2 character sequences that are not valid operators and
    match the RE [_operator_char_1][_operator_char_1+_operator_char_2].

    Raises:
      ExpressionSyntaxError: The operator spelling is malformed.

    Returns:
      The operator backend expression, None if the next token is not an
      operator.
    """
    if not self._lex.SkipSpace():
      return None
    here = self._lex.GetPosition()
    op = self._lex.IsCharacter(self._operator_char_1)
    if not op:
      return None
    if not self._lex.EndOfInput():
      o2 = self._lex.IsCharacter(self._operator_char_1 + self._operator_char_2)
      if o2:
        op += o2
    if op not in self._operator:
      raise resource_exceptions.ExpressionSyntaxError(
          'Malformed operator [{0}].'.format(self._lex.Annotate(here)))
    self._lex.SkipSpace(token='Term operand')
    return self._operator[op]

  def _ParseTerm(self, must=False):
    """Parses a [-]<key> <operator> <operand> term.

    Args:
      must: Raises ExpressionSyntaxError if must is True and there is no
        expression.

    Raises:
      ExpressionSyntaxError: The expression has a syntax error.

    Returns:
      The new backend expression tree.
    """
    here = self._lex.GetPosition()
    if not self._lex.SkipSpace():
      if must:
        raise resource_exceptions.ExpressionSyntaxError(
            'Term expected [{0}].'.format(self._lex.Annotate(here)))
      return None

    # Check for end of (...) term.
    if self._lex.IsCharacter(')', peek=True):
      # The caller will determine if this ends (...) or is a syntax error.
      return None

    # Check for start of (...) term.
    if self._lex.IsCharacter('('):
      self._parenthesize.append(set())
      tree = self._ParseExpr()
      # Either the next char is ')' or we hit an end of expression syntax error.
      self._lex.IsCharacter(')')
      self._parenthesize.pop()
      return tree

    # Check for term inversion.
    invert = self._lex.IsCharacter('-')

    # Parse the key.
    key, transform, args = self._ParseKey()

    # Parse the operator.
    here = self._lex.GetPosition()
    operator = self._ParseOperator()
    if not operator:
      if transform and not key:
        # A global restriction function.
        tree = self._backend.ExprGlobal(transform, args)
      elif len(key) == 1:
        # A global restriction on key[0].
        transform = self._symbols.get('global', None)
        if not transform:
          raise resource_exceptions.ExpressionSyntaxError(
              'Global restriction not supported [{0}].'.format(
                  self._lex.Annotate(here)))
        tree = self._backend.ExprGlobal(transform, key)
      else:
        raise resource_exceptions.ExpressionSyntaxError(
            'Operator expected [{0}].'.format(self._lex.Annotate(here)))
      if invert:
        tree = self._backend.ExprNOT(tree)
      return tree

    # Parse the operand.
    self._lex.SkipSpace(token='Operand')
    here = self._lex.GetPosition()
    if any([self._lex.IsString(x) for x in self._LOGICAL]):
      raise resource_exceptions.ExpressionSyntaxError(
          'Logical operator not expected [{0}].'.format(
              self._lex.Annotate(here)))
    operand = self._lex.Token('()')
    if operand is None:
      raise resource_exceptions.ExpressionSyntaxError(
          'Term operand expected [{0}].'.format(self._lex.Annotate(here)))

    # Make an Expr node for the term.
    tree = operator(key=key, operand=self._backend.ExprOperand(operand),
                    transform=transform, args=args)
    if invert:
      tree = self._backend.ExprNOT(tree)
    return tree

  def _ParseAndTerm(self, must=False):
    """Parses an andterm term.

    Args:
      must: Raises ExpressionSyntaxError if must is True and there is no
        expression.

    Returns:
      The new backend expression tree.
    """
    if self._lex.IsString('NOT'):
      return self._backend.ExprNOT(self._ParseTerm(must=True))
    return self._ParseTerm(must=must)

  def _ParseAndTail(self, tree):
    """Parses an andtail term.

    Args:
      tree: The backend expression tree.

    Returns:
      The new backend expression tree.
    """
    if self._lex.IsString('AND'):
      self._CheckParenthesization(self._OP_AND)
      tree = self._backend.ExprAND(tree, self._ParseOrTerm(must=True))
    return tree

  def _ParseOrTerm(self, must=False):
    """Parses an orterm term.

    Args:
      must: Raises ExpressionSyntaxError if must is True and there is no
        expression.

    Raises:
      ExpressionSyntaxError: Term expected in expression.

    Returns:
      The new backend expression tree.
    """
    tree = self._ParseAndTerm()
    if tree:
      tree = self._ParseAndTail(tree)
    elif must:
      raise resource_exceptions.ExpressionSyntaxError(
          'Term expected [{0}].'.format(self._lex.Annotate()))
    return tree

  def _ParseOrTail(self, tree):
    """Parses an ortail term.

    Args:
      tree: The backend expression tree.

    Returns:
      The new backend expression tree.
    """
    if self._lex.IsString('OR'):
      self._CheckParenthesization(self._OP_OR)
      tree = self._backend.ExprOR(tree, self._ParseAdjTerm(must=True))
    return tree

  def _ParseAdjTerm(self, must=False):
    """Parses an adjterm term.

    Args:
      must: ExpressionSyntaxError if must is True and there is no expression.

    Raises:
      ExpressionSyntaxError: Term expected in expression.

    Returns:
      The new backend expression tree.
    """
    tree = self._ParseOrTerm()
    if tree:
      tree = self._ParseOrTail(tree)
    elif must:
      raise resource_exceptions.ExpressionSyntaxError(
          'Term expected [{0}].'.format(self._lex.Annotate()))
    return tree

  def _ParseAdjTail(self, tree):
    """Parses an adjtail term.

    Args:
      tree: The backend expression tree.

    Returns:
      The new backend expression tree.
    """
    if (not self._lex.IsString('AND', peek=True) and
        not self._lex.IsString('OR', peek=True) and
        not self._lex.IsCharacter(')', peek=True) and
        not self._lex.EndOfInput()):
      tree = self._backend.ExprAND(tree, self._ParseExpr(must=True))
    return tree

  def _ParseExpr(self, must=False):
    """Parses an expr term.

    Args:
      must: ExpressionSyntaxError if must is True and there is no expression.

    Raises:
      ExpressionSyntaxError: The expression has a syntax error.

    Returns:
      The new backend expression tree.
    """
    tree = self._ParseAdjTerm()
    if tree:
      tree = self._ParseAdjTail(tree)
    elif must:
      raise resource_exceptions.ExpressionSyntaxError(
          'Term expected [{0}].'.format(self._lex.Annotate()))
    return tree

  def Parse(self, expression, aliases=None):
    """Parses a resource list filter expression.

    This is a hand-rolled recursive descent parser based directly on the
    left-factorized BNF grammar in the file docstring. The parser is not thread
    safe. Each thread should use distinct _Parser objects.

    Args:
      expression: A resource list filter expression string.
      aliases: Resource key alias dictionary.

    Raises:
      ExpressionSyntaxError: The expression has a syntax error.

    Returns:
      tree: The backend expression tree.
    """
    self._lex = resource_lex.Lexer(expression, aliases=aliases)
    tree = self._ParseExpr()
    if not self._lex.EndOfInput():
      raise resource_exceptions.ExpressionSyntaxError(
          'Unexpected tokens [{0}] in expression.'.format(self._lex.Annotate()))
    self._lex = None
    return tree or self._backend.ExprTRUE()


def Compile(expression, symbols=None, aliases=None, defaults=None,
            backend=None):
  """Compiles a resource list filter expression.

  Args:
    expression: A resource list filter expression string.
    symbols: Filter function symbol table dict indexed by function name.
    aliases: Resource key alias dictionary.
    defaults: Resource projection defaults (for default symbols and aliases).
    backend: The backend expression tree generator module, resource_expr
      if None.

  Returns:
    A backend expression tree.

  Example:
    query = resource_filter.Compile(expression)
    for resource in resources:
      if query.Evaluate(resource):
        ProcessMatchedResource(resource)
  """
  all_symbols = {}
  all_aliases = {}
  if defaults:
    if defaults.symbols:
      all_symbols.update(defaults.symbols)
    if defaults.aliases:
      all_aliases.update(defaults.aliases)
  if symbols:
    all_symbols.update(symbols)
  if aliases:
    all_aliases.update(aliases)
  return _Parser(symbols=all_symbols,
                 backend=backend).Parse(expression, aliases=all_aliases)
