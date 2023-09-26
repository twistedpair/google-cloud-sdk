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
"""Utils for VMware Engine private-clouds clusters commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections

from googlecloudsdk.core import exceptions


class InvalidNodeConfigsProvidedError(exceptions.Error):

  def __init__(self, details):
    super(InvalidNodeConfigsProvidedError, self).__init__(
        'INVALID_ARGUMENT: {}'.format(details)
    )


NodeTypeConfig = collections.namedtuple(
    typename='NodeTypeConfig',
    field_names=['type', 'count', 'custom_core_count'],
)


def FindDuplicatedTypes(types):
  type_counts = collections.Counter(types)
  return [node_type for node_type, count in type_counts.items() if count > 1]


def ParseNodesConfigsParameters(nodes_configs):
  requested_node_types = [config['type'] for config in nodes_configs]

  duplicated_types = FindDuplicatedTypes(requested_node_types)
  if duplicated_types:
    raise InvalidNodeConfigsProvidedError(
        'types: {} provided more than once.'.format(duplicated_types)
    )

  return [
      NodeTypeConfig(
          config['type'], config['count'], config.get('custom-core-count', 0)
      )
      for config in nodes_configs
  ]
