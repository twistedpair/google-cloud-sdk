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

Refer to the calliope.parser_extensions module for a detailed overview.
"""

from googlecloudsdk.core import exceptions


class ArgparseException(exceptions.Error):
  """General base class for exceptions during parsing of commands or flags."""


class WrongTrackException(ArgparseException):
  """WrongTrackException is for parsed commands in a different track."""


class ParsingCommandException(ArgparseException):
  """ParsingCommandException is for parsing problems with the command."""


class TooFewArgumentsException(ArgparseException):
  """Argparse didn't use all the Positional objects."""


class RequiredArgumentException(ArgparseException):
  """Arparse required actions were not all present."""


class RequiredArgumentGroupException(ArgparseException):
  """Command has a group of arguments with none of the options present."""


class UnrecognizedArguments(ArgparseException):
  """User entered arguments that were not recognized by argparse."""


class OtherParsingError(ArgparseException):
  """Some other parsing error that is not any of the above."""


class ArgumentException(Exception):
  """ArgumentException is for problems with the provided arguments."""


class UnknownDestination(Exception):
  """Fatal error for an internal dest that has no associated arg."""


class ArgumentParserError(object):
  """Object to store the ArgumentParser error and extra information.

    Args:
      dotted_command_path: str, as much as we could parse from the path to the
          command, separating elements by dots.
      error: class, the class to the error we want to report
      error_extra_info: str, json string for extra information that we want
          recorded with the error.
  """

  def __init__(self, dotted_command_path, error, error_extra_info):
    self.dotted_command_path = dotted_command_path
    self.error = error
    self.error_extra_info = error_extra_info
