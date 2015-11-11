# Copyright 2014 Google Inc. All Rights Reserved.
"""Commands for reading and manipulating instance groups."""
from googlecloudsdk.calliope import base


class InstanceGroups(base.Group):
  """Read and manipulate Google Compute Engine instance groups."""


InstanceGroups.detailed_help = {
    'brief': (
        'Read and manipulate Google Compute Engine instance groups'),
}
