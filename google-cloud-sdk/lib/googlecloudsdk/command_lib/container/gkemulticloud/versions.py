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
"""Supports getting additional information on gke version(s).

We may want to retrieve specific information on a gke version. This file will
aid us in doing so. Such as if we need to know if a cluster version is end of
life etc.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.container.gkemulticloud import locations as api_util
from googlecloudsdk.command_lib.container.gkemulticloud import constants


_UPGRADE_COMMAND_CLUSTER = """
To upgrade a cluster to a newer version, run:
$ gcloud container {users_platform} clusters update {name} --location={location} --cluster-version={{CLUSTER_VERSION}}
"""

_END_OF_LIFE_MESSAGE_DESCRIBE_CLUSTER = """
The current version of your cluster(s) is unsupported, please upgrade.
"""

_SUPPORTED_COMMAND = """
To see the list of supported versions, run:
$ gcloud container {users_platform} get-server-config --location={location}
"""


def _is_end_of_life(platform, location_ref, version):
  """Tells if a version is end of life.

  Args:
    platform: A string, the platform the component is on {AWS,Azure}.
    location_ref:  A resource object, the pathing portion the url, used to get
      the proper server config.
    version: A string, the GKE version the component is running.

  Returns:
    A boolean value to state if the version on the specified platform is marked
    as end of life.
  """
  client = api_util.LocationsClient()
  if platform == constants.AZURE:
    v = client.GetAzureServerConfig(location_ref)
  elif platform == constants.AWS:
    v = client.GetAwsServerConfig(location_ref)
  else:
    return False
  for x in v.validVersions:
    if x.version == version:
      if x.endOfLife:
        return True
      return False
  return True


def upgrade_hint_cluster(cluster_ref, cluster_info, platform):
  """Generates a message that users if their cluster version can be upgraded.

  Args:
    cluster_ref: A resource object, the cluster resource information.
    cluster_info: A GoogleCloudGkemulticloudV1AzureCluster or
      GoogleCloudGkemulticloudV1AwsCluster resource, the full list of
      information on the cluster that is to be tested.
    platform: A string, the platform the component is on {AWS,Azure}.

  Returns:
    A message in how to upgrade a cluster if its end of life.
  """
  upgrade = None
  if _is_end_of_life(
      platform, cluster_ref.Parent(), cluster_info.controlPlane.version
  ):
    name = None
    if platform == constants.AWS:
      name = cluster_ref.awsClustersId
    elif platform == constants.AZURE:
      name = cluster_ref.azureClustersId
    location = cluster_ref.locationsId
    upgrade = _END_OF_LIFE_MESSAGE_DESCRIBE_CLUSTER
    upgrade += _UPGRADE_COMMAND_CLUSTER.format(
        users_platform=platform.lower(), name=name, location=location
    )
    upgrade += _SUPPORTED_COMMAND.format(
        users_platform=platform.lower(), location=location
    )
  return upgrade
