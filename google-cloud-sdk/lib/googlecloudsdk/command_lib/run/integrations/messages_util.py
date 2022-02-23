# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Code for making shared messages between commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.command_lib.run.integrations import integration_printer


def GetSuccessMessageDeploy(integration_type, integration_name):
  """Returns a user message for a successful integration deploy.

  Args:
    integration_type: str, type of the integration
    integration_name: str, name of the integration
  """
  return ('[{{bold}}{}{{reset}}] integration [{{bold}}{}{{reset}}] '
          'has been deployed successfully.').format(integration_type,
                                                    integration_name)


def GetCallToAction(integration_type, resource_config, resource_status):
  """Print the call to action message for the given integration.

  Args:
    integration_type: str, type of the integration
    resource_config: dict, config of the integration
    resource_status: dict, status of the integration

  Returns:
    A formatted string of the call to action message.
  """
  formatter = integration_printer.GetFormatter(integration_type)
  return formatter.CallToAction({
      'config': resource_config,
      'status': resource_status
  })
