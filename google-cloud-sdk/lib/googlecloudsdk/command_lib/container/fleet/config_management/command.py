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
"""Core command logic for Config Management surface."""

from googlecloudsdk.command_lib.container.fleet.features import base
from googlecloudsdk.core import exceptions
import six


class Core(base.UpdateCommand):
  """Backend for Config Management surface.

  Config Management command core that supports all complex operations on the
  feature. Serves to unclutter surface command implementations.
  """

  # TODO(b/338005906): Call method for disable --fleet-default-member-config.
  def clear_fleet_default(self):
    """Unsets the fleet-default config for the Config Management feature.

    Returns:
      The feature with the fleet-default config cleared, if the feature exists.
      Otherwise, None, without raising an error.
    """
    mask = ['fleet_default_member_config']
    # Feature cannot be empty on update, which would be the case without the
    # placeholder name field when we try to clear the fleet default config.
    # The placeholder name field must not be in the mask, lest we actually
    # change the feature name.
    # TODO(b/302390572): Replace with better solution if found.
    patch = self.messages.Feature(name='placeholder')
    try:
      return self.Update(mask, patch)
    except exceptions.Error as e:
      # Do not error or log if feature does not exist.
      if six.text_type(e) != six.text_type(self.FeatureNotEnabledError()):
        raise e
