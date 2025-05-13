# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""Factory for SparkHistoryServerConfig message."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.generated_clients.apis.dataproc.v1.dataproc_v1_messages import AuthenticationConfig as ac


class AuthenticationConfigFactory(object):
  """Factory for AuthenticationConfig message.

  Adds arguments to argument parser and create AuthenticationConfig from
  parsed arguments.
  """

  def __init__(self, dataproc):
    """Factory class for AuthenticationConfig message.

    Args:
      dataproc: An api_lib.dataproc.Dataproc instance.
    """
    self.dataproc = dataproc

  def GetMessage(self, args):
    """Builds an AuthenticationConfig instance.

    Args:
      args: Parsed arguments.

    Returns:
      AuthenticationConfig: An AuthenticationConfig message instance.
      None if all fields are None.
    """
    kwargs = {}

    if args.user_workload_authentication_type:
      kwargs['userWorkloadAuthenticationType'] = arg_utils.ChoiceToEnum(
          args.user_workload_authentication_type,
          ac.UserWorkloadAuthenticationTypeValueValuesEnum,
      )

    if not kwargs:
      return None

    return self.dataproc.messages.AuthenticationConfig(**kwargs)


def AddArguments(parser):
  """Adds related arguments to aprser."""
  parser.add_argument(
      '--user-workload-authentication-type',
      help=(
          'Whether to use END_USER_CREDENTIALS or SERVICE_ACCOUNT to run'
          ' the workload.'
      ),
  )
