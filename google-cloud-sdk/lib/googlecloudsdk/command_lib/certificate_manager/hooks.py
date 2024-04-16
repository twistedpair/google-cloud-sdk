# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Hooks for Certificate Manager declarative commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.api_lib.certificate_manager import api_client
from googlecloudsdk.core.util import times

DNS_AUTHORIZATIONS_TEMPLATE = "{}/dnsAuthorizations/{}"
ISSUANCE_CONFIG_TEMPLATE = "{}/certificateIssuanceConfigs/{}"
CA_POOL_TEMPLATE = "{}/caPools/{}"


def GetLocation():
  return "global"


def SetAuthorizationURL(ref, args, request):
  """Converts the dns-authorization argument into a relative URL with project name and location.

  Args:
    ref: Reference to the membership object.
    args: Command line arguments.
    request: API request to be issued

  Returns:
    Modified request
  """

  del ref
  if not args:
    return request

  if args.dns_authorizations:
    authorizations = []

    for field in args.dns_authorizations:
      if not field.startswith("projects/"):
        authorizations.append(
            DNS_AUTHORIZATIONS_TEMPLATE.format(request.parent, field))
      else:
        authorizations.append(field)

    request.certificate.managed.dnsAuthorizations = authorizations

  return request


def SetIssuanceConfigURL(ref, args, request):
  """Converts the issuance-config argument into a relative URL with project name and location.

  Args:
    ref: Reference to the membership object.
    args: Command line arguments.
    request: API request to be issued.

  Returns:
    Modified request
  """

  del ref
  if not args:
    return request

  # TODO(b/228342902): Remove once enabled in GA.
  if hasattr(args, "issuance_config"
            ) and args.issuance_config and not args.issuance_config.startswith(
                "projects/"):
    request.certificate.managed.issuanceConfig = ISSUANCE_CONFIG_TEMPLATE.format(
        request.parent, args.issuance_config)

  return request


def SetCAPoolURL(ref, args, request):
  """Converts the ca-pool argument into a relative URL with project name and location.

  Args:
    ref: reference to the membership object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request
  """

  del ref
  if not args:
    return request

  if args.ca_pool:
    if not args.ca_pool.startswith("projects/"):
      request.certificateIssuanceConfig.certificateAuthorityConfig.certificateAuthorityServiceConfig.caPool = CA_POOL_TEMPLATE.format(
          request.parent, args.ca_pool)

  return request


def ParseIso8601LifetimeFlag(value):
  """Parses the ISO 8601 lifetime argument.

  Args:
    value: An ISO 8601 valid value.

  Returns:
    modified value as expected by the API
  """

  return times.FormatDurationForJson(times.ParseDuration(value))


def UpdateTrustConfigAllowlistedCertificates(ref, args, request):
  """Updates allowlisted certificates based on the used flag.

  Args:
    ref: reference to the membership object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request
  """

  del ref
  if not args:
    return request

  if (
      not args.IsSpecified("add_allowlisted_certificates")
      and not args.IsSpecified("remove_allowlisted_certificates")
      and not args.IsSpecified("clear_allowlisted_certificates")
  ):
    return request

  if request.updateMask.find("allowlistedCertificates") == -1:
    if request.updateMask:
      request.updateMask += ","
    request.updateMask += "allowlistedCertificates"

  client = api_client.GetClientInstance()
  service = client.projects_locations_trustConfigs
  messages = client.MESSAGES_MODULE
  get_trust_config_request = (
      messages.CertificatemanagerProjectsLocationsTrustConfigsGetRequest(
          name=request.name
      )
  )
  request.trustConfig.allowlistedCertificates = service.Get(
      get_trust_config_request
  ).allowlistedCertificates

  if args.IsSpecified("remove_allowlisted_certificates"):
    pem_certificates_to_be_removed = set([
        NormalizePemCertificate(ac["pemCertificate"])
        for ac in args.remove_allowlisted_certificates
        if "pemCertificate" in ac
    ])
    request.trustConfig.allowlistedCertificates = [
        ac
        for ac in request.trustConfig.allowlistedCertificates
        if NormalizePemCertificate(ac.pemCertificate)
        not in pem_certificates_to_be_removed
    ]

  if args.IsSpecified("clear_allowlisted_certificates"):
    request.trustConfig.allowlistedCertificates = []

  if args.IsSpecified("add_allowlisted_certificates"):
    request.trustConfig.allowlistedCertificates = (
        request.trustConfig.allowlistedCertificates
        + args.add_allowlisted_certificates
    )

  return request


def NormalizePemCertificate(pem_certificate):
  """Normalizes the PEM certificate for the comparison by removing all whitespace characters.

  Args:
    pem_certificate: PEM certificate to be normalized.

  Returns:
    PEM certificate without whitespace characters.
  """
  return re.sub(r"\s+", "", pem_certificate, flags=re.ASCII)
