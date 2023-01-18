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
"""This typekit contains functions implemented by the CloudSQL integration.

The base functions from the TypeKit class can be overridden here if more
functionality is needed.  For now, the CloudSQL integration almost entirely
works out of the box with what works in the base class.

TODO(b/191327853):
Once private IP is supported then this class needs to be updated.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.command_lib.run.integrations.typekits import base


class CloudSqlTypeKit(base.TypeKit):
  """The Cloud SQL integration typekit."""

  def GetDeployMessage(self, create=False):
    return 'This might take up to 15 minutes.'

  def UpdateResourceConfig(self, parameters, resource_config):
    """Updates the existing resource config with the parameters provided.

    Args:
      parameters: dict, user provided parameters from the command.
      resource_config: dict, resource config associated with the integration.
    """
    settings = resource_config.setdefault('settings', {})
    if 'tier' in parameters:
      settings['tier'] = parameters['tier']
    if 'version' in parameters:
      resource_config['version'] = parameters['version']

