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
"""Flags for Workstation Config related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import argparse

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def AddAsyncFlag(parser):
  """Adds --async flag."""
  base.ASYNC_FLAG.AddToParser(parser)


def LocationsAttributeConfig(help_text=''):
  """Create a location attribute in resource argument.

  Args:
    help_text: If set, overrides default help text for `--location`

  Returns:
    Location resource argument parameter config
  """
  return concepts.ResourceParameterAttributeConfig(
      name='region',
      help_text=help_text if help_text else
      ('The location for the {resource}.'))


def ClustersAttributeConfig(help_text=''):
  """Create a cluster attribute in resource argument.

  Args:
    help_text: If set, overrides default help text for `--cluster`

  Returns:
    Cluster resource argument parameter config
  """
  return concepts.ResourceParameterAttributeConfig(
      name='cluster',
      help_text=help_text if help_text else ('The cluster for the {resource}.'))


def ConfigsAttributeConfig(help_text=''):
  """Create a config attribute in resource argument.

  Args:
    help_text: If set, overrides default help text for `config`

  Returns:
    Config resource argument parameter config
  """
  return concepts.ResourceParameterAttributeConfig(
      name='config',
      help_text=help_text if help_text else ('The config for the {resource}.'))


def WorkstationsAttributeConfig(help_text=''):
  """Create a workstation attribute in resource argument.

  Args:
    help_text: If set, overrides default help text for `workstation`

  Returns:
    Workstation resource argument parameter config
  """
  return concepts.ResourceParameterAttributeConfig(
      name='workstation',
      help_text=help_text if help_text else ('The workstation.'))


def AddConfigResourceArg(parser, api_version='v1beta'):
  """Create a config resource argument."""
  spec = concepts.ResourceSpec(
      'workstations.projects.locations.workstationClusters.workstationConfigs',
      resource_name='config',
      api_version=api_version,
      workstationConfigsId=ConfigsAttributeConfig(),
      workstationClustersId=ClustersAttributeConfig(),
      locationsId=LocationsAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )
  concept_parsers.ConceptParser.ForResource(
      'config',
      spec,
      'The group of arguments defining a config',
      required=True,
  ).AddToParser(parser)


def AddWorkstationResourceArg(parser, api_version='v1beta'):
  """Create a workstation resource argument."""
  spec = concepts.ResourceSpec(
      'workstations.projects.locations.workstationClusters.workstationConfigs.workstations',
      resource_name='workstation',
      api_version=api_version,
      workstationsId=WorkstationsAttributeConfig(),
      workstationConfigsId=ConfigsAttributeConfig(),
      workstationClustersId=ClustersAttributeConfig(),
      locationsId=LocationsAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )
  concept_parsers.ConceptParser.ForResource(
      'workstation',
      spec,
      'The group of arguments defining a workstation',
      required=True,
  ).AddToParser(parser)


def AddIdleTimeoutFlag(parser, use_default=True):
  """Adds an --idle-timeout flag to the given parser."""
  help_text = """\
  How long (in seconds) to wait before automatically stopping an instance that
  hasn't received any user traffic. A value of 0 indicates that this instance
  should never time out due to idleness.
  """
  parser.add_argument(
      '--idle-timeout',
      default=7200 if use_default else None,
      type=int,
      help=help_text,
  )


def AddRunningTimeoutFlag(parser, use_default=True):
  """Adds an --running-timeout flag to the given parser."""
  help_text = """\
  How long (in seconds) to wait before automatically stopping a workstation
  after it started. A value of 0 indicates that workstations using this config
  should never time out.
  """
  parser.add_argument(
      '--running-timeout',
      default=7200 if use_default else None,
      type=int,
      help=help_text,
  )


def AddMachineTypeFlag(parser, use_default=True):
  """Adds a --machine-type flag to the given parser."""
  help_text = """\
  Machine type determines the specifications of the Compute Engine machines
  that the workstations created under this configuration will run on."""
  parser.add_argument(
      '--machine-type',
      choices=[
          'e2-standard-2',
          'e2-standard-4',
          'e2-standard-8',
          'e2-standard-16',
          'e2-standard-32',
          'n2-standard-8',
          'n1-standard-4',
          't2d-standard-6',
          'n2d-standard-2',
          'n2d-standard-4',
          'n2d-standard-8',
          'n2d-standard-16',
          'n2d-standard-32',
      ],
      default='e2-standard-4' if use_default else None,
      help=help_text,
  )


def AddServiceAccountFlag(parser):
  """Adds a --service-account flag to the given parser."""
  help_text = """\
  Email address of the service account that will be used on VM instances used to
  support this config. This service account must have permission to pull the
  specified container image. If not set, VMs will run without a service account,
  in which case the image must be publicly accessible."""
  parser.add_argument('--service-account', help=help_text)


def AddNetworkTags(parser):
  """Adds a --network-tags flag to the given parser."""
  help_text = """\
  Network tags to add to the Google Compute Engine machines backing the
  Workstations.

  Example:

    $ {command} --network-tags=tag_1,tag_2
  """
  parser.add_argument(
      '--network-tags',
      metavar='NETWORK_TAGS',
      type=arg_parsers.ArgList(),
      help=help_text)


def AddPoolSize(parser, use_default=True):
  """Adds a --pool-size flag to the given parser."""
  help_text = """\
  Number of instances to pool for faster Workstation starup."""
  parser.add_argument(
      '--pool-size',
      default=0 if use_default else None,
      type=int,
      help=help_text,
  )


def AddDisablePublicIpAddresses(parser, use_default=True):
  """Adds a --disable-public-ip-addresses flag to the given parser."""
  help_text = """\
  Default value is false.
  If set, instances will have no public IP address."""
  parser.add_argument(
      '--disable-public-ip-addresses',
      action='store_true',
      default=False if use_default else None,
      help=help_text,
  )


def AddShieldedSecureBoot(parser, use_default=True):
  """Adds --shielded-secure-boot flag to the given parser."""
  help_text = """\
  Default value is false.
  If set, instances will have Secure Boot enabled."""
  parser.add_argument(
      '--shielded-secure-boot',
      action='store_true',
      default=False if use_default else None,
      help=help_text,
  )


def AddShieldedVtpm(parser, use_default=True):
  """Adds a --shielded-vtpm flag to the given parser."""
  help_text = """\
  Default value is false.
  If set, instances will have vTPM enabled."""
  parser.add_argument(
      '--shielded-vtpm',
      action='store_true',
      default=False if use_default else None,
      help=help_text,
  )


def AddShieldedIntegrityMonitoring(parser, use_default=True):
  """Adds a --shielded-integrity-monitoring flag to the given parser."""
  help_text = """\
  Default value is false.
  If set, instances will have integrity monitoring enabled."""
  parser.add_argument(
      '--shielded-integrity-monitoring',
      action='store_true',
      default=False if use_default else None,
      help=help_text,
  )


def AddEnableConfidentialCompute(parser, use_default=True):
  """Adds an --enable-confidential-compute flag to the given parser."""
  help_text = """\
  Default value is false.
  If set, instances will have confidential compute enabled."""
  parser.add_argument(
      '--enable-confidential-compute',
      action='store_true',
      default=False if use_default else None,
      help=help_text,
  )


def AddBootDiskSize(parser, use_default=True):
  """Adds a --boot-disk-size flag to the given parser."""
  help_text = """\
  Size of the boot disk in GB."""
  parser.add_argument(
      '--boot-disk-size',
      default=50 if use_default else None,
      type=int,
      help=help_text,
  )


def AddPdDiskType(parser):
  """Adds a --pd-disk-type flag to the given parser."""
  help_text = """\
  Type of the persistent directory."""
  parser.add_argument(
      '--pd-disk-type',
      choices=['pd-standard', 'pd-balanced', 'pd-ssd'],
      default='pd-standard',
      help=help_text)


def AddPdDiskSize(parser):
  """Adds a --pd-disk-size flag to the given parser."""
  help_text = """\
  Size of the persistent directory in GB."""
  parser.add_argument(
      '--pd-disk-size',
      choices=[10, 50, 100, 200, 500, 1000],
      default=200,
      type=int,
      help=help_text)


def AddPdReclaimPolicy(parser):
  """Adds a --pd-reclaim-policy flag to the given parser."""
  help_text = """\
  What should happen to the disk after the Workstation is deleted."""
  parser.add_argument(
      '--pd-reclaim-policy',
      choices={
          'delete':
              'The persistent disk will be deleted with the Workstation.',
          'retain':
              'The persistent disk will be remain after the workstation is deleted and the administrator must manually delete the disk.'
      },
      default='delete',
      help=help_text)


def AddContainerImageField(parser, use_default=True):
  """Adds the --container-predefined-image and --container-custom-image flags to the given parser.
  """
  predefined_image_help_text = """\
  Code editor on base images."""
  custom_image_help_text = """\
  A docker image for the workstation. This image must be accessible by the
  service account configured in this configuration (--service-account). If no
  service account is defined, this image must be public.
  """
  group = parser.add_mutually_exclusive_group()
  group.add_argument(
      '--container-predefined-image',
      choices={
          'codeoss': 'Code OSS',
          'intellij': 'IntelliJ IDEA Ultimate',
          'pycharm': 'PyCharm Professional',
          'rider': 'Rider',
          'webstorm': 'WebStorm',
          'phpstorm': 'PhpStorm',
          'rubymine': 'RubyMine',
          'goland': 'GoLand',
          'clion': 'CLion',
          'base-image': 'Base image - no IDE',
      },
      default='codeoss' if use_default else None,
      help=predefined_image_help_text,
  )

  group.add_argument(
      '--container-custom-image', type=str, help=custom_image_help_text)


def AddContainerCommandField(parser):
  """Adds a --container-command flag to the given parser."""
  help_text = """\
  If set, overrides the default ENTRYPOINT specified by the image.

  Example:

    $ {command} --container-command=executable,parameter_1,parameter_2"""
  parser.add_argument(
      '--container-command',
      metavar='CONTAINER_COMMAND',
      type=arg_parsers.ArgList(),
      help=help_text)


def AddContainerArgsField(parser):
  """Adds a --container-args flag to the given parser."""
  help_text = """\
  Arguments passed to the entrypoint.

  Example:

    $ {command} --container-args=arg_1,arg_2"""
  parser.add_argument(
      '--container-args',
      metavar='CONTAINER_ARGS',
      type=arg_parsers.ArgList(),
      help=help_text)


def AddContainerEnvField(parser):
  """Adds a --container-env flag to the given parser."""
  help_text = """\
  Environment variables passed to the container.

  Example:

    $ {command} --container-env=key1=value1,key2=value2"""
  parser.add_argument(
      '--container-env',
      metavar='CONTAINER_ENV',
      type=arg_parsers.ArgDict(key_type=str, value_type=str),
      help=help_text)


def AddContainerWorkingDirField(parser):
  """Adds a --container-working-dir flag to the given parser."""
  help_text = """\
  If set, overrides the default DIR specified by the image."""
  parser.add_argument('--container-working-dir', help=help_text)


def AddContainerRunAsUserField(parser):
  """Adds a --container-run-as-user flag to the given parser."""
  help_text = """\
  If set, overrides the USER specified in the image with the given
  uid."""
  parser.add_argument('--container-run-as-user', type=int, help=help_text)


def AddWorkstationPortField(parser):
  """Adds a workstation-port flag to the given parser."""
  help_text = """\
  The port on the workstation to which traffic should be sent."""
  parser.add_argument('workstation_port', type=int, help=help_text)


def AddPortField(parser):
  """Adds a --port flag to the given parser."""
  help_text = """\
  The port on the workstation to which traffic should be sent."""
  parser.add_argument('--port', type=int, default=22, help=help_text)


def AddLocalHostPortField(parser):
  """Adds a --local-host-port flag to the given parser."""
  help_text = """\
  `LOCAL_HOST:LOCAL_PORT` on which gcloud should bind and listen for connections
  that should be tunneled.

  `LOCAL_PORT` may be omitted, in which case it is treated as 0 and an arbitrary
  unused local port is chosen. The colon also may be omitted in that case.

  If `LOCAL_PORT` is 0, an arbitrary unused local port is chosen."""
  parser.add_argument(
      '--local-host-port',
      type=arg_parsers.HostPort.Parse,
      default='localhost:0',
      help=help_text)


def AddCommandField(parser):
  """Adds a --command flag to the given parser."""
  help_text = """\
      A command to run on the workstation.

      Runs the command on the target workstation and then exits.
      """
  parser.add_argument('--command', type=str, help=help_text)


def AddSshArgsAndUserField(parser):
  """Adds a --user flag to the given parser."""
  help_text = """\
  The username with which to SSH.
  """
  parser.add_argument('--user', type=str, default='user', help=help_text)

  help_text = """\
  Flags and positionals passed to the underlying ssh implementation."""
  parser.add_argument('ssh_args', nargs=argparse.REMAINDER, help=help_text)
