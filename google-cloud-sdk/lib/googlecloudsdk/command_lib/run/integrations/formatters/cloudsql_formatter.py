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
"""CloudSQL integration formatter for the describe command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.command_lib.run.integrations.formatters import base_formatter
from googlecloudsdk.command_lib.run.integrations.formatters import states
from googlecloudsdk.core.resource import custom_printer_base as cp


class CloudSQLFormatter(base_formatter.BaseFormatter):
  """CloudSQL formatter."""

  def TransformConfig(self, record):
    """Prints the config of the integration.

    Args:
      record: integration_printer.Record class that only holds data.

    Returns:
      The formatted output to be printed to the console.
    """
    res_config = record.config.get('cloudsql', {})
    version = ('Database version', res_config.get('version'))
    tier = ('Instance tier', res_config.get('settings').get('tier'))

    labeled = [
        version,
        tier
    ]
    return cp.Labeled(labeled)

  def TransformComponentStatus(self, record):
    """Prints the status of the integration components.

    Args:
      record: integration_printer.Record class that only holds data.

    Returns:
      The formatted output to be printed to the console.
    """
    resources = record.status.get('resourceComponentStatuses', {})
    db_instance = _DBInstanceFromResources(resources)
    secret = _SecretFromResources(resources)

    return cp.Labeled([
        cp.Lines([
            ('Database Instance ({})'.format(db_instance.get('name', ''))),
            cp.Labeled([
                ('Console link', db_instance.get('consoleLink', 'n/a')),
                ('Resource Status', db_instance.get('state', 'n/a')),
            ]),
        ]),
        cp.Lines([
            ('Secret ({})'.format(secret.get('name', ''))),
            cp.Labeled([
                ('Console link', secret.get('consoleLink', 'n/a')),
                ('Resource Status', secret.get('state', 'n/a')),
            ]),
        ])
    ])

  def CallToAction(self, record):
    """Call to action to use generated environment variables.

    If the resource state is not ACTIVE then the resource is not ready for
    use and the call to action will not be shown.

    Args:
      record: integration_printer.Record class that just holds data.

    Returns:
      A formatted string of the call to action message,
      or None if no call to action is required.
    """
    state = record.status.get('state', '')
    if state != states.ACTIVE:
      return None

    return ('To connect to the CloudSQL instance utilize the '
            'environment variables {}, {}, {}, and {}. These have '
            'been added to the Cloud Run service for you.'.format(
                'DB_NAME', 'DB_SOCKET', 'DB_USER', 'DB_PASS'))


def _DBInstanceFromResources(resources):
  for res in resources:
    if res.get('type', None) == 'google_sql_database_instance':
      return res

  return {}


def _SecretFromResources(resources):
  for res in resources:
    if res.get('type', None) == 'google_secret_manager_secret':
      return res

  return {}
