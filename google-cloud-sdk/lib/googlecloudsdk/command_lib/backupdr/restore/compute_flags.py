# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Flags for backup-dr restore compute commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.backupdr import util


def AddNameArg(parser, required=True):
  parser.add_argument(
      '--name',
      type=str,
      required=required,
      help='Name of the restored Compute Instance.',
  )


def AddTargetZoneArg(parser, required=True):
  parser.add_argument(
      '--target-zone',
      type=str,
      required=required,
      help='Zone where the target instance is restored.',
  )


def AddTargetProjectArg(parser, required=True):
  parser.add_argument(
      '--target-project',
      type=str,
      required=required,
      help='Project where the restore should happen.',
  )


def AddNetworkInterfaceArg(parser, required=True):
  """Network interface of the restored resource."""
  network_tier_options = ('NETWORK_TIER_UNSPECIFIED', 'STANDARD', 'PREMIUM')
  stack_type_options = ('STACK_TYPE_UNSPECIFIED', 'IPV4_ONLY', 'IPV4_IPV6')
  nic_type_options = ('NIC_TYPE_UNSPECIFIED', 'VIRTIO_NET', 'GVNIC')

  network_tier_validator = util.GetOneOfValidator(
      'network-tier', network_tier_options
  )
  stack_type_validator = util.GetOneOfValidator(
      'stack-type', stack_type_options
  )
  nic_type_validator = util.GetOneOfValidator('nic-type', nic_type_options)
  network_interface_spec = {
      'network': str,
      'subnet': str,
      'address': str,
      'internal-ipv6-address': str,
      'internal-ipv6-prefix-length': int,
      'external-ipaddress': str,
      'external-ipv6-address': str,
      'external-ipv6-prefix-length': int,
      'public-ptr-domain': str,
      'ipv6-public-ptr-domain': str,
      'network-tier': network_tier_validator,
      'aliases': str,
      'stack-type': stack_type_validator,
      'queue-count': int,
      'nic-type': nic_type_validator,
      'network-attachment': str,
  }
  parser.add_argument(
      '--network-interface',
      required=required,
      type=arg_parsers.ArgDict(spec=network_interface_spec),
      action='append',
      metavar='PROPERTY=VALUE',
      help=(
          'Adds a network interface to the instance. This flag can be repeated'
          ' to specify multiple network interfaces. The following keys are'
          ' allowed: network, subnet, address, internal-ipv6-address,'
          ' internal-ipv6-prefix-length, external-ipaddress,'
          ' external-ipv6-address, external-ipv6-prefix-length,'
          ' public-ptr-domain, ipv6-public-ptr-domain, network-tier, aliases,'
          ' stack-type, queue-count, nic-type, network-attachment'
      ),
  )


def AddServiceAccountArg(parser, required=True):
  """Service account used to restore."""
  parser.add_argument(
      '--service-account',
      type=str,
      required=required,
      help=(
          'A service account is an identity attached to the instance. Its'
          ' access tokens can be accessed through the instance metadata server'
          ' and are used to authenticate applications on the instance. The'
          ' account can be set using an email address corresponding to the'
          ' required service account. If not provided, the instance will use'
          " the project's default service account."
      ),
  )


def AddScopesArg(parser, required=True):
  """Scopes for the service account used to restore."""
  scopes_group = parser.add_mutually_exclusive_group()

  scopes_group.add_argument(
      '--scopes',
      type=arg_parsers.ArgList(str),
      required=required,
      metavar='SCOPE',
      help=(
          'If not provided, the instance will be assigned the default scopes,'
          ' described below. However, if neither --scopes nor --no-scopes are'
          ' specified and the project has no default service account, then the'
          ' instance will be created with no scopes. Note that the level of'
          ' access that a service account has is determined by a combination of'
          ' access scopes and IAM roles so you must configure both access'
          ' scopes and IAM roles for the service account to work properly.'
          ' SCOPE can be either the full URI of the scope or an alias. Default'
          ' scopes are assigned to all instances. Available aliases are:'
          ' https://cloud.google.com/sdk/gcloud/reference/compute/instances/create#--scopes'
      ),
  )

  scopes_group.add_argument(
      '--no-scopes',
      action='store_true',
      help='Create the instance with no scopes.',
  )


