# Copyright 2015 Google Inc. All Rights Reserved.

"""Cloud logging logs group."""

from googlecloudsdk.calliope import base


@base.Hidden
class Metrics(base.Group):
  """Manages log-based metrics."""
