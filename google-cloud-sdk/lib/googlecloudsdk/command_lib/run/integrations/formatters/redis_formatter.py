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
"""Redis formatter for Cloud Run Integrations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.command_lib.run.integrations.formatters import base_formatter
from googlecloudsdk.core.resource import custom_printer_base as cp

_REDIS_INSTANCE_TYPE = 'google_redis_instance'
_VPC_INSTANCE_TYPE = 'google_vpc_access_connector'


class RedisFormatter(base_formatter.BaseFormatter):
  """Format logics for redis integration."""

  def TransformConfig(self, record):
    """Print the config of the integration.

    Args:
      record: dict, the integration.

    Returns:
      The printed output.
    """
    res_config = record.get('config', {}).get('redis', {}).get('instance', {})

    labeled = [('Memory Size GB', res_config.get('memory-size-gb'))]
    if 'tier' in res_config:
      labeled.append(('Tier', res_config.get('tier')))
    if 'version' in res_config:
      labeled.append(('Version', res_config.get('version')))

    return cp.Labeled(labeled)

  def TransformComponentStatus(self, record):
    """Print the component status of the integration.

    Args:
      record: dict, the integration.

    Returns:
      The printed output.
    """
    resource_status = record.get('status', {})
    resources = resource_status.get('resourceComponentStatuses', {})
    redis = self._RedisFromResources(resources)
    vpc = self._VpcFromResources(resources)
    return cp.Labeled([
        cp.Lines([
            ('MemoryStore Redis ({})'.format(
                redis.get('name', ''))),
            cp.Labeled([
                ('Console link', redis.get('consoleLink', 'n/a')),
                ('Resource Status', redis.get('state', 'n/a')),
            ]),
        ]),
        cp.Lines([
            ('Serverless VPC Connector ({})'.format(vpc.get('name', ''))),
            cp.Labeled([
                ('Console link', vpc.get('consoleLink', 'n/a')),
            ]),
        ])
    ])

  def CallToAction(self, record):
    """Call to action to use generated environment variables.

    Args:
      record: dict, the integration.

    Returns:
      A formatted string of the call to action message,
      or None if no call to action is required.
    """
    ## TODO(b/222759433):Once more than one redis instance is supported print
    ## correct variables. This will not be trivial since binding is not
    ## contained with redis resource.

    return ('To connect to the Redis instance utilize the '
            'environment variables {} and {}. These have '
            'been added to the Cloud Run service for you.'.format(
                'REDISHOST', 'REDISPORT'))

  def _VpcFromResources(self, records):
    for rec in records:
      if rec.get('type', None) == _VPC_INSTANCE_TYPE:
        return rec

    return {}

  def _RedisFromResources(self, records):
    for rec in records:
      if rec.get('type', None) == _REDIS_INSTANCE_TYPE:
        return rec

    return {}
