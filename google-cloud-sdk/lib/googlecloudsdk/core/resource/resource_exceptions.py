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


class ResourceRegistryAttributeError(exceptions.InternalError):
  """Missing or invalid resource registry attribute error."""
  pass


class UnregisteredCollectionError(Error):
  """Unregistered resource collection error."""
  pass