def AddCreateDiskArg(parser, required=True):
  """Attaches persistent disks to the instances."""

  disk_spec = {
      'name': str,
      'replica-zones': arg_parsers.ArgList(str, custom_delim_char=' '),
      'device-name': str,
  }
  parser.add_argument(
      '--create-disk',
      required=required,
      type=arg_parsers.ArgDict(spec=disk_spec),
      action='append',
      metavar='PROPERTY=VALUE',
      help="""
          Creates and attaches persistent disks to the instances.

          *name*: Specifies the name of the disk.

          *replica-zones*: Required for each regional disk associated with the
          instance. Specify the URLs of the zones where the disk should be
          replicated to. You must provide exactly two replica zones, and one
          zone must be the same as the instance zone.

          *device-name*: Device name of the disk from the source instance.
          """,
  )


def AddDescriptionArg(parser, required=True):
  """Description of the restored instance."""
  parser.add_argument(
      '--description',
      type=str,
      required=required,
      help='Specifies a textual description of the restored instance.',
  )


def AddMetadataArg(parser, required=True):
  """Metadata to be made available to the guest operating system."""
  helptext = """\
      Metadata to be made available to the guest operating system
      running on the instances. Each metadata entry is a key/value
      pair separated by an equals sign. Each metadata key must be unique
      and have a max of 128 bytes in length. Each value must have a max of
      256 KB in length. Multiple arguments can be
      passed to this flag, e.g.,
      ``--metadata key-1=value-1,key-2=value-2,key-3=value-3''.
      The combined total size for all metadata entries is 512 KB.

      In images that have Compute Engine tools installed on them,
      such as the
      link:https://cloud.google.com/compute/docs/images[official images],
      the following metadata keys have special meanings:

      *startup-script*::: Specifies a script that will be executed
      by the instances once they start running. For convenience,
      ``--metadata-from-file'' can be used to pull the value from a
      file.

      *startup-script-url*::: Same as ``startup-script'' except that
      the script contents are pulled from a publicly-accessible
      location on the web.


      For startup scripts on Windows instances, the following metadata keys
      have special meanings:
      ``windows-startup-script-url'',
      ``windows-startup-script-cmd'', ``windows-startup-script-bat'',
      ``windows-startup-script-ps1'', ``sysprep-specialize-script-url'',
      ``sysprep-specialize-script-cmd'', ``sysprep-specialize-script-bat'',
      and ``sysprep-specialize-script-ps1''. For more information, see
      [Running startup scripts](https://cloud.google.com/compute/docs/startupscript).
      """
  parser.add_argument(
      '--metadata',
      required=required,
      type=arg_parsers.ArgDict(min_length=1),
      default={},
      metavar='KEY=VALUE',
      help=helptext,
      action=arg_parsers.StoreOnceAction,
  )


def AddLabelsArg(parser, required=True):
  """Labels to be added to the instance."""
  helptext = """\
      List of label KEY=VALUE pairs to add.

      Keys must start with a lowercase character and contain only hyphens (-),
      underscores (_), lowercase characters, and numbers. Values must contain
      only hyphens (-), underscores (_), lowercase characters, and numbers.
      """
  parser.add_argument(
      '--labels',
      required=required,
      type=arg_parsers.ArgDict(),
      default={},
      metavar='KEY=VALUE',
      help=helptext,
  )


def AddTagsArg(parser, required=True):
  """Tags to be added to the instance."""
  helptext = """\
      Specifies a list of tags to apply to the instance. These tags allow
      network firewall rules and routes to be applied to specified VM instances.
      See gcloud_compute_firewall-rules_create(1) for more details.
      """
  parser.add_argument(
      '--tags',
      required=required,
      type=arg_parsers.ArgList(min_length=1),
      metavar='TAG',
      help=helptext,
  )
