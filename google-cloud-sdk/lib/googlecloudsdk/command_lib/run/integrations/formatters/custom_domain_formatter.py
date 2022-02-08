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
"""Custom domain formatter for Cloud Run Integrations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.command_lib.run.integrations.formatters import base_formatter
from googlecloudsdk.core.resource import custom_printer_base as cp


class CustomDomainFormatter(base_formatter.BaseFormatter):
  """Format logics for custom domain integration."""

  def TransformConfig(self, record):
    """Print the config of the integration.

    Args:
      record: dict, the integration.

    Returns:
      The printed output.
    """
    res_config = record.get('config', {}).get('router', {})
    labeled = [
        ('Domain', res_config.get('domain', '')),
    ]
    if 'default-route' in res_config:
      labeled.append(('Path', '/*'))
      labeled.append(
          ('Service',
           self._GetServiceName(res_config.get('default-route',
                                               {}).get('ref', ''))))
    for r in res_config.get('routes', []):
      labeled.append(('Path', ','.join(r.get('paths', ''))))
      labeled.append(('Service', self._GetServiceName(r.get('ref', ''))))
    return cp.Labeled(labeled)

  def TransformComponentStatus(self, record):
    """Print the component status of the integration.

    Args:
      record: dict, the integration.

    Returns:
      The printed output.
    """
    gcp_resources = record.get('status', {}).get('gcpResource', {})
    details = record.get('status', {}).get('routerDetails', {})

    return cp.Labeled([
        cp.Lines([
            ('Google Cloud Load Balancer ({})'.format(
                self._GetGCLBName(gcp_resources))),
            cp.Labeled([
                ('Frontend', details.get('ipAddress', 'n/a')),
                ('SSL Certificate',
                 self.PrintStatus(self._GetSSLStatus(gcp_resources))),
            ]),
        ])
    ])

  def _GetServiceName(self, ref):
    parts = ref.split('/')
    if len(parts) == 2 and parts[0] == 'service':
      ref = parts[1]
    return ref

  def _GetGCLBName(self, gcp_resources):
    url_map = self._FindResourceByType(gcp_resources, 'google_compute_url_map')
    if url_map:
      return url_map.get('gcpResourceName', 'n/a')
    return 'n/a'

  def _GetSSLStatus(self, gcp_resources):
    ssl_cert = self._FindResourceByType(
        gcp_resources, 'google_compute_managed_ssl_certificate')
    if ssl_cert:
      return self.GetResourceState(ssl_cert)
    return 'UNKNOWN'

  def _FindResourceByType(self, resources, rtype):
    if not resources:
      return None
    for resource in resources:
      if resource.get('type') == rtype:
        return resource
