# -*- coding: utf-8 -*- #
# Copyright 2018 Google LLC. All Rights Reserved.
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
"""Flags for the `compute network-endpoint-groups` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute import flags as compute_flags


def MakeNetworkEndpointGroupsArg(support_global_scope=False):
  return compute_flags.ResourceArgument(
      resource_name='network endpoint group',
      zonal_collection='compute.networkEndpointGroups',
      global_collection='compute.globalNetworkEndpointGroups'
      if support_global_scope else None,
      zone_explanation=compute_flags.ZONE_PROPERTY_EXPLANATION)


def AddNetworkEndpointGroupType(parser, support_neg_type):
  """Adds NEG type argument for creating network endpoint group."""
  if support_neg_type:
    base.ChoiceArgument(
        '--neg-type',
        hidden=True,
        choices=['load-balancing'],
        default='load-balancing',
        help_str='The type of network endpoint group to create.').AddToParser(
            parser)


def AddNetworkEndpointType(parser, support_global_scope, support_hybrid_neg,
                           support_l4ilb_neg):
  """Adds endpoint type argument for creating network endpoint groups."""
  endpoint_type_choices = ['gce-vm-ip-port']
  endpoint_type_hidden = True
  if support_global_scope:
    endpoint_type_choices.append('internet-ip-port')
    endpoint_type_choices.append('internet-fqdn-port')
    endpoint_type_hidden = False
  if support_hybrid_neg:
    endpoint_type_choices.append('non-gcp-private-ip-port')
    endpoint_type_hidden = False
  if support_l4ilb_neg:
    endpoint_type_choices.append('gce-vm-primary-ip')
    endpoint_type_hidden = False

  help_text = 'The network endpoint type.'
  if support_global_scope or support_hybrid_neg or support_l4ilb_neg:
    help_text = """\
      Determines the spec of endpoints attached to this group.

      * `GCE_VM_IP_PORT`

          Endpoint IP address must belong to a VM in Google Compute Engine
          (either the primary IP or as part of an aliased IP range).
          The `--default-port` must be specified or every network endpoint
          in the network endpoint group must have a port specified.
          """
  if support_global_scope:
    help_text += """\

      * `INTERNET_IP_PORT`

          Endpoint IP address must be publicly routable address. The default
          port will be used if specified. If the default port is not
          specified, the well known port for your backend protocol will be
          used as the default port (80 for http,  443 for https).

      * `INTERNET_FQDN_PORT`

          Endpoint FQDN must be resolvable to a public IP address via public
          DNS. The default port will be used if specified. If the default
          port is not specified, the well known port for your backend
          protocol will be used as the default port (80 for http, 443 for
          https).
    """
  if support_hybrid_neg:
    help_text += """\

      * `NON_GCP_PRIVATE_IP_PORT`

          Endpoint IP address must belong to a VM not in Google Compute
          Engine and must be routable using a cloud router over VPN or an
          Interconnect. In this case the NEG must be zonal. The
          `--default-port` must be specified or every network endpoint in
          the network endpoint group must have a port specified.
    """
  if support_l4ilb_neg:
    help_text += """\

      * `GCE_VM_PRIMARY_IP`

          Endpoint IP address must be the primary IP of a VM's primary
          network interface in Google Compute Engine.
    """

  base.ChoiceArgument(
      '--network-endpoint-type',
      hidden=endpoint_type_hidden,
      choices=endpoint_type_choices,
      default='gce-vm-ip-port',
      help_str=help_text).AddToParser(parser)


def AddNetwork(parser, support_global_scope, support_hybrid_neg,
               support_l4ilb_neg):
  """Adds network argument for creating network endpoint groups."""
  help_text = """\
      Name of the network in which the NEG is created. `default` project
      network is used if unspecified.
  """
  network_applicable_ne_types = ['`GCE_VM_IP_PORT`']
  if support_hybrid_neg:
    network_applicable_ne_types.append('`NON_GCP_PRIVATE_IP_PORT`')
  if support_l4ilb_neg:
    network_applicable_ne_types.append('`GCE_VM_PRIMARY_IP`')
  if support_global_scope:
    help_text += """\

      This is only supported for NEGs with endpoint type {0}.
    """.format(' or '.join(network_applicable_ne_types))
  parser.add_argument('--network', help=help_text)


def AddSubnet(parser, support_global_scope, support_hybrid_neg,
              support_l4ilb_neg):
  """Adds subnet argument for creating network endpoint groups."""
  help_text = """\
      Name of the subnet to which all network endpoints belong.

      If not specified, network endpoints may belong to any subnetwork in the
      region where the network endpoint group is created.
  """
  if support_global_scope or support_hybrid_neg:
    subnet_applicable_types = ['`GCE_VM_IP_PORT`']
    if support_l4ilb_neg:
      subnet_applicable_types.append('`GCE_VM_PRIMARY_IP`')
    help_text += """\

      This is only supported for NEGs with endpoint type {0}.
    """.format(' or '.join(subnet_applicable_types))
  parser.add_argument('--subnet', help=help_text)


def AddDefaultPort(parser, support_global_scope, support_hybrid_neg):
  """Adds default port argument for creating network endpoint groups."""
  help_text = """\
    The default port to use if the port number is not specified in the network
    endpoint.

    If this flag isn't specified, then every network endpoint in the network
    endpoint group must have a port specified.
  """
  if support_global_scope or support_hybrid_neg:
    help_text = """\
      The default port to use if the port number is not specified in the network
      endpoint.

      If this flag isn't specified for a NEG with endpoint type {0},
      then every network endpoint in the network endpoint group must have a port
      specified.
    """.format('`GCE_VM_IP_PORT` or `NON_GCP_PRIVATE_IP_PORT`'
               if support_hybrid_neg else '`GCE_VM_IP_PORT`')
    if support_global_scope:
      help_text += """\
      For a NEG with endpoint type `INTERNET_IP_PORT` and `INTERNET_FQDN_PORT`.
      If the default port is not specified the well known port for your backend
      protocol will be used (80 for http,  443 for https).
      """
  parser.add_argument('--default-port', type=int, help=help_text)


def AddCreateNegArgsToParser(parser,
                             support_neg_type,
                             support_global_scope=False,
                             support_hybrid_neg=False,
                             support_l4ilb_neg=False):
  """Adds flags for creating a network endpoint group to the parser."""
  AddNetworkEndpointGroupType(parser, support_neg_type)
  AddNetworkEndpointType(parser, support_global_scope, support_hybrid_neg,
                         support_l4ilb_neg)
  AddNetwork(parser, support_global_scope, support_hybrid_neg,
             support_l4ilb_neg)
  AddSubnet(parser, support_global_scope, support_hybrid_neg, support_l4ilb_neg)
  AddDefaultPort(parser, support_global_scope, support_hybrid_neg)


def AddAddEndpoint(endpoint_group, endpoint_spec, support_global_scope,
                   support_hybrid_neg, support_l4ilb_neg):
  """Adds add endpoint argument for updating network endpoint groups."""
  help_text = """\
          The network endpoint to add to the network endpoint group. Allowed
          keys are:

          * instance - Name of instance in same zone as network endpoint
            group.

            The VM instance must belong to the network / subnetwork associated
            with the network endpoint group. If the VM instance is deleted, then
            any network endpoint group that has a reference to it is updated.
            The delete causes all network endpoints on the VM to be removed
            from the network endpoint group.

          * ip - Optional IP address of the network endpoint.

            Optional IP address of the network endpoint. If the IP address is
            not specified then, we use the primary IP address for the VM
            instance in the network that the NEG belongs to.

          * port - Optional port for the network endpoint.

            Optional port for the network endpoint. If not specified and the
            networkEndpointType is `GCE_VM_IP_PORT`, the defaultPort for the
            network endpoint group will be used.
  """
  if support_global_scope or support_hybrid_neg or support_l4ilb_neg:
    help_text = """\
          The network endpoint to add to the network endpoint group. Keys used
          depend on the endpoint type of the NEG.

          `GCE_VM_IP_PORT`

              *instance* - Name of instance in same zone as the network endpoint
              group.

              The VM instance must belong to the network / subnetwork
              associated with the network endpoint group. If the VM instance
              is deleted, then any network endpoint group that has a reference
              to it is updated.

              *ip* - Optional IP address of the network endpoint. the IP address
              must belong to a VM in compute engine (either the primary IP or
              as part of an aliased IP range). If the IP address is not
              specified, then the primary IP address for the VM instance in
              the network that the network endpoint group belongs to will be
              used.

              *port* - Required endpoint port unless NEG default port is set.
    """
    if support_global_scope:
      help_text += """\

          `INTERNET_IP_PORT`

              *ip* - Required IP address of the endpoint to attach. Must be
              publicly routable.

              *port* - Optional port of the endpoint to attach. If unspecified
              then NEG default port is set. If no default port is set, the
              well known port for the backend protocol will be used instead
              (80 for http, 443 for https).

          `INTERNET_FQDN_PORT`

              *fqdn* - Required fully qualified domain name to use to look up an
              external endpoint. Must be resolvable to a public IP address via
              public DNS.

              *port* - Optional port of the endpoint to attach. If unspecified
              then NEG default port is set. If no default port is set, the
              well known port for the backend protocol will be used instead
              (80 for http, 443 for https or http2).
      """
    if support_hybrid_neg:
      help_text += """\

          `NON_GCP_PRIVATE_IP_PORT`

              *ip* - Required IP address of the network endpoint to attach. The
              IP address must belong to a VM not in Google Compute Engine and
              must be routable using a cloud router over VPN or an Interconnect.

              *port* - Required port of the network endpoint to attach unless
              NEG default port is set.
      """
    if support_l4ilb_neg:
      help_text += """\

          `GCE_VM_PRIMARY_IP`

              *ip* - Required IP address of the network endpoint to attach. The
              IP address must be the primary IP of a VM's primary network
              interface.
      """

  endpoint_group.add_argument(
      '--add-endpoint',
      action='append',
      type=arg_parsers.ArgDict(spec=endpoint_spec),
      help=help_text)


def AddRemoveEndpoint(endpoint_group, endpoint_spec, support_global_scope,
                      support_hybrid_neg, support_l4ilb_neg):
  """Adds remove endpoint argument for updating network endpoint groups."""
  help_text = """\
          The network endpoint to detach from the network endpoint group.
          Allowed keys are:

          * instance - Name of instance in same zone as network endpoint
            group.

          * ip - Optional IP address of the network endpoint.

            If the IP address is not specified then all network endpoints that
            belong to the instance are removed from the NEG.

          * port - Optional port for the network endpoint. Required if the
            network endpoint type is `GCE_VM_IP_PORT`.
  """
  if support_global_scope or support_hybrid_neg or support_l4ilb_neg:
    help_text = """\
          The network endpoint to detach from the network endpoint group. Keys
          used depend on the endpoint type of the NEG.

          `GCE_VM_IP_PORT`

              *instance* - Required name of instance whose endpoint(s) to
              detach. If IP address is unset then all endpoints for the
              instance in the NEG will be detached.

              *ip* - Optional IP address of the network endpoint to detach.
              If specified port must be provided as well.

              *port* - Optional port of the network endpoint to detach.
    """
    if support_global_scope:
      help_text += """\

          `INTERNET_IP_PORT`

              *ip* - Required IP address of the network endpoint to detach.

              *port* - Optional port of the network endpoint to detach if the
              endpoint has a port specified.

          `INTERNET_FQDN_PORT`

              *fqdn* - Required fully qualified domain name of the endpoint to
              detach.

              *port* - Optional port of the network endpoint to detach if the
              endpoint has a port specified.
      """
    if support_hybrid_neg:
      help_text += """\

          `NON_GCP_PRIVATE_IP_PORT`

              *ip* - Required IP address of the network endpoint to detach.

              *port* - Required port of the network endpoint to detach unless
              NEG default port is set.
      """
    if support_l4ilb_neg:
      help_text += """\

          `GCE_VM_PRIMARY_IP`

              *ip* - Required IP address of the network endpoint to attach. The
              IP address must be the primary IP of a VM's primary network
              interface.
      """

  endpoint_group.add_argument(
      '--remove-endpoint',
      action='append',
      type=arg_parsers.ArgDict(spec=endpoint_spec),
      help=help_text)


def AddUpdateNegArgsToParser(parser,
                             support_global_scope=False,
                             support_hybrid_neg=False,
                             support_l4ilb_neg=False):
  """Adds flags for updating a network endpoint group to the parser."""
  endpoint_group = parser.add_group(
      mutex=True,
      required=True,
      help='These flags can be specified multiple times to add/remove '
      'multiple endpoints.')

  endpoint_spec = {'instance': str, 'ip': str, 'port': int}
  if support_global_scope:
    endpoint_spec['fqdn'] = str

  AddAddEndpoint(endpoint_group, endpoint_spec, support_global_scope,
                 support_hybrid_neg, support_l4ilb_neg)
  AddRemoveEndpoint(endpoint_group, endpoint_spec, support_global_scope,
                    support_hybrid_neg, support_l4ilb_neg)
