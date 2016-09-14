# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Calliope parsing errors for logging and collecting metrics.

Not to be used by mortals.

"""

from googlecloudsdk.core import exceptions


class ArgparseException(exceptions.Error):
  """General base class for exceptions during parsing of commands or flags."""
  pass


class WrongTrackException(ArgparseException):
  """WrongTrackException is for parsed commands in a different track."""
  pass


class ParsingCommandException(ArgparseException):
  """ParsingCommandException is for parsing problems with the command."""
  pass


class TooFewArgumentsException(ArgparseException):
  """Argparse didn't use all the Positional objects."""
  pass


class RequiredArgumentException(ArgparseException):
  """Arparse required actions were not all present."""
  pass


class RequiredArgumentGroupException(ArgparseException):
  """Command has a group of arguments with none of the options present."""
  pass


class UnrecognizedArguments(ArgparseException):
  """User entered arguments that were not recognized by argparse."""
  pass


class OtherParsingError(ArgparseException):
  """Some other parsing error that is not any of the above."""
  pass
