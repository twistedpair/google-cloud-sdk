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
"""Utility for updating Looker instances."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core.console import console_io


def _WarnForAdminSettingsUpdate():
  """Adds prompt that warns about allowed email domains update."""
  message = 'Change to instance allowed email domain requested. '
  message += (
      'Updating the allowed email domains from cli means the value provided'
      ' will be considered as the entire list and not an amendment to the'
      ' existing list of allowed email domains.'
  )
  console_io.PromptContinue(
      message=message,
      prompt_string='Do you want to proceed with update?',
      cancel_on_no=True,
  )


def ModifyAllowedEmailDomains(unused_instance_ref, args, patch_request):
  """Python hook to modify allowed email domains in looker instance update request."""
  if args.IsSpecified('allowed_email_domains'):
    # Changing allowed email domains means this list will be overwritten in the
    # DB and not amended and users should be warned before proceeding.
    _WarnForAdminSettingsUpdate()
    patch_request.instance.adminSettings.allowedEmailDomains = (
        args.allowed_email_domains
    )
  return patch_request
