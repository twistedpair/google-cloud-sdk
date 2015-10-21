# Copyright 2015 Google Inc. All Rights Reserved.
"""Commands for reading and manipulating unmanaged instance group."""
from googlecloudsdk.calliope import base
from googlecloudsdk.shared.compute import utils


class UnmanagedInstanceGroups(base.Group):
  """Read and manipulate Google Compute Engine unmanaged instance groups."""

UnmanagedInstanceGroups.detailed_help = {
    'brief': (
        'Read and manipulate Google Compute Engine unmanaged instance group'),
}
