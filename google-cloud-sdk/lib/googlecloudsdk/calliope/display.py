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
"""Resource display for all calliope commands.

The print_format string passed to resource_printer.Print() is determined in this
order:
 (1) Display disabled and resources not consumed if user output is disabled.
 (2) The explicit --format flag format string.
 (3) The explicit Display() method.
 (4) The Format() string.
 (5) Otherwise no output but the resources are consumed.

Format expressions are left-to-right composable. Each format expression is a
string tuple

  < NAME [ATTRIBUTE...] (PROJECTION...) >

where only one of the three elements need be present.
"""

from googlecloudsdk.calliope import display_taps
from googlecloudsdk.core import log
from googlecloudsdk.core.resource import resource_filter
from googlecloudsdk.core.resource import resource_keys_expr
from googlecloudsdk.core.resource import resource_lex
from googlecloudsdk.core.resource import resource_printer
from googlecloudsdk.core.resource import resource_projection_parser
from googlecloudsdk.core.resource import resource_transform
from googlecloudsdk.core.util import peek_iterable


class Displayer(object):
  """Implements the resource display method.

  Dispatches the global flags args by constructing a format string and letting
  resource_printer.Print() do the heavy lifting.

  Attributes:
    _args: The argparse.Namespace given to command.Run().
    _command: The Command object that generated the resources to display.
    _defaults: The resource format and filter default projection.
    _format: The printer format string.
    _info: The resource info or None if not registered.
    _printer: The printer object.
    _printer_is_initialized: True if self._printer has been initialized.
    _resources: The resources to display, returned by command.Run().
    _transform_uri: A transform function that returns the URI for a resource.
  """

  # A command with these flags might return incomplete resource lists.
  _CORRUPT_FLAGS = ('async', 'filter', 'limit')

  def __init__(self, command, args, resources=None):
    """Constructor.

    Args:
      command: The Command object.
      args: The argparse.Namespace given to the command.Run().
      resources: The resources to display, returned by command.Run(). May be
        omitted if only GetFormat() will be called.
    """
    self._args = args
    self._command = command
    self._default_format_used = False
    self._defaults = None
    self._format = None
    self._info = command.ResourceInfo(args)
    self._printer = None
    self._printer_is_initialized = False
    self._resources = resources
    self._defaults = resource_projection_parser.Parse(
        None, defaults=command.Defaults())
    self._defaults.symbols[
        resource_transform.GetTypeDataName('conditionals')] = args
    if self._info:
      self._defaults.symbols['collection'] = (
          lambda r, undefined='': self._info.collection or undefined)
    geturi = command.GetUriFunc()
    if geturi:
      self._transform_uri = lambda r, undefined='': geturi(r) or undefined
      self._defaults.symbols['uri'] = self._transform_uri
    else:
      self._transform_uri = resource_transform.TransformUri

  def _GetFlag(self, flag_name):
    """Returns the value of flag_name in args, None if it is unknown or unset.

    Args:
      flag_name: The flag name string sans leading '--'.

    Returns:
      The flag value or None if it is unknown or unset.
    """
    return getattr(self._args, flag_name, None)

  def _AddUriCacheTap(self):
    """Taps a resource Uri cache updater into self.resources if needed."""

    if not self._info or self._info.bypass_cache:
      return

    cache_update_op = self._command.GetUriCacheUpdateOp()
    if not cache_update_op:
      return

    if any([self._GetFlag(flag) for flag in self._CORRUPT_FLAGS]):
      return

    tap = display_taps.UriCacher(cache_update_op, self._transform_uri)
    self._resources = peek_iterable.Tapper(self._resources, tap)

  def _AddFilterTap(self):
    """Taps a resource filter into self.resources if needed."""
    expression = self._GetFlag('filter')
    if not expression:
      return
    tap = display_taps.Filterer(expression, self._defaults)
    self._resources = peek_iterable.Tapper(self._resources, tap)

  def _AddFlattenTap(self):
    """Taps one or more resource flatteners into self.resources if needed."""
    keys = self._GetFlag('flatten')
    if not keys:
      return
    for key in keys:
      flattened_key = []
      for k in resource_lex.Lexer(key).Key():
        if k is None:
          # None represents a [] slice in resource keys.
          tap = display_taps.Flattener(flattened_key)
          # Apply the flatteners from left to right so the innermost flattener
          # flattens the leftmost slice. The outer flatteners can then access
          # the flattened keys to the left.
          self._resources = peek_iterable.Tapper(self._resources, tap)
        else:
          flattened_key.append(k)

  def _AddLimitTap(self):
    """Taps a resource limit into self.resources if needed."""
    limit = self._GetFlag('limit')
    if limit is None or limit < 0:
      return
    tap = display_taps.Limiter(limit)
    self._resources = peek_iterable.Tapper(self._resources, tap)

  def _AddPageTap(self):
    """Taps a resource pager into self.resources if needed."""
    page_size = self._GetFlag('page_size')
    if page_size is None or page_size <= 0:
      return
    tap = display_taps.Pager(page_size)
    self._resources = peek_iterable.Tapper(self._resources, tap)

  def _AddUriReplaceTap(self):
    """Taps a resource Uri replacer into self.resources if needed."""

    if not self._GetFlag('uri'):
      return

    tap = display_taps.UriReplacer(self._transform_uri)
    self._resources = peek_iterable.Tapper(self._resources, tap)

  def _GetResourceInfoDefaults(self):
    """Returns the default symbols for --filter and --format."""
    if not self._info:
      return self._defaults
    symbols = self._info.GetTransforms()
    if not symbols and not self._info.defaults:
      return self._defaults
    return resource_projection_parser.Parse(
        self._info.defaults, defaults=self._defaults, symbols=symbols)

  def _GetExplicitFormat(self):
    """Determines the explicit format.

    Returns:
      format: The format string, '' if there is no explicit format, or None
    """
    return self._args.format or ''

  def _GetDefaultFormat(self):
    """Determines the default format.

    Returns:
      format: The format string, '' if there is an explicit Display().
    """
    if hasattr(self._command, 'Display'):
      return ''
    return self._command.Format(self._args)

  def GetFormat(self):
    """Determines the display format.

    Returns:
      format: The display format string.
    """
    default_fmt = self._GetDefaultFormat()
    fmt = self._GetExplicitFormat()

    if not fmt:
      # No explicit format.
      if self._GetFlag('uri'):
        return 'value(.)'
      # Use the default format.
      self._default_format_used = True
      fmt = default_fmt
    elif default_fmt:
      # Compose the default and explicit formats.
      #
      # The rightmost format in fmt takes precedence. Appending gives higher
      # precendence to the explicit format over the default format. Appending
      # also makes projection attributes from preceding projections available
      # to subsequent projections. For example, a user specified explicit
      # --format expression can use the column heading names instead of resource
      # key names:
      #
      #   table(foo.bar:label=NICE, state:STATUS) table(NICE, STATUS)
      #
      # or a --filter='s:DONE' expression can use alias named defined by the
      # defaults:
      #
      #   table(foo.bar:alias=b, state:alias=s)
      #
      fmt = default_fmt + ' ' + fmt

    if fmt and self._GetFlag('sort_by'):
      # :(...) adds key only attributes that don't affect the projection.
      names = (self._args.sort_by if isinstance(self._args.sort_by, list)
               else [self._args.sort_by])
      reverse = False
      orders = []
      for order, name in enumerate(names):
        if name.startswith('~'):
          name = name.lstrip('~')
          if not order:
            reverse = True
        # Slices default to the first list element for consistency.
        name = name.replace('[]', '[0]')
        orders.append('{name}:sort={order}{reverse}'.format(
            name=name, order=order + 1, reverse=':reverse' if reverse else ''))
      fmt += ':({orders})'.format(orders=','.join(orders))

    return fmt

  def _InitPrinter(self):
    """Initializes the printer and associated attributes."""

    if self._printer_is_initialized:
      return
    self._printer_is_initialized = True

    # Determine the format.
    self._format = self.GetFormat()

    # Initialize the default symbols.
    self._defaults = self._GetResourceInfoDefaults()

    # Instantiate a printer if output is enabled.
    if self._format:
      self._printer = resource_printer.Printer(
          self._format, defaults=self._defaults, out=log.out)
      if self._printer:
        self._defaults = self._printer.column_attributes

  def GetReferencedKeyNames(self):
    """Returns the list of key names referenced by the command."""

    keys = set()

    # Add the format key references.
    self._InitPrinter()
    if self._printer:
      for col in self._printer.column_attributes.Columns():
        keys.add(resource_lex.GetKeyName(col.key))

    # Add the filter key references.
    filter_expression = self._GetFlag('filter')
    if filter_expression:
      expr = resource_filter.Compile(filter_expression,
                                     defaults=self._defaults,
                                     backend=resource_keys_expr.Backend())
      for key in expr.Evaluate(None):
        keys.add(resource_lex.GetKeyName(key))

    return keys

  def Display(self):
    """The default display method."""

    if not log.IsUserOutputEnabled():
      log.info('Display disabled.')
      # NOTICE: Do not consume resources here. Some commands use this case to
      # access the results of Run() via the return value of Execute().
      return self._resources

    # Initialize the printer.
    self._InitPrinter()

    # Add a URI cache update tap if needed.
    self._AddUriCacheTap()

    # Add a resource page tap if needed.
    self._AddPageTap()

    # Add a resource flatten tap if needed.
    self._AddFlattenTap()

    # Add a resource filter tap if needed.
    self._AddFilterTap()

    # Add a resource limit tap if needed.
    self._AddLimitTap()

    # Add the URI replace tap if needed.
    self._AddUriReplaceTap()

    resources_were_displayed = True
    if self._printer:
      # Most command output will end up here.
      log.info('Display format "%s".', self._format)
      self._printer.Print(self._resources)
      resources_were_displayed = self._printer.ResourcesWerePrinted()
    elif hasattr(self._command, 'Display'):
      # This will eventually be rare.
      log.info('Explicit Display.')
      self._command.Display(self._args, self._resources)

    # Resource display is done.
    log.out.flush()

    # If the default format was used then display the epilog.
    if self._default_format_used:
      self._command.Epilog(resources_were_displayed)

    return self._resources
