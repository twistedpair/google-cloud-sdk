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
from googlecloudsdk.command_lib.run.integrations.formatters import states
from googlecloudsdk.core.console import console_attr
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
    resource_status = record.get('status', {})
    resource_components = resource_status.get('resourceComponentStatuses', {})
    details = resource_status.get('routerDetails', {})
    return cp.Labeled([
        cp.Lines([
            ('Google Cloud Load Balancer ({})'.format(
                self._GetGCLBName(resource_components))),
            cp.Labeled([
                ('Console link', resource_status.get('consoleLink', 'n/a')),
                ('Frontend', details.get('ipAddress', 'n/a')),
                ('SSL Certificate',
                 self.PrintStatus(self._GetSSLStatus(resource_components))),
            ]),
        ])
    ])

  def CallToAction(self, record):
    """Call to action to configure IP for the domain.

    Args:
      record: dict, the integration.

    Returns:
      A formatted string of the call to action message,
      or None if no call to action is required.
    """
    resource_config = record.get('config')
    resource_status = record.get('status')
    if not resource_status or not resource_status:
      return None

    domain = resource_config.get('router', {}).get('domain')
    resource_components = resource_status.get('resourceComponentStatuses', {})
    ssl_status = self._GetSSLStatus(resource_components)
    ip = resource_status.get('routerDetails', {}).get('ipAddress')
    if domain and ip and ssl_status != states.ACTIVE:
      domain_padding = len(domain) - len('NAME')
      padding_string = ' ' * domain_padding
      con = console_attr.GetConsoleAttr()
      return ('{0} To complete the process, please ensure the following '
              'DNS records are configured for the domain "{1}":\n'
              '    NAME{2}  TTL   TYPE  DATA\n'
              '    {1}  3600  A     {3}\n'
              'It can take up to an hour for the certificate to be provisioned.'
              .format(con.Colorize('!', 'yellow'), domain, padding_string, ip))
    return None

  def _GetServiceName(self, ref):
    parts = ref.split('/')
    if len(parts) == 2 and parts[0] == 'service':
      ref = parts[1]
    return ref

  def _GetGCLBName(self, resource_components):
    url_map = self._FindResourceByType(resource_components,
                                       'google_compute_url_map')
    if url_map:
      return url_map.get('name', 'n/a')
    return 'n/a'

  def _GetSSLStatus(self, resource_components):
    ssl_cert = self._FindResourceByType(
        resource_components, 'google_compute_managed_ssl_certificate')
    if ssl_cert:
      return ssl_cert.get('state', states.UNKNOWN)
    return states.UNKNOWN

  def _FindResourceByType(self, resources, rtype):
    if not resources:
      return None
    for resource in resources:
      if resource.get('type') == rtype:
        return resource
