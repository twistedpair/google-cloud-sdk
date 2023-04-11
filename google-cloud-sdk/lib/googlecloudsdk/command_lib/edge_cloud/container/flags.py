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
"""Flags and helpers for the container related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers


def AddAuthProviderCmdPath(parser):
  parser.add_argument(
      '--auth-provider-cmd-path',
      help="""
      Path to the gcloud executable for the auth provider field in kubeconfig.
      """
  )


def AddAdminUsers(parser):
  parser.add_argument(
      '--admin-users',
      help="""
      Username (Google email address) of the user who should be granted
      cluster-admin initially. This currently supports exactly one admin. If
      not set, the account issuing the creation request will be used by
      default.
      """
  )


def AddClusterIPV4CIDR(parser):
  parser.add_argument(
      '--cluster-ipv4-cidr',
      default='10.0.0.0/17',
      help="""
      All pods in the cluster are assigned an RFC1918 IPv4 address from this
      block. This field cannot be changed after creation.
      """
  )


def AddServicesIPV4CIDR(parser):
  parser.add_argument(
      '--services-ipv4-cidr',
      default='10.96.0.0/12',
      help="""
      All services in the cluster are assigned an RFC1918 IPv4 address from
      this block. This field cannot be changed after creation.
      """
  )


def AddDefaultMaxPodsPerNode(parser):
  parser.add_argument(
      '--default-max-pods-per-node',
      help='The default maximum number of pods per node.'
  )


def AddFleetProject(parser):
  parser.add_argument(
      '--fleet-project',
      help='Name of the Fleet host project where the cluster is registered.'
  )


def AddLabels(parser):
  parser.add_argument(
      '--labels',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      help="""
      List of label KEY=VALUE pairs to add.

      Keys must start with a lowercase character and contain only hyphens
      (-), underscores (```_```), lowercase characters, and numbers. Values must
      contain only hyphens (-), underscores (```_```), lowercase characters, and
      numbers.
      """
  )


def AddMaintenanceWindowRecurrence(parser):
  parser.add_argument(
      '--maintenance-window-recurrence',
      help="""
      An RFC 5545 (https://tools.ietf.org/html/rfc5545#section-3.8.5.3)
        recurrence rule for how the cluster maintenance window recurs. They go
        on for the span of time between the start and the end time.
      """
  )


def AddMaintenanceWindowEnd(parser):
  parser.add_argument(
      '--maintenance-window-end',
      help="""
      End time of the recurring cluster maintenance window in the RFC 3339
      (https://www.ietf.org/rfc/rfc3339.txt) format. E.g.
      "2021-01-01T00:00:00Z" or "2021-01-01T00:00:00-05:00"
      """
  )


def AddMaintenanceWindowStart(parser):
  parser.add_argument(
      '--maintenance-window-start',
      help="""
      Start time of the recurring cluster maintenance window in the RFC 3339
      (https://www.ietf.org/rfc/rfc3339.txt) format. E.g.
      "2021-01-01T00:00:00Z" or "2021-01-01T00:00:00-05:00"
      """
  )


def AddClusterIPV6CIDR(parser):
  parser.add_argument(
      '--cluster-ipv6-cidr',
      help="""
      If specified, all pods in the cluster are assigned an RFC4193 IPv6 address
      from this block. This field cannot be changed after creation.
      """
  )


def AddServicesIPV6CIDR(parser):
  parser.add_argument(
      '--services-ipv6-cidr',
      help="""
      If specified, all services in the cluster are assigned an RFC4193 IPv6
      address from this block. This field cannot be changed after creation.
      """
  )


def AddControlPlaneKMSKey(parser):
  parser.add_argument(
      '--control-plane-kms-key',
      hidden=True,
      help="""
      Google Cloud KMS key that will be used to secure persistent disks of the
      control plane VMs of a remote control plane cluster. The Edge Container
      service account for this project must have
      `roles/cloudkms.cryptoKeyEncrypterDecrypter` on the key.

      If not provided, a Google-managed key will be used by default.
      """
  )


def AddSystemAddonsConfig(parser):
  parser.add_argument(
      '--system-addons-config',
      hidden=True,
      type=arg_parsers.YAMLFileContents(),
      help="""
      If specified as a YAML/JSON file, customized configuration in this file
      will be applied to the system add-ons.

      For example,

      {
        "systemAddonsConfig": {
          "ingress": {
            "disabled": true,
            "ipv4_vip": "10.0.0.1"
          }
        }
      }
      """
  )


def AddExternalLbIpv4AddressPools(parser):
  parser.add_argument(
      '--external-lb-ipv4-address-pools',
      hidden=True,
      type=arg_parsers.ArgList(),
      metavar='EXTERNAL_LB_IPV4_ADDRESS',
      help="""
      IPv4 address pools that are used for data plane load balancing of
      local control plane clusters. Existing pools cannot be updated
      after cluster creation; only adding new pools is allowed.
      Each address pool must be specified as one of the following
      two types of values:
        1. A IPv4 address range, for example, "10.0.0.1-10.0.0.10". A range that contains a single IP (e.g. "10.0.0.1-10.0.0.1") is allowed.
        2. A IPv4 CIDR block, for example, "10.0.0.1/24"
      Use comma when specifying multiple address pools, for example:
        --external-lb-ipv4-address-pools 10.0.0.1-10.0.0.10,10.0.0.1/24
      """,
  )


def AddControlPlaneNodeLocation(parser):
  parser.add_argument(
      '--control-plane-node-location',
      hidden=True,
      help="""
      Google Edge Cloud zone where the local control plane nodes
      will be created.
      """
  )


def AddControlPlaneNodeCount(parser):
  parser.add_argument(
      '--control-plane-node-count',
      hidden=True,
      help="""
      The number of local control plane nodes in a cluster. Use one to create
      a single-node control plane or use three to create a high availability
      control plane.
      Any other numbers of nodes will not be accepted.
      """
  )


def AddControlPlaneMachineFilter(parser):
  parser.add_argument(
      '--control-plane-machine-filter',
      hidden=True,
      help="""
      Only machines matching this filter will be allowed to host
      local control plane nodes.
      The filtering language accepts strings like "name=<name>",
      and is documented here: [AIP-160](https://google.aip.dev/160).
      """
  )


def AddControlPlaneSharedDeploymentPolicy(parser):
  parser.add_argument(
      '--control-plane-shared-deployment-policy',
      hidden=True,
      help="""
      Policy configuration about how user application is deployed for
      local control plane cluster. It supports two values, ALLOWED and
      DISALLOWED. ALLOWED means that user application can be deployed on
      control plane nodes. DISALLOWED means that user application can not be
      deployed on control plane nodes. Instead, it can only be deployed on
      worker nodes. By default, this value is DISALLOWED. The input is case
      insensitive.
      """
  )


def AddLROMaximumTimeout(parser):
  parser.add_argument(
      '--lro-timeout',
      hidden=True,
      help="""
      Overwrite the default LRO maximum timeout.
      """
  )
