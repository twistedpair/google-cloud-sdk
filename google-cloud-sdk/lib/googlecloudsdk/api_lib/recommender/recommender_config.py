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
"""Utilities for Recommender Config."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.recommender import base
from googlecloudsdk.api_lib.recommender import flag_utils
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.core import yaml


def CreateClient(release_track):
  """Creates Client."""
  api_version = flag_utils.GetApiVersion(release_track)
  return RecommenderConfig(api_version)


class RecommenderConfig(object):
  """Base RecommenderConfig client for all versions."""

  def __init__(self, api_version):
    client = apis.GetClientInstance(base.API_NAME, api_version)
    self._api_version = api_version
    self._messages = client.MESSAGES_MODULE
    self._message_prefix = base.RECOMMENDER_MESSAGE_PREFIX[api_version]
    self._project_service = client.projects_locations_recommenders
    self._org_service = client.organizations_locations_recommenders

  def _GetMessage(self, message_name):
    """Returns the API messages class by name."""

    return getattr(
        self._messages,
        '{prefix}{name}'.format(prefix=self._message_prefix,
                                name=message_name), None)

  def _ToCamelCase(self, s):
    """Converts CamelCase to camelCase."""
    return s[0].lower() + s[1:]

  def _ReadConfig(self, config_file, message_type):
    """Parse json config file."""
    config = None
    # Yaml is a superset of json, so parse json file as yaml.
    data = yaml.load_path(config_file)
    if data:
      config = messages_util.DictToMessageWithErrorCheck(data, message_type)
    return config

  def Get(self, config_name):
    """Gets a RecommenderConfig.

    Args:
      config_name: str, the name of the config being retrieved.

    Returns:
      The RecommenderConfig message.
    """
    if config_name.startswith('organizations'):
      request = self._messages.RecommenderOrganizationsLocationsRecommendersGetConfigRequest(
          name=config_name)
      return self._org_service.GetConfig(request)

    # Default to project
    request = self._messages.RecommenderProjectsLocationsRecommendersGetConfigRequest(
        name=config_name)
    return self._project_service.GetConfig(request)

  def Update(self, config_name, args):
    """Updates a RecommenderConfig.

    Args:
      config_name: str, the name of the config being retrieved.
      args: argparse.Namespace, The arguments that the command was invoked with.

    Returns:
      The updated RecommenderConfig message.
    Raises:
      Exception: If nothing is updated.
    """

    # TODO(b/205859938): Support annotations
    update_mask = []
    config = self._GetMessage('RecommenderConfig')()
    config.name = config_name
    config.etag = args.etag

    if args.config_file:
      gen_config = self._ReadConfig(
          args.config_file, self._GetMessage('RecommenderGenerationConfig'))
      config.recommenderGenerationConfig = gen_config
      update_mask.append('recommender_generation_config')

    if args.display_name:
      config.displayName = args.display_name
      update_mask.append('display_name')

    if not update_mask:
      raise Exception(
          'Nothing is being updated. Please specify one of config-file or display-name.'
      )

    # Need to do it this way to dynamically set the versioned RecommenderConfig
    kwargs = {
        'name': config_name,
        self._ToCamelCase(self._message_prefix + 'RecommenderConfig'): config,
        'updateMask': ','.join(update_mask),
        'validateOnly': args.validate_only
    }

    # Default to project
    request = self._messages.RecommenderProjectsLocationsRecommendersUpdateConfigRequest(
        **kwargs)
    return self._project_service.UpdateConfig(request)
