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


class DomainRoutingFormatter(base_formatter.BaseFormatter):
  """Format logics for custom domain integration."""

  def TransformConfig(self, record):
    """Print the config of the integration.

    Args:
      record: dict, the integration.

    Returns:
      The printed output.
    """
    res_config = record.get('config', {}).get('router', {})
    labeled = []
    for domain_config in res_config.get('domains') or []:
      domain = domain_config.get('domain') or ''
      for route in domain_config.get('routes', []):
        service = self._GetServiceName(route.get('ref', ''))
        for path in route.get('paths', []):
          labeled.append((domain+path, service))
    return cp.Labeled(labeled)

  def TransformComponentStatus(self, record):
    """Print the component status of the integration.

    Args:
      record: dict, the integration.

    Returns:
      The printed output.
    """
    resource_config = record.get('config', {})
    resource_status = record.get('status', {})
    resource_components = resource_status.get('resourceComponentStatuses', {})
    details = resource_status.get('routerDetails', {})
    components = [
        ('Console link', resource_status.get('consoleLink', 'n/a')),
        ('Frontend', details.get('ipAddress', 'n/a')),
    ]
    for component in self._GetSSLStatuses(resource_components, resource_config):
      name, status = component
      components.append(('SSL Certificate [{}]'.format(name), status))

    return cp.Labeled([
        cp.Lines([
            ('Google Cloud Load Balancer ({})'.format(
                self._GetGCLBName(resource_components))),
            cp.Labeled(components),
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
    resource_config = record.get('config', {})
    resource_status = record.get('status')
    if not resource_status:
      return None

    resource_components = resource_status.get('resourceComponentStatuses', {})
    ip = resource_status.get('routerDetails', {}).get('ipAddress')
    if not ip:
      return None

    # Find domains with non active ssl cert
    missing_domains = []
    max_domain_length = 0
    for domain, status in self._GetSSLStatuses(resource_components,
                                               resource_config):
      if status != states.ACTIVE:
        missing_domains.append(domain)
        max_domain_length = max(max_domain_length, len(domain))
    if not missing_domains:
      return None

    # Prepare domain record and padding
    records = ''
    for domain in missing_domains:
      padded_domain = domain + ' ' * (max_domain_length - len(domain))
      records = records + '    {}  3600  A     {}\n'.format(padded_domain, ip)

    # Assemble CTA message
    padding_string = ' ' * (max_domain_length - len('NAME'))
    con = console_attr.GetConsoleAttr()
    return ('{0} To complete the process, please ensure the following '
            'DNS records are configured for the domains:\n'
            '    NAME{2}  TTL   TYPE  DATA\n'
            '{1}'
            'It can take up to an hour for the certificate to be provisioned.'
            .format(con.Colorize('!', 'yellow'), records, padding_string))

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

  def _FindResourceByType(self, resources, rtype):
    if not resources:
      return None
    for resource in resources:
      if resource.get('type') == rtype:
        return resource

  def _GetSSLStatuses(self, resource_components, resource_config):
    ssl_cert_components = self._FindAllResourceByType(
        resource_components, 'google_compute_managed_ssl_certificate')
    statuses = []
    for component in ssl_cert_components:
      gussed_domain = self._GuessDomainFromSSLComponentName(
          component.get('name'))
      matched_domain = None
      for domain_config in resource_config.get('router', {}).get('domains', []):
        res_domain = domain_config.get('domain', '')
        if gussed_domain == res_domain:
          matched_domain = res_domain
        elif res_domain.startswith(gussed_domain) and matched_domain is None:
          matched_domain = res_domain
      if matched_domain is None:
        matched_domain = gussed_domain
      statuses.append(
          (matched_domain,
           component.get('state', states.UNKNOWN)))
    return statuses

  def _FindAllResourceByType(self, resources, rtype):
    found = []
    if not resources:
      return found
    for resource in resources:
      if resource.get('type') == rtype:
        found.append(resource)
    return found

  def _GuessDomainFromSSLComponentName(self, name):
    parts = name.replace('d--', '').split('-')
    # skip prefix and suffix in the name.
    # The first two are custom-domains, the last two are <region hash>-cert.
    # if the domain is too long, the suffix will become
    # <region hash>-cert-<length hash>. So account for that accordingly.
    end_index = -2
    if parts[len(parts)-1] != 'cert':
      end_index = -3
    return '.'.join(parts[2:end_index])
