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

"""Utilities for app creation."""

from googlecloudsdk.api_lib.app import exceptions as api_lib_exceptions
from googlecloudsdk.core import exceptions
from googlecloudsdk.core.console import console_io


class UnspecifiedRegionError(exceptions.Error):
  """Region is not provided on the command line and running interactively."""


class AppAlreadyExistsError(exceptions.Error):
  """The app which is getting created already exists."""


def CreateApp(api_client, project, region):
  """Create an App Engine app in the given region.

  Prints info about the app being created and displays a progress tracker.

  Args:
    api_client: The App Engine Admin API client
    project: The GCP project
    region: The region to create the app

  Raises:
    AppAlreadyExistsError if app already exists
  """
  message = ('Creating App Engine application in project [{project}] and '
             'region [{region}].'.format(project=project, region=region))
  with console_io.ProgressTracker(message):
    try:
      api_client.CreateApp(region)
    except api_lib_exceptions.ConflictError:
      raise AppAlreadyExistsError(
          'The project [{project}] already contains an App Engine application. '
          'You can deploy your application using `gcloud app deploy`.'.format(
              project=project))


def CreateAppInteractively(api_client, project):
  """Interactively choose a region and create an App Engine app.

  The caller is responsible for calling this method only when the user can be
  prompted interactively.

  Example interaction:

      Which region?
        [1] us-east1      (supports standard and flexible)
        [2] europe-west   (supports standard)
        [3] us-central    (supports standard and flexible)
      Please enter your numeric choice:  1

  Args:
    api_client: The App Engine Admin API client
    project: The GCP project

  Raises:
    AppAlreadyExistsError if app already exists
  """
  all_regions = sorted(set(api_client.ListRegions()))
  idx = console_io.PromptChoice(all_regions, message=(
      'Please choose a region for your application. After choosing a region, '
      'it cannot be changed. Which region would you like to choose?\n\n'))
  region = all_regions[idx]
  CreateApp(api_client, project, region.region)

