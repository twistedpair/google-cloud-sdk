# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Helper functions for end of sale check and deprecation notice."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.services import enable_api
from googlecloudsdk.command_lib.run import pretty_print
from googlecloudsdk.command_lib.runapps import exceptions
from googlecloudsdk.core import properties


def CheckIfEndOfSaleApplies():
  """Checks if the customer is new and if so returns EOS error."""
  project_id = properties.VALUES.core.project.Get()
  # gcloud-disable-gdu-domain
  if not enable_api.IsServiceEnabled(project_id, "runapps.googleapis.com"):
    raise exceptions.CRIUnavailableToNewUsersError(
        "Cloud Run integrations are no longer available to new customers."
    )


def DeprecationNotice():
  """Prints a deprecation notice header for all commands."""
  pretty_print.Info("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
  pretty_print.Info(
      "Cloud Run Integrations will be removed from the gcloud CLI in January"
      " 2025. Existing integrations will continue to work with no action"
      " required."
  )
  pretty_print.Info("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n")
