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

from googlecloudsdk.core import log
from googlecloudsdk.core.resource import resource_printer


class Displayer(object):
  """Implements the resource display method.

  Dispatches the global flags args by constructing a format string and letting
  resource_printer.Print() do the heavy lifting.

  Attributes:
    _args: The argparse.Namespace given to command.Run().
    _command: The Command object that generated the resources to display.
    _resources: The resource (list) to display.
  """

  def __init__(self, command, args, resources):
    """Constructor.

    Args:
      command: The Command object.
      args: The argparse.Namespace given to the command.Run().
      resources: The return value from command.Run().
    """
    self._command = command
    self._args = args
    self._resources = resources

  def _GetFormat(self):
    """Determines the display format.

    Returns:
      The format string, '' if there is none.
    """
    return self._args.format or ''

  def Display(self):
    """The default display method."""

    if not log.IsUserOutputEnabled():
      log.debug('Display disabled.')
      # NOTICE: Do not consume resources here. Some commands use this case to
      # access the results of Run() via the return value of Execute().
      return

    # Determine the format.
    fmt = self._GetFormat()

    if fmt:
      # Most command output will end up here.
      log.debug('Display format "%s".', fmt)
      # TODO(gsfowler): b/24267426
      if self._resources is not None:
        resource_printer.Print(self._resources, fmt, out=log.out)
    else:
      # This will eventually be rare.
      log.debug('Explict Display.')
      self._command.Display(self._args, self._resources)
