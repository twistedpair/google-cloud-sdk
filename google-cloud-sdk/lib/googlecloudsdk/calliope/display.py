# Copyright 2015 Google Inc. All Rights Reserved.
"""Resource display for all calliope commands.

The print_format string passed to resource_printer.Print() is determined in this
order:
 (1) Display disabled and resources not consumed if user output is disabled.
 (2) The explicit --format flag format string.
 (3) The explicit Display() method.
 (4) Otherwise no output but the resources are consumed.

This module does a lot of format expression manipulation. Format expressions are
are left-to-right composable. Each format expression is a string tuple

  < NAME [ATTRIBUTE...] (PROJECTION...) >

where only one of the three elements need be present.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import remote_completion
from googlecloudsdk.core.resource import resource_filter
from googlecloudsdk.core.resource import resource_printer
from googlecloudsdk.core.resource import resource_projection_parser
from googlecloudsdk.core.resource import resource_transform
from googlecloudsdk.core.util import peek_iterable


# TODO(dgk): The URI list functions should be part of remote_completion.
def _AddToUriCache(uris):
  """Add the uris list to the URI cache.

  Args:
    uris: The list of URIs to add.
  """
  update = remote_completion.RemoteCompletion().AddToCache
  for uri in uris:
    update(uri)


def _DeleteFromUriCache(uris):
  """Deletes the uris list from the URI cache.

  Args:
    uris: The list of URIs to delete.
  """
  update = remote_completion.RemoteCompletion().DeleteFromCache
  for uri in uris:
    update(uri)


def _ReplaceUriCache(uris):
  """Replaces the URI cache with the uris list.

  Args:
    uris: The list of URIs that replaces the cache.
  """
  remote_completion.RemoteCompletion().StoreInCache(uris)


_URI_UPDATER = {
    base.ADD_TO_URI_CACHE: _AddToUriCache,
    base.DELETE_FROM_URI_CACHE: _DeleteFromUriCache,
    base.REPLACE_URI_CACHE: _ReplaceUriCache,
}


class _UriCacher(object):
  """A Tapper module that caches URIs based on the cache update op.

  Attributes:
    _update_cache_op: The non-None return value from UpdateUriCache().
    _uris: The list of changed URIs, None if it is corrupt.
  """

  def __init__(self, update_cache_op):
    self._update_cache_op = update_cache_op
    self._uris = []

  def AddResource(self, resource):
    """Appends the URI for resource to the list of cache changes.

    Sets self._uris to None if a URI could not be retrieved for any resource.

    Args:
      resource: The resource from which the URI is extracted.

    Returns:
      True - all resources are seen downstream.
    """
    if self._uris is not None:
      uri = resource_transform.TransformUri(resource, undefined=None)
      if uri:
        self._uris.append(uri)
      else:
        self._uris = None
    return True

  def Update(self):
    if self._uris is not None:
      _URI_UPDATER[self._update_cache_op](self._uris)


class _Filterer(object):
  """A Tapper module that filters out resources not matching an expression.

  Attributes:
    _match: The resource filter method.
  """

  def __init__(self, expression, defaults):
    """Constructor.

    Args:
      expression: The resource filter expression string.
      defaults: The resource format and filter default projection.
    """
    self._match = resource_filter.Compile(
        expression, defaults=defaults).Evaluate

  def FilterResource(self, resource):
    """Returns True if resource matches the filter expression.

    Args:
      resource: The resource to filter.

    Returns:
      True if resource matches the filter expression.
    """
    return self._match(resource)


class _Limiter(object):
  """A Tapper method that filters out resources after a limit is reached.

  Attributes:
    _limit: The resource count limit.
    _count: The resource count.
  """

  def __init__(self, limit):
    self._limit = limit
    self._count = 0

  def LimitResource(self, unused_resource):
    """Returns True if the limit has not been reached yet.

    Args:
      unused_resource: The resource to limit.

    Returns:
      True if the limit has not been reached yet.
    """
    self._count += 1
    return self._count <= self._limit


def _GetFlag(args, flag_name):
  """Returns the value of flag_name in args, None if it is unknown or unset.

  Args:
    args: The argparse.Namespace given to command.Run().
    flag_name: The flag name string sans leading '--'.

  Returns:
    The flag value or None if it is unknown or unset.
  """
  return getattr(args, flag_name, None)


class Displayer(object):
  """Implements the resource display method.

  Dispatches the global flags args by constructing a format string and letting
  resource_printer.Print() do the heavy lifting.

  Attributes:
    _args: The argparse.Namespace given to command.Run().
    _command: The Command object that generated the resources to display.
    _defaults: The resource format and filter default projection.
    _resources: The resources to display, returned by command.Run().
  """

  # A command with these flags might return incomplete resource lists.
  _CORRUPT_FLAGS = ('async', 'filter', 'limit')

  def __init__(self, command, args, resources):
    """Constructor.

    Args:
      command: The Command object.
      args: The argparse.Namespace given to the command.Run().
      resources: The resources to display, returned by command.Run().
    """
    self._args = args
    self._command = command
    self._defaults = None
    self._resources = resources

  def _AddUriCacheTap(self):
    """Taps a resource Uri cache updater into self.resources if needed."""

    cache_update_op = self._command.GetUriCacheUpdateOp()
    if not cache_update_op:
      return

    if any([_GetFlag(self._args, flag) for flag in self._CORRUPT_FLAGS]):
      return

    cacher = _UriCacher(cache_update_op)
    self._resources = peek_iterable.Tapper(self._resources,
                                           cacher.AddResource,
                                           cacher.Update)

  def _AddFilterTap(self):
    """Taps a resource filter into self.resources if needed."""
    expression = _GetFlag(self._args, 'filter')
    if not expression:
      return
    filterer = _Filterer(expression, self._defaults)
    self._resources = peek_iterable.Tapper(self._resources,
                                           filterer.FilterResource)

  def _AddLimitTap(self):
    """Taps a resource limit into self.resources if needed."""
    limit = _GetFlag(self._args, 'limit')
    if limit is None or limit < 0:
      return
    limiter = _Limiter(limit)
    self._resources = peek_iterable.Tapper(self._resources,
                                           limiter.LimitResource)

  def _GetResourceInfoFormat(self):
    """Determines the format from the resource registry if any.

    Returns:
      format: The format string, None if there is no resource registry info
          for the command.
    """
    info = self._command.ResourceInfo(self._args)
    if not info:
      return None
    styles = ['list']
    if _GetFlag(self._args, 'simple_list'):
      styles.insert(0, 'simple')
    for style in styles:
      attr = '{0}_format'.format(style)
      fmt = getattr(info, attr, None)
      if fmt:
        break
    else:
      return None
    symbols = info.GetTransforms()
    if symbols or info.defaults:
      self._defaults = resource_projection_parser.Parse(
          info.defaults, defaults=self._defaults, symbols=symbols)
    return fmt

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
    fmt = self._GetResourceInfoFormat()
    if not fmt:
      fmt = self._command.Format(self._args)
    return fmt

  def _GetFormat(self):
    """Determines the display format.

    Returns:
      format: The display format string.
    """
    if _GetFlag(self._args, 'uri'):
      return 'value(uri())'

    default_fmt = self._GetDefaultFormat()
    fmt = self._GetExplicitFormat()

    if default_fmt:
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
      fmt = default_fmt + ' ' + fmt if fmt else default_fmt

    if fmt and _GetFlag(self._args, 'sort_by'):
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
        orders.append('{name}:sort={order}{reverse}'.format(
            name=name, order=order + 1,
            reverse=':reverse' if reverse else ''))
      fmt += ':({orders})'.format(orders=','.join(orders))

    return fmt

  def Display(self):
    """The default display method."""

    if not log.IsUserOutputEnabled():
      log.info('Display disabled.')
      # NOTICE: Do not consume resources here. Some commands use this case to
      # access the results of Run() via the return value of Execute().
      return

    # Determine the format.
    fmt = self._GetFormat()

    # Add a URI cache update tap if needed.
    self._AddUriCacheTap()

    # Add a resource filter tap if needed.
    self._AddFilterTap()

    # Add a resource limit tap if needed.
    self._AddLimitTap()

    if fmt:
      # Most command output will end up here.
      log.info('Display format "%s".', fmt)
      resource_printer.Print(
          self._resources, fmt, defaults=self._defaults, out=log.out)
    elif hasattr(self._command, 'Display'):
      # This will eventually be rare.
      log.info('Explict Display.')
      self._command.Display(self._args, self._resources)
