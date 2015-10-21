# Copyright 2015 Google Inc. All Rights Reserved.
"""Wrapper for user-visible error exceptions to raise in the CLI."""

from googlecloudsdk.core import exceptions


class GenomicsError(exceptions.Error):
  """Exceptions for Genomics errors."""
