# Copyright 2015 Google Inc. All Rights Reserved.

"""A class for parsing a resource projection expression."""

import re

from googlecloudsdk.core.resource import resource_exceptions
from googlecloudsdk.core.resource import resource_lex
from googlecloudsdk.core.resource import resource_projection_spec
from googlecloudsdk.third_party.py27 import py27_copy as copy


class Parser(object):
  """Resource projection expression parser.

  A projection is an expression string that contains a list of resource keys
  with optional attributes. This class parses a projection expression into
  resource key attributes and a tree data structure that is used by a projector.

  A projector is a method that takes a JSON-serializable object and a
  projection as input and produces a new JSON-serializable object containing
  only the values corresponding to the keys in the projection. Optional
  projection key attributes may transform the values in the resulting
  JSON-serializable object.

  In the Cloud SDK projection attributes are used for output formatting.

  A default or empty projection expression still produces a projector that
  converts a resource to a JSON-serializable object.

  Attributes:
    __key_attributes_only: Parse projection key list for attributes only.
    _ordinal: The projection key ordinal counting from 1.
    _projection: The resource_projection_spec.ProjectionSpec to parse into.
    _root: The projection _Tree tree root node.
    _snake_headings: Dict used to disambiguate key attribute labels.
    _snake_re: Compiled re for converting key names to angry snake case.
  """

  _BOOLEAN_ATTRIBUTES = ['reverse']

  def __init__(self, defaults=None, symbols=None):
    """Constructor.

    Args:
      defaults: resource_projection_spec.ProjectionSpec defaults.
      symbols: Transform function symbol table dict indexed by function name.
    """
    self.__key_attributes_only = False
    self._ordinal = 0
    self._projection = resource_projection_spec.ProjectionSpec(
        defaults=defaults, symbols=symbols)
    self._snake_headings = {}
    self._snake_re = None

    # pylint: disable=g-import-not-at-top, cycle via resource_projector.Compile
    from googlecloudsdk.core.resource import resource_transform

    self._builtin_transforms = resource_transform

  class _Tree(object):
    """Defines a Projection tree node.

    Attributes:
      tree: Projection _Tree node indexed by key path.
      attribute: Key _Attribute.
    """

    def __init__(self, attribute):
      self.tree = {}
      self.attribute = attribute

  class _Attribute(object):
    """Defines a projection key attribute.

    Attribute semantics, except transform, are caller defined.  e.g., the table
    formatter uses the label attribute for the column heading for the key.

    Attributes:
      flag: The projection algorithm flag, one of DEFAULT, INNER, PROJECT.
      ordinal: The left-to-right column order counting from 1.
      order: The column sort order, None if not ordered. Lower values have
        higher sort precedence.
      label: A string associated with each projection key.
      reverse: Reverse column sort if True.
      align: The column alignment name: left, center, or right.
      transform: obj = func(obj,...) function applied during projection.
    """

    def __init__(self, flag):
      self.flag = flag
      self.ordinal = None
      self.order = None
      self.label = None
      self.reverse = None
      self.align = resource_projection_spec.ALIGN_DEFAULT
      self.transform = []

    def __str__(self):
      return (
          '({flag}, {ordinal}, {order}, {label}, {align}, {active},'
          ' {transform})'.format(
              flag=self.flag,
              ordinal=('DEFAULT' if self.ordinal is None
                       else str(self.ordinal)),
              order=('UNORDERED' if self.order is None else str(self.order)),
              label=repr(self.label),
              align=self.align,
              active=self.transform[0].active if self.transform else None,
              transform='[{0}]'.format('.'.join(map(str, self.transform)))))

  class _Transform(object):
    """A key transform function with actual args.

    Attributes:
      name: The transform function name.
      func: The transform function.
      active: The parent projection active level. A transform is active if
        transform.active is None or equal to the current projection.active.
      map_transform: If r is a list then apply the transform to each list item.
      args: List of function call actual arg strings.
      kwargs: List of function call actual keyword arg strings.
    """

    def __init__(self, name, func, active, map_transform, args, kwargs):
      self.name = name
      self.func = func
      self.active = active
      self.map_transform = map_transform
      self.args = args
      self.kwargs = kwargs

    def __str__(self):
      return '{0}{1}({2})'.format('map().' if self.map_transform else '',
                                  self.name, ','.join(self.args))

  def _AngrySnakeCase(self, key):
    """Returns an ANGRY_SNAKE_CASE string representation of a parsed key.

    Args:
        key: A parsed resource key.

    Returns:
      The ANGRY_SNAKE_CASE string representation of key, adding components
        from right to left to disambiguate from previous ANGRY_SNAKE_CASE
        strings.
    """
    if self._snake_re is None:
      self._snake_re = re.compile('((?<=[a-z0-9])[A-Z]+|(?!^)[A-Z](?=[a-z]))')
    label = ''
    for index in reversed(key):
      if isinstance(index, str):
        key_snake = self._snake_re.sub(r'_\1', index).upper()
        if label:
          label = key_snake + '_' + label
        else:
          label = key_snake
        if label not in self._snake_headings:
          self._snake_headings[label] = 1
          break
    return label

  def _AddKey(self, key, attribute_add):
    """Propagates default attribute values and adds key to the projection.

    Args:
      key: The parsed key to add.
      attribute_add: Parsed _Attribute to add.
    """
    projection = self._root

    # Add or update the inner nodes.
    for name in key[:-1]:
      tree = projection.tree
      if name in tree:
        attribute = tree[name].attribute
        if attribute.flag != self._projection.PROJECT:
          attribute.flag = self._projection.INNER
      else:
        tree[name] = self._Tree(self._Attribute(self._projection.INNER))
      projection = tree[name]

    # Add or update the terminal node.
    tree = projection.tree
    # self.key == [] => a function on the entire object.
    name = key[-1] if key else ''
    name_in_tree = name in tree
    if name_in_tree:
      # Already added.
      attribute = tree[name].attribute
    elif isinstance(name, (int, long)) and None in tree:
      # New projection for explicit name using slice defaults.
      tree[name] = copy.deepcopy(tree[None])
      attribute = tree[name].attribute
    else:
      # New projection.
      attribute = attribute_add
      tree[name] = self._Tree(attribute)

    # Propagate non-default values from attribute_add to attribute.
    if attribute_add.order is not None:
      attribute.order = attribute_add.order
    if attribute_add.label is not None:
      attribute.label = attribute_add.label
    elif attribute.label is None:
      attribute.label = self._AngrySnakeCase(key)
    if attribute_add.align != resource_projection_spec.ALIGN_DEFAULT:
      attribute.align = attribute_add.align
    if attribute_add.reverse is not None:
      attribute.reverse = attribute_add.reverse
    elif attribute.reverse is None:
      attribute.reverse = False
    if attribute_add.transform:
      attribute.transform = attribute_add.transform
    self._projection.AddAlias(attribute.label, key)

    if not self.__key_attributes_only:
      # This key is in the projection.
      attribute.flag = self._projection.PROJECT
      self._ordinal += 1
      attribute.ordinal = self._ordinal
      self._projection.AddKey(key, attribute)
    elif not name_in_tree:
      # This is a new attributes only key.
      attribute.flag = self._projection.DEFAULT

  def _ParseTransform(self, func_name, active, map_transform):
    """Parses a transform function call.

    Args:
      func_name: The transform function name.
      active: The transform active level or None if always active.
      map_transform: Apply the transform to each resource list item.

    Returns:
      A _Transform call item. The caller appends these to a list that is used
      to apply the transform functions.

    Raises:
      ExpressionSyntaxError: The expression has a syntax error.
    """
    here = self._lex.GetPosition()
    if (not self._projection.symbols or
        func_name not in self._projection.symbols):
      raise resource_exceptions.ExpressionSyntaxError(
          'Unknown transform function {0} [{1}].'.format(
              func_name, self._lex.Annotate(here)))
    kwargs = {}
    func = self._projection.symbols[func_name]
    if func == self._builtin_transforms.TransformFormat:
      args = [self._projection] + self._lex.Args()
    else:
      args = []
      for arg in self._lex.Args():
        name, sep, val = arg.partition('=')
        if sep:
          kwargs[name] = val
        else:
          args.append(arg)
    return self._Transform(func_name, func, active, map_transform, args, kwargs)

  def _ParseKeyAttributes(self, key, attribute):
    """Parses one or more key attributes and adds them to attribute.

    The initial ':' has been consumed by the caller.

    Args:
      key: The parsed key name of the attributes.
      attribute: Add the parsed transform to this resource_projector._Attribute.

    Raises:
      ExpressionSyntaxError: The expression has a syntax error.
    """
    while True:
      name = self._lex.Token('=:,)', space=False)
      here = self._lex.GetPosition()
      if self._lex.IsCharacter('=', eoi_ok=True):
        boolean_value = False
        value = self._lex.Token(':,)', space=False, convert=True)
      else:
        boolean_value = True
        if name.startswith('no-'):
          name = name[3:]
          value = False
        else:
          value = True
      if name in self._BOOLEAN_ATTRIBUTES:
        if not boolean_value:
          # A Boolean attribute with a non-Boolean value.
          raise resource_exceptions.ExpressionSyntaxError(
              'value not expected [{0}].'.format(self._lex.Annotate(here)))
      elif boolean_value:
        # A non-Boolean attribute without a value or a no- prefix.
        raise resource_exceptions.ExpressionSyntaxError(
            'value expected [{0}].'.format(self._lex.Annotate(here)))
      if name == 'alias':
        if not value:
          raise resource_exceptions.ExpressionSyntaxError(
              'Cannot unset alias [{0}].'.format(self._lex.Annotate(here)))
        self._projection.AddAlias(value, key)
      elif name == 'align':
        if value not in resource_projection_spec.ALIGNMENTS:
          raise resource_exceptions.ExpressionSyntaxError(
              'Unknown alignment [{0}].'.format(self._lex.Annotate(here)))
        attribute.align = value
      elif name == 'label':
        attribute.label = value or ''
      elif name == 'reverse':
        attribute.reverse = value
      elif name == 'sort':
        attribute.order = value
      else:
        raise resource_exceptions.ExpressionSyntaxError(
            'Unknown key attribute [{0}].'.format(self._lex.Annotate(here)))
      if not self._lex.IsCharacter(':'):
        break

  def _ParseKey(self):
    """Parses a key and optional attributes from the expression.

    Transform functions and key attributes are also handled here.

    Raises:
      ExpressionSyntaxError: The expression has a syntax error.

    Returns:
      The parsed key.
    """
    key = self._lex.Key()
    here = self._lex.GetPosition()
    attribute = self._Attribute(self._projection.PROJECT)
    if self._lex.IsCharacter('(', eoi_ok=True):
      func_name = key.pop()
      active = self._projection.active
      map_transform = False
      while True:
        transform = self._ParseTransform(func_name, active, map_transform)
        if transform.func == self._builtin_transforms.TransformAlways:
          active = None  # Always active.
          func_name = None
        elif transform.func == self._builtin_transforms.TransformMap:
          map_transform = True
          func_name = None
        else:
          # always() applies to all transforms for key.
          # map() applies to the next transform.
          map_transform = False
          attribute.transform.append(transform)
        if not self._lex.IsCharacter('.', eoi_ok=True):
          break
        call = self._lex.Key()
        here = self._lex.GetPosition()
        if not self._lex.IsCharacter('('):
          raise resource_exceptions.ExpressionSyntaxError(
              'Transform function expected [{0}].'.format(
                  self._lex.Annotate(here)))
        if len(call) != 1:
          raise resource_exceptions.ExpressionSyntaxError(
              'Unknown transform function {0} [{1}].'.format(
                  '.'.join(call), self._lex.Annotate(here)))
        func_name = call.pop()
    else:
      func_name = None
    self._lex.SkipSpace()
    if self._lex.IsCharacter(':'):
      self._ParseKeyAttributes(key, attribute)
    if func_name and attribute.label is None and not key:
      attribute.label = self._AngrySnakeCase([func_name])
    self._AddKey(key, attribute)

  def _ParseKeys(self):
    """Parses a comma separated list of keys.

    The initial '(' has already been consumed by the caller.

    Raises:
      ExpressionSyntaxError: The expression has a syntax error.
    """
    if self._lex.IsCharacter(')'):
      # An empty projection is OK.
      return
    while True:
      self._ParseKey()
      self._lex.SkipSpace()
      if self._lex.IsCharacter(')'):
        break
      if not self._lex.IsCharacter(','):
        raise resource_exceptions.ExpressionSyntaxError(
            'Expected ) in projection expression [{0}].'.format(
                self._lex.Annotate()))

  def _ParseAttributes(self):
    """Parses a comma separated [no-]name[=value] projection attribute list.

    The initial '[' has already been consumed by the caller.

    Raises:
      ExpressionSyntaxError: The expression has a syntax error.
    """
    while True:
      name = self._lex.Token('=,])', space=False)
      if name:
        if self._lex.IsCharacter('='):
          value = self._lex.Token(',])', space=False, convert=True)
        else:
          value = 1
        self._projection.AddAttribute(name, value)
        if name.startswith('no-'):
          self._projection.DelAttribute(name[3:])
        else:
          self._projection.DelAttribute('no-' + name)
      if self._lex.IsCharacter(']'):
        break
      if not self._lex.IsCharacter(','):
        raise resource_exceptions.ExpressionSyntaxError(
            'Expected ] in attribute list [{0}].'.format(self._lex.Annotate()))

  def Parse(self, expression=None):
    """Parse a projection expression.

    An empty projection is OK.

    Args:
      expression: The resource projection expression string.

    Raises:
      ExpressionSyntaxError: The expression has a syntax error.

    Returns:
      A ProjectionSpec for the expression.
    """
    self._root = self._projection.GetRoot()
    if not self._root:
      self._root = self._Tree(self._Attribute(self._projection.DEFAULT))
      self._projection.SetRoot(self._root)
    self._projection.SetEmpty(
        self._Tree(self._Attribute(self._projection.PROJECT)))
    if expression:
      self._lex = resource_lex.Lexer(expression,
                                     aliases=self._projection.aliases)
      defaults = False
      self.__key_attributes_only = False
      while self._lex.SkipSpace():
        if self._lex.IsCharacter('('):
          if not self.__key_attributes_only:
            defaults = False
            self._projection.Defaults()
            self._ordinal = 0
          self._ParseKeys()
        elif self._lex.IsCharacter('['):
          self._ParseAttributes()
        elif self._lex.IsCharacter(':'):
          self.__key_attributes_only = True
        else:
          self.__key_attributes_only = False
          here = self._lex.GetPosition()
          name = self._lex.Token(':([')
          if not name.isalpha():
            raise resource_exceptions.ExpressionSyntaxError(
                'Name expected [{0}].'.format(self._lex.Annotate(here)))
          self._projection.SetName(name)
          defaults = True
      self._lex = None
      if defaults:
        self._projection.Defaults()
    return self._projection


def Parse(expression, defaults=None, symbols=None):
  """Parses a resource projector expression.

  Args:
    expression: The resource projection expression string.
    defaults: resource_projection_spec.ProjectionSpec defaults.
    symbols: Transform function symbol table dict indexed by function name.

  Returns:
    A ProjectionSpec for the expression.
  """
  return Parser(defaults=defaults, symbols=symbols).Parse(expression)
