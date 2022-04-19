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


def GetSuccessMessage(integration_type, integration_name, action='deployed'):
  """Returns a user message for a successful integration deploy.

  Args:
    integration_type: str, type of the integration
    integration_name: str, name of the integration
    action: str, the action that succeeded
  """
  return ('[{{bold}}{}{{reset}}] integration [{{bold}}{}{{reset}}] '
          'has been {} successfully.').format(integration_type,
                                              integration_name, action)


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


def GetDeleteErrorMessage(integration_name):
  """Returns message when delete command fails.

  Args:
    integration_name: str, name of the integration.

  Returns:
    A formatted string of the error message.
  """
  return ('Deleting Integration [{}] failed, please rerun the delete command to'
          ' try again.').format(integration_name)


def CheckStatusMessage(release_track, integration_name):
  """Message about check status with describe command.

  Args:
    release_track: Release track of the command being run.
    integration_name: str, name of the integration

  Returns:
    A formatted string of the message.
  """
  track = release_track.prefix
  if track:
    track += ' '
  return (
      'You can check the status with `gcloud {}run integrations describe {}`'
      .format(track, integration_name))


def GetDeployMessage(resource_type, create=False):
  """Generates a message about the deployment of the integration type.

  Args:
    resource_type: Resource Type of the integration.
    create: whether it's for the create command.

  Returns:
    A string message, or None if no message is configured for that type.
  """

  if resource_type == 'redis':
    return 'This might take up to 10 minutes.'
  if resource_type == 'router':
    message = 'This might take up to 5 minutes.'
    if create:
      message += ' Manual DNS configuration will be required after completion.'
    return message
  return None
