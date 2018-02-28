# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Code that's shared between multiple subnets subcommands."""

from googlecloudsdk.calliope import exceptions


def MakeSubnetworkUpdateRequest(client,
                                subnet_ref,
                                enable_private_ip_google_access=None,
                                add_secondary_ranges=None,
                                remove_secondary_ranges=None,
                                enable_flow_logs=None):
  """Make the appropriate update request for the args.

  Args:
    client: GCE API client
    subnet_ref: Reference to a subnetwork
    enable_private_ip_google_access: Enable/disable access to Google Cloud APIs
      from this subnet for instances without a public ip address.
    add_secondary_ranges: List of secondary IP ranges to add to the subnetwork
      for use in IP aliasing.
    remove_secondary_ranges: List of secondary ranges to remove from the
      subnetwork.
    enable_flow_logs: Enable/disable flow logging for this subnet.

  Returns:
    response, result of sending the update request for the subnetwork
  """
  if enable_private_ip_google_access is not None:
    google_access = (
        client.messages.SubnetworksSetPrivateIpGoogleAccessRequest())
    google_access.privateIpGoogleAccess = enable_private_ip_google_access

    google_access_request = (
        client.messages.ComputeSubnetworksSetPrivateIpGoogleAccessRequest(
            project=subnet_ref.project,
            region=subnet_ref.region,
            subnetwork=subnet_ref.Name(),
            subnetworksSetPrivateIpGoogleAccessRequest=google_access))
    return client.MakeRequests([(client.apitools_client.subnetworks,
                                 'SetPrivateIpGoogleAccess',
                                 google_access_request)])
  elif add_secondary_ranges is not None:
    subnetwork = client.MakeRequests(
        [(client.apitools_client.subnetworks,
          'Get', client.messages.ComputeSubnetworksGetRequest(
              **subnet_ref.AsDict()))])[0]

    for secondary_range in add_secondary_ranges:
      for range_name, ip_cidr_range in sorted(secondary_range.iteritems()):
        subnetwork.secondaryIpRanges.append(
            client.messages.SubnetworkSecondaryRange(
                rangeName=range_name, ipCidrRange=ip_cidr_range))

    return client.MakeRequests(
        [CreateSubnetworkPatchRequest(client, subnet_ref, subnetwork)])
  elif remove_secondary_ranges is not None:
    subnetwork = client.MakeRequests(
        [(client.apitools_client.subnetworks,
          'Get', client.messages.ComputeSubnetworksGetRequest(
              **subnet_ref.AsDict()))])[0]

    for name in remove_secondary_ranges[0]:
      if name not in [r.rangeName for r in subnetwork.secondaryIpRanges]:
        raise exceptions.UnknownArgumentException(
            'remove-secondary-ranges', 'Subnetwork does not have a range {}, '
            'present ranges are {}.'.format(
                name, [r.rangeName for r in subnetwork.secondaryIpRanges]))
    subnetwork.secondaryIpRanges = [
        r for r in subnetwork.secondaryIpRanges
        if r.rangeName not in remove_secondary_ranges[0]
    ]

    cleared_fields = []
    if not subnetwork.secondaryIpRanges:
      cleared_fields.append('secondaryIpRanges')
    with client.apitools_client.IncludeFields(cleared_fields):
      return client.MakeRequests(
          [CreateSubnetworkPatchRequest(client, subnet_ref, subnetwork)])
  elif enable_flow_logs is not None:
    subnetwork = client.MakeRequests(
        [(client.apitools_client.subnetworks,
          'Get', client.messages.ComputeSubnetworksGetRequest(
              **subnet_ref.AsDict()))])[0]

    subnetwork.enableFlowLogs = enable_flow_logs
    return client.MakeRequests(
        [CreateSubnetworkPatchRequest(client, subnet_ref, subnetwork)])

  return client.MakeRequests([])


def CreateSubnetworkPatchRequest(client, subnet_ref, subnetwork_resource):
  patch_request = client.messages.ComputeSubnetworksPatchRequest(
      project=subnet_ref.project,
      subnetwork=subnet_ref.subnetwork,
      region=subnet_ref.region,
      subnetworkResource=subnetwork_resource)
  return (client.apitools_client.subnetworks, 'Patch', patch_request)
