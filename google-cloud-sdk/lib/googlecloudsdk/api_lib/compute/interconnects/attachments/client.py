# -*- coding: utf-8 -*- #
# Copyright 2017 Google LLC. All Rights Reserved.
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
"""Interconnect Attachment."""

import copy
import json

from apitools.base.py import encoding
from googlecloudsdk.command_lib.compute.interconnects.attachments import flags
from googlecloudsdk.core import log


class InterconnectAttachment(object):
  """Abstracts Interconnect attachment resource."""

  _BANDWIDTH_CONVERSION = {
      'bps-50m': 'BPS_50M',
      'bps-100m': 'BPS_100M',
      'bps-200m': 'BPS_200M',
      'bps-300m': 'BPS_300M',
      'bps-400m': 'BPS_400M',
      'bps-500m': 'BPS_500M',
      'bps-1g': 'BPS_1G',
      'bps-2g': 'BPS_2G',
      'bps-5g': 'BPS_5G',
      'bps-10g': 'BPS_10G',
      'bps-20g': 'BPS_20G',
      'bps-50g': 'BPS_50G',
      'bps-100g': 'BPS_100G',
      '50m': 'BPS_50M',
      '100m': 'BPS_100M',
      '200m': 'BPS_200M',
      '300m': 'BPS_300M',
      '400m': 'BPS_400M',
      '500m': 'BPS_500M',
      '1g': 'BPS_1G',
      '2g': 'BPS_2G',
      '5g': 'BPS_5G',
      '10g': 'BPS_10G',
      '20g': 'BPS_20G',
      '50g': 'BPS_50G',
      '100g': 'BPS_100G',
  }

  _BANDWIDTH_CONVERSION_WITH_400G = copy.deepcopy(_BANDWIDTH_CONVERSION)
  _BANDWIDTH_CONVERSION_WITH_400G.update({
      'bps-400g': 'BPS_400G',
      '400g': 'BPS_400G',
  })

  _EDGE_AVAILABILITY_DOMAIN_CONVERSION = {
      'availability-domain-1': 'AVAILABILITY_DOMAIN_1',
      'availability-domain-2': 'AVAILABILITY_DOMAIN_2',
      'any': 'AVAILABILITY_DOMAIN_ANY'
  }

  def __init__(self, ref, compute_client=None):
    self.ref = ref
    self._compute_client = compute_client

  @property
  def _client(self):
    return self._compute_client.apitools_client

  @property
  def _messages(self):
    return self._compute_client.messages

  def _MakeCreateRequestTuple(
      self,
      description,
      interconnect,
      router,
      attachment_type,
      edge_availability_domain,
      admin_enabled,
      bandwidth,
      pairing_key,
      vlan_tag_802_1q,
      candidate_subnets,
      partner_metadata,
      partner_asn,
      validate_only,
      mtu,
      encryption,
      ipsec_internal_addresses,
      stack_type,
      candidate_ipv6_subnets,
      cloud_router_ipv6_interface_id,
      customer_router_ipv6_interface_id,
      subnet_length,
      multicast_enabled,
      candidate_cloud_router_ip_address,
      candidate_customer_router_ip_address,
      candidate_cloud_router_ipv6_address,
      candidate_customer_router_ipv6_address,
      network,
      geneve_vni,
      default_appliance_ip_address,
      tunnel_endpoint_ip_address,
      resource_manager_tags,
  ):
    """Make an interconnect attachment insert request."""
    interconnect_self_link = None
    if interconnect is not None:
      interconnect_self_link = interconnect.SelfLink()
    router_self_link = None
    if router is not None:
      router_self_link = router.SelfLink()
    attachment = self._messages.InterconnectAttachment(
        name=self.ref.Name(),
        description=description,
        interconnect=interconnect_self_link,
        router=router_self_link,
        type=attachment_type,
        edgeAvailabilityDomain=edge_availability_domain,
        adminEnabled=admin_enabled,
        bandwidth=bandwidth,
        pairingKey=pairing_key,
        vlanTag8021q=vlan_tag_802_1q,
        candidateSubnets=candidate_subnets,
        partnerMetadata=partner_metadata,
        partnerAsn=partner_asn)
    if mtu is not None:
      attachment.mtu = mtu
    if encryption is not None:
      attachment.encryption = (
          self._messages.InterconnectAttachment.EncryptionValueValuesEnum(
              encryption))
    if ipsec_internal_addresses is not None:
      attachment.ipsecInternalAddresses = ipsec_internal_addresses

    if stack_type is not None:
      attachment.stackType = (
          self._messages.InterconnectAttachment.StackTypeValueValuesEnum(
              stack_type
          )
      )
    if candidate_ipv6_subnets is not None:
      attachment.candidateIpv6Subnets = candidate_ipv6_subnets
    if cloud_router_ipv6_interface_id is not None:
      attachment.cloudRouterIpv6InterfaceId = cloud_router_ipv6_interface_id
    if customer_router_ipv6_interface_id is not None:
      attachment.customerRouterIpv6InterfaceId = (
          customer_router_ipv6_interface_id
      )
    if subnet_length is not None:
      attachment.subnetLength = subnet_length
    if multicast_enabled is not None:
      attachment.multicastEnabled = multicast_enabled
    if candidate_cloud_router_ip_address is not None:
      attachment.candidateCloudRouterIpAddress = (
          candidate_cloud_router_ip_address
      )
    if candidate_customer_router_ip_address is not None:
      attachment.candidateCustomerRouterIpAddress = (
          candidate_customer_router_ip_address
      )
    if candidate_cloud_router_ipv6_address is not None:
      attachment.candidateCloudRouterIpv6Address = (
          candidate_cloud_router_ipv6_address
      )
    if candidate_customer_router_ipv6_address is not None:
      attachment.candidateCustomerRouterIpv6Address = (
          candidate_customer_router_ipv6_address
      )
    if network is not None:
      if attachment.l2Forwarding is None:
        attachment.l2Forwarding = (
            self._messages.InterconnectAttachmentL2Forwarding()
        )
      attachment.l2Forwarding.network = network.SelfLink()
    if tunnel_endpoint_ip_address is not None:
      if attachment.l2Forwarding is None:
        attachment.l2Forwarding = (
            self._messages.InterconnectAttachmentL2Forwarding()
        )
      attachment.l2Forwarding.tunnelEndpointIpAddress = (
          tunnel_endpoint_ip_address
      )
    if geneve_vni is not None:
      attachment.l2Forwarding.geneveHeader = (
          self._messages.InterconnectAttachmentL2ForwardingGeneveHeader(
              vni=geneve_vni,
          )
      )
    if default_appliance_ip_address is not None:
      attachment.l2Forwarding.defaultApplianceIpAddress = (
          default_appliance_ip_address
      )
    if resource_manager_tags is not None:
      attachment.params = flags.CreateInterconnectAttachmentParams(
          self._messages, resource_manager_tags
      )

    if validate_only is not None:
      return (self._client.interconnectAttachments, 'Insert',
              self._messages.ComputeInterconnectAttachmentsInsertRequest(
                  project=self.ref.project,
                  region=self.ref.region,
                  validateOnly=validate_only,
                  interconnectAttachment=attachment))
    return (self._client.interconnectAttachments, 'Insert',
            self._messages.ComputeInterconnectAttachmentsInsertRequest(
                project=self.ref.project,
                region=self.ref.region,
                interconnectAttachment=attachment))

  def _MakePatchRequestTuple(
      self,
      description,
      admin_enabled,
      bandwidth,
      partner_metadata,
      mtu=None,
      stack_type=None,
      candidate_ipv6_subnets=None,
      cloud_router_ipv6_interface_id=None,
      customer_router_ipv6_interface_id=None,
      labels=None,
      label_fingerprint=None,
      candidate_cloud_router_ipv6_address=None,
      candidate_customer_router_ipv6_address=None,
      geneve_vni=None,
      default_appliance_ip_address=None,
  ):
    """Make an interconnect attachment patch request."""
    interconnect_attachment = self._messages.InterconnectAttachment(
        name=self.ref.Name(),
        description=description,
        adminEnabled=admin_enabled,
        bandwidth=bandwidth,
        partnerMetadata=partner_metadata)
    if mtu is not None:
      interconnect_attachment.mtu = mtu
    if stack_type is not None:
      interconnect_attachment.stackType = (
          self._messages.InterconnectAttachment.StackTypeValueValuesEnum(
              stack_type
          )
      )
    if labels is not None:
      interconnect_attachment.labels = labels
    if label_fingerprint is not None:
      interconnect_attachment.labelFingerprint = label_fingerprint
    if candidate_ipv6_subnets is not None:
      interconnect_attachment.candidateIpv6Subnets = candidate_ipv6_subnets
    if cloud_router_ipv6_interface_id is not None:
      interconnect_attachment.cloudRouterIpv6InterfaceId = (
          cloud_router_ipv6_interface_id
      )
    if customer_router_ipv6_interface_id is not None:
      interconnect_attachment.customerRouterIpv6InterfaceId = (
          customer_router_ipv6_interface_id
      )
    if candidate_cloud_router_ipv6_address is not None:
      interconnect_attachment.candidateCloudRouterIpv6Address = (
          candidate_cloud_router_ipv6_address
      )
    if candidate_customer_router_ipv6_address is not None:
      interconnect_attachment.candidateCustomerRouterIpv6Address = (
          candidate_customer_router_ipv6_address
      )
    if geneve_vni is not None:
      if interconnect_attachment.l2Forwarding is None:
        interconnect_attachment.l2Forwarding = (
            self._messages.InterconnectAttachmentL2Forwarding()
        )
        interconnect_attachment.l2Forwarding.geneveHeader = (
            self._messages.InterconnectAttachmentL2ForwardingGeneveHeader(
                vni=geneve_vni,
            )
        )
    if default_appliance_ip_address is not None:
      if interconnect_attachment.l2Forwarding is None:
        interconnect_attachment.l2Forwarding = (
            self._messages.InterconnectAttachmentL2Forwarding()
        )
      interconnect_attachment.l2Forwarding.defaultApplianceIpAddress = (
          default_appliance_ip_address
      )
    return (self._client.interconnectAttachments, 'Patch',
            self._messages.ComputeInterconnectAttachmentsPatchRequest(
                project=self.ref.project,
                region=self.ref.region,
                interconnectAttachment=self.ref.Name(),
                interconnectAttachmentResource=interconnect_attachment))

  def _MakeDescribeRequestTuple(self):
    return (self._client.interconnectAttachments, 'Get',
            self._messages.ComputeInterconnectAttachmentsGetRequest(
                project=self.ref.project,
                region=self.ref.region,
                interconnectAttachment=self.ref.Name()))

  def _MakeDeleteRequestTuple(self):
    return (self._client.interconnectAttachments, 'Delete',
            self._messages.ComputeInterconnectAttachmentsDeleteRequest(
                project=self.ref.project,
                region=self.ref.region,
                interconnectAttachment=self.ref.Name()))

  def _MakePatchMappingRequestTuple(
      self,
      vlan_key,
      appliance_name,
      appliance_ip_address,
      inner_vlan_to_appliance_mappings,
  ):
    """Make an interconnect attachment patch request for L2 mappings."""
    attachment = self._messages.InterconnectAttachment(
        name=self.ref.Name(),
        l2Forwarding=self._messages.InterconnectAttachmentL2Forwarding(
            applianceMappings=self._messages.InterconnectAttachmentL2Forwarding.ApplianceMappingsValue(
                additionalProperties=[
                    self._messages.InterconnectAttachmentL2Forwarding.ApplianceMappingsValue.AdditionalProperty(
                        key=vlan_key,
                        value=self._messages.InterconnectAttachmentL2ForwardingApplianceMapping(
                            applianceIpAddress=appliance_ip_address,
                            innerVlanToApplianceMappings=[],
                            name=appliance_name,
                        ),
                    )
                ],
            ),
        ),
    )

    for inner_mapping in inner_vlan_to_appliance_mappings:
      attachment.l2Forwarding.applianceMappings.additionalProperties[
          0
      ].value.innerVlanToApplianceMappings.append(
          self._messages.InterconnectAttachmentL2ForwardingApplianceMappingInnerVlanToApplianceMapping(
              innerVlanTags=inner_mapping.get('innerVlanTags', []),
              innerApplianceIpAddress=inner_mapping.get(
                  'innerApplianceIpAddress', ''
              ),
          )
      )

    return (
        self._client.interconnectAttachments,
        'Patch',
        self._messages.ComputeInterconnectAttachmentsPatchRequest(
            project=self.ref.project,
            region=self.ref.region,
            interconnectAttachment=self.ref.Name(),
            interconnectAttachmentResource=attachment,
        ),
    )

  def _MakeRemoveMappingRequestTuple(
      self,
      vlan_key,
  ):
    """Make an interconnect attachment patch request for L2 mappings."""
    def _NullValueEncoder(message):
      def _EncodeApplianceMappings(message):
        mapping = {}

        if message.applianceIpAddress is not None:
          mapping['applianceIpAddress'] = message.applianceIpAddress
        if message.name is not None:
          mapping['name'] = message.name

        mapping['innerVlanToApplianceMappings'] = []
        for inner_mapping in message.innerVlanToApplianceMappings:
          mapping['innerVlanToApplianceMappings'].append({
              'innerVlanTags': list(inner_mapping.innerVlanTags),
              'innerApplianceIpAddress': inner_mapping.innerApplianceIpAddress,
          })

        return mapping

      return json.dumps({
          property.key: (
              _EncodeApplianceMappings(property.value)
              if property.value
              else None
          )
          for property in message.additionalProperties
      })

    def _NullValueDecoder(data):
      def _DecodeApplianceMappings(data):
        value = (
            self._messages.InterconnectAttachmentL2ForwardingApplianceMapping(
                applianceIpAddress=data.get('applianceIpAddress', None),
                innerVlanToApplianceMappings=[],
                name=data.get('name', None),
            )
        )
        for inner_mapping in data.get('innerVlanToApplianceMappings', []):
          value.innerVlanToApplianceMappings.append(
              self._messages.InterconnectAttachmentL2ForwardingApplianceMappingInnerVlanToApplianceMapping(
                  innerVlanTags=inner_mapping.get('innerVlanTags', []),
                  innerApplianceIpAddress=inner_mapping.get(
                      'innerApplianceIpAddress', ''
                  ),
              )
          )
        return value

      py_object = json.loads(data)
      return self._messages.InterconnectAttachmentL2Forwarding.ApplianceMappingsValue(
          additionalProperties=[
              self._messages.InterconnectAttachmentL2Forwarding.ApplianceMappingsValue.AdditionalProperty(
                  key=key,
                  value=_DecodeApplianceMappings(value) if value else None,
              )
              for key, value in py_object.items()
          ]
      )

    encoding.RegisterCustomMessageCodec(
        encoder=_NullValueEncoder, decoder=_NullValueDecoder
    )(self._messages.InterconnectAttachmentL2Forwarding.ApplianceMappingsValue)

    attachment = self._messages.InterconnectAttachment(
        name=self.ref.Name(),
        l2Forwarding=self._messages.InterconnectAttachmentL2Forwarding(
            applianceMappings=self._messages.InterconnectAttachmentL2Forwarding.ApplianceMappingsValue(
                additionalProperties=[
                    self._messages.InterconnectAttachmentL2Forwarding.ApplianceMappingsValue.AdditionalProperty(
                        key=vlan_key,
                        value=None,
                    )
                ],
            ),
        ),
    )

    return (
        self._client.interconnectAttachments,
        'Patch',
        self._messages.ComputeInterconnectAttachmentsPatchRequest(
            project=self.ref.project,
            region=self.ref.region,
            interconnectAttachment=self.ref.Name(),
            interconnectAttachmentResource=attachment,
        ),
    )

  def Create(
      self,
      description='',
      interconnect=None,
      router=None,
      attachment_type=None,
      edge_availability_domain=None,
      admin_enabled=None,
      bandwidth=None,
      pairing_key=None,
      vlan_tag_802_1q=None,
      candidate_subnets=None,
      partner_name=None,
      partner_interconnect=None,
      partner_portal_url=None,
      partner_asn=None,
      mtu=None,
      encryption=None,
      ipsec_internal_addresses=None,
      stack_type=None,
      candidate_ipv6_subnets=None,
      cloud_router_ipv6_interface_id=None,
      customer_router_ipv6_interface_id=None,
      subnet_length=None,
      multicast_enabled=None,
      only_generate_request=False,
      validate_only=None,
      candidate_cloud_router_ip_address=None,
      candidate_customer_router_ip_address=None,
      candidate_cloud_router_ipv6_address=None,
      candidate_customer_router_ipv6_address=None,
      network=None,
      geneve_vni=None,
      default_appliance_ip_address=None,
      tunnel_endpoint_ip_address=None,
      supports_400g=False,
      resource_manager_tags=None,
  ):
    """Create an interconnectAttachment."""
    if edge_availability_domain is not None:
      edge_availability_domain = self._messages.InterconnectAttachment.EdgeAvailabilityDomainValueValuesEnum(
          self._EDGE_AVAILABILITY_DOMAIN_CONVERSION[edge_availability_domain]
      )
    if bandwidth is not None:
      bandwidth_options = (
          self._BANDWIDTH_CONVERSION_WITH_400G
          if supports_400g
          else self._BANDWIDTH_CONVERSION
      )
      bandwidth = (
          self._messages.InterconnectAttachment.BandwidthValueValuesEnum(
              bandwidth_options[bandwidth]
          )
      )
    if attachment_type is not None:
      attachment_type = (
          self._messages.InterconnectAttachment.TypeValueValuesEnum(
              attachment_type))
    if (partner_interconnect is not None or partner_name is not None or
        partner_portal_url is not None):
      partner_metadata = self._messages.InterconnectAttachmentPartnerMetadata(
          interconnectName=partner_interconnect,
          partnerName=partner_name,
          portalUrl=partner_portal_url)
    else:
      partner_metadata = None
    if candidate_subnets is None:
      candidate_subnets = []
    requests = [
        self._MakeCreateRequestTuple(
            description,
            interconnect,
            router,
            attachment_type,
            edge_availability_domain,
            admin_enabled,
            bandwidth,
            pairing_key,
            vlan_tag_802_1q,
            candidate_subnets,
            partner_metadata,
            partner_asn,
            validate_only,
            mtu,
            encryption,
            ipsec_internal_addresses,
            stack_type,
            candidate_ipv6_subnets,
            cloud_router_ipv6_interface_id,
            customer_router_ipv6_interface_id,
            subnet_length,
            multicast_enabled,
            candidate_cloud_router_ip_address,
            candidate_customer_router_ip_address,
            candidate_cloud_router_ipv6_address,
            candidate_customer_router_ipv6_address,
            network,
            geneve_vni,
            default_appliance_ip_address,
            tunnel_endpoint_ip_address,
            resource_manager_tags,
        )
    ]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      if validate_only:
        log.status.Print('Validation was successful.')
      return resources[0]
    return requests

  def Patch(
      self,
      description='',
      admin_enabled=None,
      bandwidth=None,
      partner_name=None,
      partner_interconnect=None,
      partner_portal_url=None,
      labels=None,
      label_fingerprint=None,
      stack_type=None,
      candidate_ipv6_subnets=None,
      cloud_router_ipv6_interface_id=None,
      customer_router_ipv6_interface_id=None,
      only_generate_request=False,
      mtu=None,
      candidate_cloud_router_ipv6_address=None,
      candidate_customer_router_ipv6_address=None,
      geneve_vni=None,
      default_appliance_ip_address=None,
      supports_400g=False,
  ):
    """Patch an interconnectAttachment."""
    if bandwidth:
      bandwidth_options = (
          self._BANDWIDTH_CONVERSION_WITH_400G
          if supports_400g
          else self._BANDWIDTH_CONVERSION
      )
      bandwidth = (
          self._messages.InterconnectAttachment.BandwidthValueValuesEnum(
              bandwidth_options[bandwidth]
          )
      )
    if (partner_interconnect is not None or partner_name is not None or
        partner_portal_url is not None):
      partner_metadata = self._messages.InterconnectAttachmentPartnerMetadata(
          interconnectName=partner_interconnect,
          partnerName=partner_name,
          portalUrl=partner_portal_url)
    else:
      partner_metadata = None
    requests = [
        self._MakePatchRequestTuple(
            description,
            admin_enabled,
            bandwidth,
            partner_metadata,
            mtu,
            stack_type,
            candidate_ipv6_subnets,
            cloud_router_ipv6_interface_id,
            customer_router_ipv6_interface_id,
            labels,
            label_fingerprint,
            candidate_cloud_router_ipv6_address,
            candidate_customer_router_ipv6_address,
            geneve_vni,
            default_appliance_ip_address,
        )
    ]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests

  def Describe(self, only_generate_request=False):
    requests = [self._MakeDescribeRequestTuple()]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests

  def DescribeMapping(self, vlan_key=None, only_generate_request=False):
    """Describe an interconnect attachment L2 inner mapping."""
    requests = [self._MakeDescribeRequestTuple()]
    if only_generate_request:
      return requests

    l2_forwarding = getattr(
        self._compute_client.MakeRequests(requests)[0], 'l2Forwarding', None
    )
    appliance_mapping = getattr(l2_forwarding, 'applianceMappings', None)
    inner_mapping = getattr(appliance_mapping, 'additionalProperties', [])
    if vlan_key is not None:
      for mapping in inner_mapping:
        if mapping.key == vlan_key:
          return {mapping.key: mapping.value}
    return {}

  def ListMapping(self, is_json=False, only_generate_request=False,):
    """List all interconnect attachment L2 inner mappings."""
    requests = [self._MakeDescribeRequestTuple()]
    if only_generate_request:
      return requests
    l2_forwarding = getattr(
        self._compute_client.MakeRequests(requests)[0], 'l2Forwarding', None
    )
    appliance_mapping = getattr(l2_forwarding, 'applianceMappings', None)
    inner_mapping = getattr(appliance_mapping, 'additionalProperties', [])

    if is_json:
      return inner_mapping

    list_results = []
    for mapping in inner_mapping:
      list_results.append({
          'key': mapping.key,
          'name': mapping.value.name,
          'innerApplianceIpAddress': mapping.value.applianceIpAddress,
      })
    return list_results

  def Delete(self, only_generate_request=False):
    requests = [self._MakeDeleteRequestTuple()]
    if not only_generate_request:
      return self._compute_client.MakeRequests(requests)
    return requests

  def UpdateMapping(
      self,
      vlan_key=None,
      appliance_name=None,
      appliance_ip_address=None,
      inner_vlan_to_appliance_mappings=None,
      only_generate_request=False,
  ):
    """Add an interconnectAttachmen L2 appliance mapping."""
    if inner_vlan_to_appliance_mappings is None:
      inner_vlan_to_appliance_mappings = []
    requests = [
        self._MakePatchMappingRequestTuple(
            vlan_key,
            appliance_name,
            appliance_ip_address,
            inner_vlan_to_appliance_mappings,
        )
    ]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests

  def RemoveMapping(
      self,
      vlan_key=None,
      only_generate_request=False,
  ):
    """Remove an interconnectAttachment L2 appliance mapping."""
    requests = [
        self._MakeRemoveMappingRequestTuple(
            vlan_key,
        )
    ]
    if not only_generate_request:
      resources = self._compute_client.MakeRequests(requests)
      return resources[0]
    return requests
