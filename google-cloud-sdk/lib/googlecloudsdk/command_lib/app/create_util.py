# -*- coding: utf-8 -*- #
# Copyright 2016 Google LLC. All Rights Reserved.
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

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io


APP_CREATE_WARNING = """\
Creating an App Engine application for a project is irreversible and the region
cannot be changed. More information about regions is at
<https://cloud.google.com/appengine/docs/locations>.
"""
DEFAULT_MAX_INSTANCES_FORWARD_CHANGE_WARNING = """\
Starting from March, 2025, App Engine sets the automatic scaling maximum instances
default for standard environment deployments to 20. This change doesn't impact
existing apps. To override the default, specify the new max_instances value in your
app.yaml file, and deploy a new version or redeploy over an existing version.
For more details on max_instances, see
<https://cloud.google.com/appengine/docs/standard/reference/app-yaml.md#scaling_elements>.
"""

TRY_CLOUD_RUN_NUDGE_MSG = """\
Cloud Run offers the most modern fully managed application hosting experience
with lower minimum billable times and support for GPUs on demand for your AI/ML workloads.
Deploy code written in any programming language supported by App Engine on Cloud Run.
Learn more at https://cloud.google.com/run/docs/quickstarts#build-and-deploy-a-web-service
"""


class UnspecifiedRegionError(exceptions.Error):
  """Region is not provided on the command line and running interactively."""


class AppAlreadyExistsError(exceptions.Error):
  """The app which is getting created already exists."""


def AddAppCreateFlags(parser):
  """Add the common flags to a app create command."""
  parser.add_argument(
      '--region',
      help=(
          'The region to create the app within.  '
          'Use `gcloud app regions list` to list available regions.  '
          'If not provided, select region interactively.'
      ),
  )
  parser.add_argument(
      '--service-account',
      help=("""\
          The app-level default service account to create the app with.
          Note that you can specify a distinct service account for each
          App Engine version with `gcloud app deploy --service-account`.
          However if you do not specify a version-level service account,
          this default will be used. If this parameter is not provided for app
          creation, the app-level default will be set to be the out-of-box
          App Engine Default Service Account,
          https://cloud.google.com/appengine/docs/standard/python3/service-account
          outlines the limitation of that service account."""),
  )
  parser.add_argument(
      '--ssl-policy',
      choices=['TLS_VERSION_1_0', 'TLS_VERSION_1_2'],
      help='The app-level SSL policy to create the app with.',
  )


def CheckAppNotExists(api_client, project):
  """Raises an error if the app already exists.

  Args:
    api_client: The App Engine Admin API client
    project: The GCP project

  Raises:
    AppAlreadyExistsError if app already exists
  """
  try:
    app = api_client.GetApplication()  # Should raise NotFoundError
  except apitools_exceptions.HttpNotFoundError:
    pass
  else:
    region = ' in region [{}]'.format(app.locationId) if app.locationId else ''
    raise AppAlreadyExistsError(
        'The project [{project}] already contains an App Engine '
        'application{region}.  You can deploy your application using '
        '`gcloud app deploy`.'.format(project=project, region=region))


def CreateApp(
    api_client,
    project,
    region,
    suppress_warning=False,
    service_account=None,
    ssl_policy=None,
):
  """Create an App Engine app in the given region.

  Prints info about the app being created and displays a progress tracker.

  Args:
    api_client: The App Engine Admin API client
    project: The GCP project
    region: The region to create the app
    suppress_warning: True if user doesn't need to be warned this is
      irreversible.
    service_account: The app level service account for the App Engine app.
    ssl_policy: str, the app-level SSL policy to update for this App Engine app.
      Can be default or modern.

  Raises:
    AppAlreadyExistsError if app already exists
  """

  ssl_policy_enum = {
      'TLS_VERSION_1_0': (
          api_client.messages.Application.SslPolicyValueValuesEnum.DEFAULT
      ),
      'TLS_VERSION_1_2': (
          api_client.messages.Application.SslPolicyValueValuesEnum.MODERN
      ),
  }.get(ssl_policy)

  if not suppress_warning:
    log.status.Print(
        'You are creating an app for project [{project}].'.format(
            project=project
        )
    )
    if service_account:
      log.status.Print(
          'Designating app-level default service account to be '
          '[{service_account}].'.format(service_account=service_account)
      )
    if ssl_policy_enum:
      log.status.Print(
          'Designating app-level SSL policy to be [{ssl_policy}].'.format(
              ssl_policy=ssl_policy
          )
      )
    log.warning(APP_CREATE_WARNING)
    # TODO: b/388712720 - Cleanup warning once backend experiments are cleaned
    log.warning(DEFAULT_MAX_INSTANCES_FORWARD_CHANGE_WARNING)

    log.status.Print('NOTE: ' + TRY_CLOUD_RUN_NUDGE_MSG)
  try:
    api_client.CreateApp(
        region, service_account=service_account, ssl_policy=ssl_policy_enum
    )
  except apitools_exceptions.HttpConflictError:
    raise AppAlreadyExistsError(
        'The project [{project}] already contains an App Engine application. '
        'You can deploy your application using `gcloud app deploy`.'.format(
            project=project))


def CreateAppInteractively(
    api_client,
    project,
    regions=None,
    extra_warning='',
    service_account=None,
    ssl_policy=None,
):
  """Interactively choose a region and create an App Engine app.

  The caller is responsible for calling this method only when the user can be
  prompted interactively.

  Example interaction:

      Please choose the region where you want your App Engine application
      located:

        [1] us-east1      (supports standard and flexible)
        [2] europe-west   (supports standard)
        [3] us-central    (supports standard and flexible)
        [4] cancel
      Please enter your numeric choice:  1

  Args:
    api_client: The App Engine Admin API client
    project: The GCP project
    regions: The list of regions to choose from; if None, all possible regions
      are listed
    extra_warning: An additional warning to print before listing regions.
    service_account: The app level service account for the App Engine app.
    ssl_policy: str, the app-level SSL policy to update for this App Engine app.
      Can be default or modern.

  Raises:
    AppAlreadyExistsError if app already exists
  """
  log.status.Print('You are creating an app for project [{}].'.format(project))
  log.warning(APP_CREATE_WARNING)
  # TODO: b/388712720 - Cleanup warning once backend experiments are cleaned
  log.warning(DEFAULT_MAX_INSTANCES_FORWARD_CHANGE_WARNING)

  log.status.Print('NOTE: ' + TRY_CLOUD_RUN_NUDGE_MSG)
  regions = regions or sorted(set(api_client.ListRegions()), key=str)
  if extra_warning:
    log.warning(extra_warning)
  idx = console_io.PromptChoice(
      regions,
      message=(
          'Please choose the region where you want your App Engine '
          'application located:\n\n'
      ),
      cancel_option=True,
  )
  region = regions[idx]
  CreateApp(
      api_client,
      project,
      region.region,
      suppress_warning=True,
      service_account=service_account,
      ssl_policy=ssl_policy,
  )
