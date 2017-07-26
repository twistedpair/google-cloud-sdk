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

import argparse


class ArgumentError(argparse.ArgumentError):
  """Base class for argument errors with metrics.

  ArgumentError instances are intercepted by
  parser_extensions.ArgumentParser.error(), which
    1. reports a failed command to metrics
    2. prints a usage diagnostic to the standard error
    3. exits with status 2, bypassing gcloud_main exception handling

  Attributes:
    argument: str, The argument name(s) causing the error.
    error_extra_info: {str: str}, Extra info dict for error_format.
    error_format: str, A .format() string for constructng the error message
      from error_extra_info.
    extra_path_arg: str, Dotted command path to append to the command path.
    parser: ArgmentParser, Used to generate the usage string for the command.
      This could be a different subparser than the command parser.
  """

  def __init__(self, error_format, argument=None, extra_path_arg=None,
               parser=None, **kwargs):
    self.error_format = error_format
    self.argument = argument
    self.extra_path_arg = extra_path_arg
    self.parser = parser
    self.error_extra_info = kwargs
    super(ArgumentError, self).__init__(None, unicode(self))

  def __str__(self):
    message = self.error_format.format(**self.error_extra_info)
    if self.argument:
      message = u'argument {argument}: {message}'.format(
          argument=self.argument, message=message)
    return message


class RequiredArgumentError(ArgumentError):
  """Arparse required actions were not all present."""


class RequiredArgumentGroupError(ArgumentError):
  """Command has a group of arguments with none of the options present."""


class TooFewArgumentsError(ArgumentError):
  """Argparse didn't use all the Positional objects."""


class UnknownCommandError(ArgumentError):
  """Unknown command error."""


class UnrecognizedArgumentsError(ArgumentError):
  """User entered arguments that were not recognized by argparse."""


class WrongTrackError(ArgumentError):
  """For parsed commands in a different track."""


class OtherParsingError(ArgumentError):
  """Some other parsing error that is not any of the above."""


class ArgumentException(Exception):
  """ArgumentException is for problems with the declared arguments."""


class UnknownDestinationException(Exception):
  """Fatal error for an internal dest that has no associated arg."""
