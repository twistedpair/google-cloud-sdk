# Copyright 2017 Google Inc. All Rights Reserved.
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

"""Util for calling Cloud Filestore API."""

from __future__ import absolute_import
from __future__ import unicode_literals
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.api_lib.util import apis


FILESTORE_API_NAME = 'file'
FILESTORE_API_VERSION = 'v1alpha1'
OPERATIONS_COLLECTION = 'file.projects.locations.operations'


def GetClient():
  """Import and return the appropriate Cloud Filestore client.

  Returns:
    Cloud Filestore client for the appropriate release track.
  """
  return apis.GetClientInstance(FILESTORE_API_NAME, FILESTORE_API_VERSION)


def GetMessages():
  """Import and return the appropriate Filestore messages module."""
  return apis.GetMessagesModule(FILESTORE_API_NAME, FILESTORE_API_VERSION)


def ParseFilestoreConfig(tier=None, description=None, file_share=None,
                         network=None, labels=None):
  """Parses the command line arguments for Create into a config.

  Args:
    tier: the tier.
    description: the description of the instance.
    file_share: the config for the fileshare.
    network: The network(s) for the instance.
    labels: The parsed labels value.

  Returns:
    the configuration that will be used as the request body for creating a Cloud
    Filestore instance.
  """
  messages = GetMessages()
  instance = messages.Instance()

  instance.tier = tier
  instance.labels = labels

  if description:
    instance.description = description

  if instance.volumes is None:
    instance.volumes = []
  if file_share:
    fileshare_config = messages.VolumeConfig(
        name=file_share.get('name'),
        capacityGb=utils.BytesToGb(file_share.get('capacity')))
    instance.volumes.append(fileshare_config)

  if network:
    instance.networks = []
    network_config = messages.NetworkConfig()
    network_config.network = network.get('name')
    if 'reserved-ip-range' in network:
      network_config.reservedIpRange = network['reserved-ip-range']
    instance.networks.append(network_config)
  return instance
