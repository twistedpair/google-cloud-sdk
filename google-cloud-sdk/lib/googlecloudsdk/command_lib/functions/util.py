# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Cross-version utility classes and functions for gcloud functions commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc

from googlecloudsdk.api_lib.functions.v1 import util as api_util_v1
from googlecloudsdk.api_lib.functions.v2 import client as client_v2
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.command_lib.functions import flags

import six  # pylint: disable=unused-import # Somehow Pylint complains :(


class FunctionResourceCommand(six.with_metaclass(abc.ABCMeta, base.Command)):
  """Mix-in for single function resource commands that work with both v1 or v2.

  Which version of the command to run is determined by the following precedence:
  1. Explicit setting via the --gen2/--no-gen2 flags or functions/gen2 property.
  2. The generation of the function if it exists.
  2. The v1 API by default.

  Subclasses should add the function resource arg and --gen2 flag.
  """

  @abc.abstractmethod
  def _RunV1(self, args):
    # type: (parser_extensions.Namespace) -> Any
    """Runs the command against the v1 API."""

  @abc.abstractmethod
  def _RunV2(self, args):
    # type: (parser_extensions.Namespace) -> Any
    """Runs the command against the v2 API."""

  @api_util_v1.CatchHTTPErrorRaiseHTTPException
  def Run(self, args):
    # type: (parser_extensions.Namespace) -> Any
    """Runs the command.

    Args:
      args: The arguments this command was invoked with.

    Returns:
      The result of the command.

    Raises:
      HttpException: If an HttpError occurs.
    """
    if flags.ShouldUseGen2():
      return self._RunV2(args)

    if flags.ShouldUseGen1():
      return self._RunV1(args)

    client = client_v2.FunctionsClient(self.ReleaseTrack())
    function = client.GetFunction(args.CONCEPTS.name.Parse().RelativeName())

    if (
        function
        and function.environment
        == client.messages.Function.EnvironmentValueValuesEnum.GEN_2
    ):
      return self._RunV2(args)

    return self._RunV1(args)
