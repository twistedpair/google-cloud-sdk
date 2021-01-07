# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Provides getters and validators for the platform flag and property."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections

from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io

PLATFORM_MANAGED = 'managed'
PLATFORM_GKE = 'gke'
PLATFORM_KUBERNETES = 'kubernetes'

PLATFORM_SHORT_DESCRIPTIONS = {
    PLATFORM_MANAGED: 'Cloud Run (fully managed)',
    PLATFORM_GKE: 'Cloud Run for Anthos deployed on Google Cloud',
    PLATFORM_KUBERNETES: 'Cloud Run for Anthos deployed on VMware',
}

_PLATFORM_LONG_DESCRIPTIONS = {
    PLATFORM_MANAGED:
        ('Fully managed version of Cloud Run. '
         'Use with the `--region` flag or set the [run/region] property '
         'to specify a Cloud Run region.'),
    PLATFORM_GKE:
        ('Cloud Run for Anthos on Google Cloud. '
         'Use with the `--cluster` and `--cluster-location` flags or set the '
         '[run/cluster] and [run/cluster_location] properties to specify a '
         'cluster in a given zone.'),
    PLATFORM_KUBERNETES:
        ('Use a Knative-compatible kubernetes cluster. '
         'Use with the `--kubeconfig` and `--context` flags to specify a '
         'kubeconfig file and the context for connecting.'),
}

PLATFORMS = collections.OrderedDict([
    (PLATFORM_MANAGED, _PLATFORM_LONG_DESCRIPTIONS[PLATFORM_MANAGED]),
    (PLATFORM_GKE, _PLATFORM_LONG_DESCRIPTIONS[PLATFORM_GKE]),
    (PLATFORM_KUBERNETES, _PLATFORM_LONG_DESCRIPTIONS[PLATFORM_KUBERNETES]),
])

# Used by managed-only commands to support showing a specific disallowed error
# when platform is set to anything other than `managed` rather than ignoring
# the flag/property or throwing a generic gcloud error for unsupported value.
PLATFORMS_MANAGED_ONLY = collections.OrderedDict([
    (PLATFORM_MANAGED, _PLATFORM_LONG_DESCRIPTIONS[PLATFORM_MANAGED]),
    (PLATFORM_GKE,
     'Cloud Run for Anthos on Google Cloud. Not supported by this command.'),
    (PLATFORM_KUBERNETES,
     'Use a Knative-compatible kubernetes cluster.  Not supported by this command.'
    ),
])

# Used by Anthos-only commands to support showing a specific disallowed error
# when platform is set to `managed` rather than throwing a generic gcloud error
# for unsupported value.
PLATFORMS_ANTHOS_ONLY = collections.OrderedDict([
    (PLATFORM_MANAGED,
     'Fully managed version of Cloud Run. Not supported by this command.'),
    (PLATFORM_GKE, _PLATFORM_LONG_DESCRIPTIONS[PLATFORM_GKE]),
    (PLATFORM_KUBERNETES, _PLATFORM_LONG_DESCRIPTIONS[PLATFORM_KUBERNETES]),
])


def GetPlatform(prompt_if_unset=True):
  """Returns the platform to run on.

  If set by the user, returns whatever value they specified without any
  validation. If not set by the user, this may prompt the user to choose a
  platform and sets the property so future calls to this method do continue to
  prompt.

  Args:
    prompt_if_unset: bool, if True, will try to prompt for the platform

  Raises:
    ArgumentError: if no platform is specified, prompt_if_unset is True, and
      prompting is not allowed.
  """
  platform = properties.VALUES.run.platform.Get()
  if platform is None and prompt_if_unset:
    if console_io.CanPrompt():
      platform_descs = [PLATFORM_SHORT_DESCRIPTIONS[k] for k in PLATFORMS]
      index = console_io.PromptChoice(
          platform_descs,
          message='Please choose a target platform:',
          cancel_option=True)
      platform = list(PLATFORMS.keys())[index]
      # Set platform so we don't re-prompt on future calls to this method
      # and so it's available to anyone who wants to know the platform.
      properties.VALUES.run.platform.Set(platform)
      log.status.Print(
          'To specify the platform yourself, pass `--platform {0}`. '
          'Or, to make this the default target platform, run '
          '`gcloud config set run/platform {0}`.\n'.format(platform))
    else:
      raise exceptions.ArgumentError(
          'No platform specified. Pass the `--platform` flag or set '
          'the [run/platform] property to specify a target platform.\n'
          'Available platforms:\n{}'.format('\n'.join(
              ['- {}: {}'.format(k, v) for k, v in PLATFORMS.items()])))
  return platform


def ValidatePlatformIsManaged(unused_ref, unused_args, req):
  """Validate the specified platform is managed.

  This method is referenced by the declaritive iam commands which only work
  against the managed platform.

  Args:
    unused_ref: ref to the service.
    unused_args: Namespace, The args namespace.
    req: The request to be made.

  Returns:
    Unmodified request
  """
  if GetPlatform() != PLATFORM_MANAGED:
    raise calliope_exceptions.BadArgumentException(
        '--platform', 'The platform [{platform}] is not supported by this '
        'operation. Specify `--platform {managed}` or run '
        '`gcloud config set run/platform {managed}`.'.format(
            platform=GetPlatform(), managed=PLATFORM_MANAGED))
  return req
