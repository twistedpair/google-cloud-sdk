# Copyright 2015 Google Inc. All Rights Reserved.

"""Resource execeptions."""

from googlecloudsdk.core import exceptions


class Error(exceptions.Error):
  """A base exception for all recoverable resource errors => no stack trace."""
  pass


class InternalError(exceptions.InternalError):
  """A base exception for all unrecoverable resource errors => stack trace."""
  pass


class ExpressionSyntaxError(Error):
  """Resource expression syntax error."""
  pass


class UnregisteredCollectionError(Error):
  """Unregistered resource collection error."""
  pass


class CollectionRefLoopError(InternalError):
  """Resource collection ref lookup loop error."""
  pass
