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
"""Functions for creating a client to talk to the App Engine Admin API."""

from googlecloudsdk.api_lib.app import operations_util
from googlecloudsdk.api_lib.app.api import appengine_api_client_base as base
from googlecloudsdk.api_lib.app.api import requests
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import resources


class AppengineDomainsApiClient(base.AppengineApiClientBase):
  """Client used by gcloud to communicate with the App Engine API."""

  def __init__(self, client):
    base.AppengineApiClientBase.__init__(self, client)

    self._registry = resources.REGISTRY.Clone()
    self._registry.RegisterApiByName('appengine', self.ApiVersion())

  @classmethod
  def ApiVersion(cls):
    return 'v1beta'

  def CreateDomainMapping(self, domain, certificate_id):
    """Creates a domain mapping for the given application.

    Args:
      domain: str, the custom domain string.
      certificate_id: str, a certificate id for the new domain.

    Returns:
      The created DomainMapping object.
    """
    ssl = self.messages.SslSettings(certificateId=certificate_id)

    domain_mapping = self.messages.DomainMapping(id=domain, sslSettings=ssl)

    request = self.messages.AppengineAppsDomainMappingsCreateRequest(
        parent=self._FormatApp(), domainMapping=domain_mapping)

    operation = requests.MakeRequest(self.client.apps_domainMappings.Create,
                                     request)

    return operations_util.WaitForOperation(self.client.apps_operations,
                                            operation).response

  def DeleteDomainMapping(self, domain):
    """Deletes a domain mapping for the given application.

    Args:
      domain: str, the domain to delete.
    """
    request = self.messages.AppengineAppsDomainMappingsDeleteRequest(
        name=self._FormatDomainMapping(domain))

    operation = requests.MakeRequest(self.client.apps_domainMappings.Delete,
                                     request)

    operations_util.WaitForOperation(self.client.apps_operations, operation)

  def GetDomainMapping(self, domain):
    """Gets a domain mapping for the given application.

    Args:
      domain: str, the domain to retrieve.

    Returns:
      The retrieved DomainMapping object.
    """
    request = self.messages.AppengineAppsDomainMappingsGetRequest(
        name=self._FormatDomainMapping(domain))

    return requests.MakeRequest(self.client.apps_domainMappings.Get, request)

  def ListDomainMappings(self):
    """Lists all domain mappings for the given application.

    Returns:
      A list of DomainMapping objects.
    """
    request = self.messages.AppengineAppsDomainMappingsListRequest(
        parent=self._FormatApp())

    response = requests.MakeRequest(self.client.apps_domainMappings.List,
                                    request)

    return response.domainMappings

  def UpdateDomainMapping(self, domain, certificate_id, no_certificate_id):
    """Updates a domain mapping for the given application.

    Args:
      domain: str, the custom domain string.
      certificate_id: str, a certificate id for the domain.
      no_certificate_id: bool, remove the certificate id from the domain.

    Returns:
      The updated DomainMapping object.
    """
    mask_fields = []
    if certificate_id or no_certificate_id:
      mask_fields.append('sslSettings.certificateId')

    ssl = self.messages.SslSettings(certificateId=certificate_id)

    domain_mapping = self.messages.DomainMapping(id=domain, sslSettings=ssl)

    if not mask_fields:
      raise exceptions.MinimumArgumentException(
          ['--[no-]certificate-id'],
          'Please specify at least one attribute to the domain-mapping update.')

    request = self.messages.AppengineAppsDomainMappingsPatchRequest(
        name=self._FormatDomainMapping(domain),
        domainMapping=domain_mapping,
        updateMask=','.join(mask_fields))

    operation = requests.MakeRequest(self.client.apps_domainMappings.Patch,
                                     request)

    return operations_util.WaitForOperation(self.client.apps_operations,
                                            operation).response

  def ListVerifiedDomains(self):
    """Lists all domains verified by the current user.

    Returns:
      A list of AuthorizedDomain objects.
    """
    request = self.messages.AppengineAppsAuthorizedDomainsListRequest(
        parent=self._FormatApp())

    response = requests.MakeRequest(self.client.apps_authorizedDomains.List,
                                    request)

    return response.domains

  def _FormatDomainMapping(self, domain):
    res = self._registry.Parse(
        domain,
        params={'appsId': self.project},
        collection='appengine.apps.domainMappings')
    return res.RelativeName()


class AppengineDomainsApiAlphaClient(AppengineDomainsApiClient):
  """Client used by gcloud to communicate with the App Engine API."""

  @classmethod
  def ApiVersion(cls):
    return 'v1alpha'

  def CreateDomainMapping(self, domain, certificate_id, no_managed_certificate):
    """Creates a domain mapping for the given application.

    Args:
      domain: str, the custom domain string.
      certificate_id: str, a certificate id for the new domain.
      no_managed_certificate: bool, don't automatically provision a certificate.

    Returns:
      The created DomainMapping object.
    """
    ssl = self.messages.SslSettings(certificateId=certificate_id)

    domain_mapping = self.messages.DomainMapping(id=domain, sslSettings=ssl)

    request = self.messages.AppengineAppsDomainMappingsCreateRequest(
        parent=self._FormatApp(),
        domainMapping=domain_mapping,
        noManagedCertificate=no_managed_certificate)

    operation = requests.MakeRequest(self.client.apps_domainMappings.Create,
                                     request)

    return operations_util.WaitForOperation(self.client.apps_operations,
                                            operation).response

  def UpdateDomainMapping(self,
                          domain,
                          certificate_id,
                          no_certificate_id,
                          no_managed_certificate=None):
    """Updates a domain mapping for the given application.

    Args:
      domain: str, the custom domain string.
      certificate_id: str, a certificate id for the domain.
      no_certificate_id: bool, remove the certificate id from the domain.
      no_managed_certificate: bool, don't automatically provision a certificate.

    Returns:
      The updated DomainMapping object.
    """
    mask_fields = []
    if certificate_id or no_certificate_id:
      mask_fields.append('sslSettings.certificateId')
    if no_managed_certificate:
      mask_fields.append('noManagedCertificate')

    ssl = self.messages.SslSettings(certificateId=certificate_id)

    domain_mapping = self.messages.DomainMapping(id=domain, sslSettings=ssl)

    if not mask_fields:
      raise exceptions.MinimumArgumentException(
          ['--[no-]certificate-id', '--no_managed_certificate'],
          'Please specify at least one attribute to the domain-mapping update.')

    request = self.messages.AppengineAppsDomainMappingsPatchRequest(
        name=self._FormatDomainMapping(domain),
        noManagedCertificate=no_managed_certificate,
        domainMapping=domain_mapping,
        updateMask=','.join(mask_fields))

    operation = requests.MakeRequest(self.client.apps_domainMappings.Patch,
                                     request)

    return operations_util.WaitForOperation(self.client.apps_operations,
                                            operation).response
