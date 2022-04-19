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
"""Gather stage/condition information for any important objects here."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.core.console import progress_tracker


UPDATE_APPLICATION = 'UpdateApplication'
CREATE_DEPLOYMENT = 'CreateDeployment'
UNDEPLOY_RESOURCE = 'UndeployResource'
CLEANUP_CONFIGURATION = 'CleanupConfiguration'


def _UpdateApplicationStage(create):
  """Returns the stage for updating the Application.

  Args:
    create: whether it's for the create command.

  Returns:
    progress_tracker.Stage
  """
  if create:
    message = 'Saving Configuration for Integration...'
  else:
    message = 'Updating Configuration for Integration...'

  return progress_tracker.Stage(message, key=UPDATE_APPLICATION)


def IntegrationStages(create):
  """Returns the progress tracker Stages for creating or updating an Integration.

  Args:
    create: whether it's for the create command.

  Returns:
    list of progress_tracker.Stage
  """
  return [
      _UpdateApplicationStage(create),
      progress_tracker.Stage(
          'Configuring Integration...', key=CREATE_DEPLOYMENT),
  ]


def IntegrationDeleteStages():
  """Returns the progress tracker Stages for deleting an Integration.

  Returns:
    list of progress_tracker.Stage
  """
  return [
      progress_tracker.Stage('Unbinding services...', key=UPDATE_APPLICATION),
      progress_tracker.Stage('Configuring services...', key=CREATE_DEPLOYMENT),
      progress_tracker.Stage(
          'Deleting Integration resources...', key=UNDEPLOY_RESOURCE),
      progress_tracker.Stage(
          'Saving Integration configurations...', key=CLEANUP_CONFIGURATION)
  ]


def ApplyStages():
  """Returns the progress tracker Stages for apply command.

  Returns:
    array of progress_tracker.Stage
  """
  return [
      progress_tracker.Stage('Saving Configuration...', key=UPDATE_APPLICATION),
      progress_tracker.Stage(
          'Actuating Configuration...', key=CREATE_DEPLOYMENT),
  ]

