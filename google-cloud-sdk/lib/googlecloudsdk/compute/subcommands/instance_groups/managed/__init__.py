# Copyright 2015 Google Inc. All Rights Reserved.
"""Commands for reading and manipulating managed instance groups."""
from googlecloudsdk.calliope import base
from googlecloudsdk.shared.compute import utils


class ManagedInstanceGroups(base.Group):
  """Read and manipulate Google Compute Engine managed instance groups."""

ManagedInstanceGroups.detailed_help = {
    'brief': (
        'Read and manipulate Google Compute Engine managed instance groups'),
}
