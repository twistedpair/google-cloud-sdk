# -*- coding: utf-8 -*-
# Copyright 2014 Google Inc. All Rights Reserved.

"""Unified diff resource printer."""

import cStringIO
import difflib

from googlecloudsdk.core import log
from googlecloudsdk.core.resource import resource_printer


class ResourceDiff(object):
  """Prints the unified diff of two resources in a specific format."""

  def __init__(self, original, changed):
    self.original = original
    self.changed = changed

  def Print(self, print_format, out=None, defaults=None):
    """Prints the unified diff of formatter output for original and changed.

    Prints a unified diff, eg,
    ---

    +++

    @@ -27,6 +27,6 @@

     settings.pricingPlan:                             PER_USE
     settings.replicationType:                         SYNCHRONOUS
     settings.settingsVersion:                         1
    -settings.tier:                                    D1
    +settings.tier:                                    D0
     state:                                            RUNNABLE

    Args:
      print_format: The print format name.
      out: The output stream, stdout if None.
      defaults: Optional resource_projection_spec.ProjectionSpec defaults.
    """
    # Fill a buffer with the object as rendered originally.
    buff_original = cStringIO.StringIO()
    printer = resource_printer.Printer(print_format, out=buff_original,
                                       defaults=defaults)
    printer.PrintSingleRecord(self.original)
    # Fill a buffer with the object as rendered after the change.
    buff_changed = cStringIO.StringIO()
    printer = resource_printer.Printer(print_format, out=buff_changed,
                                       defaults=defaults)
    printer.PrintSingleRecord(self.changed)
    # Send these two buffers to the unified_diff() function for printing.
    lines_original = buff_original.getvalue().split('\n')
    lines_changed = buff_changed.getvalue().split('\n')
    lines_diff = difflib.unified_diff(lines_original, lines_changed)
    out = out or log.out
    for line in lines_diff:
      out.write(line + '\n')
