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
"""Utilities for flags for `gcloud colab-enterprise` commands."""

from googlecloudsdk.api_lib.colab_enterprise import runtime_templates as runtime_templates_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.colab_enterprise import completers
from googlecloudsdk.command_lib.compute.networks import flags as compute_network_flags
from googlecloudsdk.command_lib.compute.networks.subnets import flags as compute_subnet_flags
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.util.concepts import concept_parsers

_accelerator_choices = [
    'NVIDIA_TESLA_V100',
    'NVIDIA_TESLA_T4',
    'NVIDIA_TESLA_A100',
    'NVIDIA_A100_80GB',
    'NVIDIA_L4',
]
_disk_choices = ['PD_STANDARD', 'PD_SSD', 'PD_BALANCED', 'PD_EXTREME']


def GetRegionAttributeConfig():
  """Get the attribute config for the region resource.

  Returns:
    The resource attribute for the region.
  """
  return concepts.ResourceParameterAttributeConfig(
      name='region',
      help_text='Cloud region for the {resource}.',
  )


def AddRuntimeTemplateResourceArg(parser, verb, is_positional):
  """Add a resource argument for a runtime template to the parser.

  Args:
    parser: argparse parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    is_positional: bool, True for if arg is positional; False if flag.
  """

  def GetRuntimeTemplateResourceSpec(resource_name='runtime template'):
    return concepts.ResourceSpec(
        'aiplatform.projects.locations.notebookRuntimeTemplates',
        resource_name=resource_name,
        projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
        locationsId=GetRegionAttributeConfig(),
        disable_auto_completers=False,
    )

  if is_positional:
    arg_name = 'runtime_template'
    prefixes = False
    flag_name_overrides = None
    fallthroughs = None
  else:
    arg_name = '--runtime-template'
    prefixes = True
    flag_name_overrides = {'region': ''}
    fallthroughs = {'region': ['--region']}
  concept_parsers.ConceptParser.ForResource(
      arg_name,
      GetRuntimeTemplateResourceSpec(),
      'Unique name of the runtime template {}. This was optionally provided by'
      ' setting --runtime-template-id in the create runtime-template command,'
      ' or was system-generated if unspecified.'.format(verb),
      required=True,
      prefixes=prefixes,
      flag_name_overrides=flag_name_overrides,
      command_level_fallthroughs=fallthroughs,
  ).AddToParser(parser)


def AddRegionResourceArg(parser, verb):
  """Add a resource argument for a Vertex AI region to the parser.

  Args:
    parser: argparse parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """

  region_resource_spec = concepts.ResourceSpec(
      'aiplatform.projects.locations',
      resource_name='region',
      locationsId=GetRegionAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )

  concept_parsers.ConceptParser.ForResource(
      '--region',
      region_resource_spec,
      'Cloud region {}. Please see '
      ' https://cloud.google.com/colab/docs/locations for a list of supported'
      ' regions.'.format(verb),
      required=True,
  ).AddToParser(parser)


def AddNetworkResourceArg(help_text, parser):
  """Adds Resource arg for network to the parser.

  Args:
    help_text: str, the help text for the flag.
    parser: argparse parser for the command.
  """

  def GetNetworkResourceSpec():
    """Constructs and returns the Resource specification for network."""

    def NetworkAttributeConfig():
      return concepts.ResourceParameterAttributeConfig(
          name='network',
          help_text=help_text,
          completer=compute_network_flags.NetworksCompleter,
      )

    return concepts.ResourceSpec(
        'compute.networks',
        resource_name='network',
        network=NetworkAttributeConfig(),
        project=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
        disable_auto_completers=False,
    )

  concept_parsers.ConceptParser.ForResource(
      '--network', GetNetworkResourceSpec(), help_text
  ).AddToParser(parser)


def AddSubnetworkResourceArg(help_text, parser):
  """Adds Resource arg for subnetwork to the parser.

  Args:
    help_text: str, the help text for the flag.
    parser: argparse parser for the command.
  """

  def GetSubnetResourceSpec():
    """Constructs and returns the Resource specification for Subnet."""

    def SubnetAttributeConfig():
      return concepts.ResourceParameterAttributeConfig(
          name='subnetwork',
          help_text=help_text,
          completer=compute_subnet_flags.SubnetworksCompleter,
      )

    def RegionAttributeConfig():
      return concepts.ResourceParameterAttributeConfig(
          name='subnetwork-region',
          help_text=(
              'Google Cloud region of this subnetwork '
              'https://cloud.google.com/compute/docs/regions-zones/#locations.'
          ),
          completer=completers.RegionCompleter,
      )

    return concepts.ResourceSpec(
        'compute.subnetworks',
        resource_name='subnetwork',
        subnetwork=SubnetAttributeConfig(),
        region=RegionAttributeConfig(),
        project=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
        disable_auto_completers=False,
    )

  concept_parsers.ConceptParser.ForResource(
      '--subnetwork', GetSubnetResourceSpec(), help_text
  ).AddToParser(parser)


def AddKmsKeyResourceArg(parser, help_text):
  """Adds Resource arg for KMS key to the parser.

  Args:
    parser: argparse parser for the command.
    help_text: str, the help text for the flag.
  """

  def GetKmsKeyResourceSpec():

    def KmsKeyAttributeConfig():
      # For anchor attribute, help text is generated automatically.
      return concepts.ResourceParameterAttributeConfig(name='kms-key')

    def KmsKeyringAttributeConfig():
      return concepts.ResourceParameterAttributeConfig(
          name='kms-keyring', help_text='KMS keyring id of the {resource}.'
      )

    def KmsLocationAttributeConfig():
      return concepts.ResourceParameterAttributeConfig(
          name='kms-location', help_text='Cloud location for the {resource}.'
      )

    def KmsProjectAttributeConfig():
      return concepts.ResourceParameterAttributeConfig(
          name='kms-project', help_text='Cloud project id for the {resource}.'
      )

    return concepts.ResourceSpec(
        'cloudkms.projects.locations.keyRings.cryptoKeys',
        resource_name='key',
        cryptoKeysId=KmsKeyAttributeConfig(),
        keyRingsId=KmsKeyringAttributeConfig(),
        locationsId=KmsLocationAttributeConfig(),
        projectsId=KmsProjectAttributeConfig(),
    )

  concept_parsers.ConceptParser.ForResource(
      '--kms-key',
      GetKmsKeyResourceSpec(),
      help_text,
      required=False,
  ).AddToParser(parser)


def AddAsyncFlag(parser):
  """Adds the --async flags to the given parser."""
  base.ASYNC_FLAG.AddToParser(parser)


def AddCreateRuntimeTemplateFlags(parser):
  """Construct groups and arguments specific to runtime template creation."""

  AddRegionResourceArg(parser, 'to create runtime template')
  parser.add_argument(
      '--runtime-template-id',
      required=False,
      help=(
          'The id of the runtime template. If not specified, a random id will'
          ' be generated.'
      ),
  )
  parser.add_argument(
      '--display-name',
      required=True,
      help='The display name of the runtime template.',
  )
  runtime_template_group = parser.add_group(
      help='Configuration of the runtime template',
  )
  runtime_template_group.add_argument(
      '--description',
      required=False,
      help='The description of the runtime template.',
  )
  machine_spec_group = runtime_template_group.add_group(
      help=(
          'The machine configuration of the runtime provisioned from this'
          ' template.'
      ),
  )
  machine_spec_group.add_argument(
      '--machine-type',
      required=False,
      help='The Compute Engine machine type selected for the runtime.',
      default='e2-standard-4',
  )
  machine_spec_group.add_argument(
      '--accelerator-type',
      help=(
          'The type of hardware accelerator used by the runtime. If specified,'
          ' --accelerator-count must also be specified.'
      ),
      choices=_accelerator_choices,
      default=None,
  )
  machine_spec_group.add_argument(
      '--accelerator-count',
      type=int,
      help='The number of accelerators used by the runtime.',
  )
  disk_spec_group = runtime_template_group.add_group(
      help=(
          'The configuration for the data disk of the runtime provisioned from'
          ' this template.'
      ),
  )
  disk_spec_group.add_argument(
      '--disk-type',
      help='The type of the persistent disk.',
      choices=_disk_choices,
      default='PD_STANDARD',
  )
  disk_spec_group.add_argument(
      '--disk-size-gb',
      help=(
          'The disk size of the runtime in GB. If specified, the --disk-type'
          ' must also be specified. The minimum size is 10GB and the maximum is'
          ' 65536GB.'
      ),
      type=int,
      default=100,
  )
  network_spec_group = runtime_template_group.add_group(
      help='The network configuration for the runtime.',
  )
  AddNetworkResourceArg(
      help_text='The name of the VPC that this runtime is in.',
      parser=network_spec_group,
  )
  AddSubnetworkResourceArg(
      help_text='The name of the subnetwork that this runtime is in.',
      parser=network_spec_group,
  )
  # Since default for this flag is True, the documentation will only show
  # --no-enable-internet-access. Even though now true/false values will always
  # be specified in API request instead of defaulting to none, this gives a
  # better UX than providing both the flag and its negative when default is
  # True.
  network_spec_group.add_argument(
      '--enable-internet-access',
      action='store_true',
      dest='enable_internet_access',
      default=True,
      help='Enable public internet access for the runtime.',
  )
  runtime_template_group.add_argument(
      '--labels',
      help='Add labels to identify and group the runtime template.',
      type=arg_parsers.ArgDict(),
      metavar='KEY=VALUE',
  )
  runtime_template_group.add_argument(
      '--idle-shutdown-timeout',
      help=(
          'The duration after which the runtime is automatically shut down. An'
          ' input of 0s disables the idle shutdown feature, and a valid range'
          " is [10m, 24h]. See '$ gcloud topic datetimes' for details on"
          ' formatting the input duration.'
      ),
      type=arg_parsers.Duration(),
      default='3h',
  )
  runtime_template_group.add_argument(
      '--enable-euc',
      action='store_true',
      dest='enable_euc',
      help='Enable end user credential access for the runtime.',
      default=True,
  )
  runtime_template_group.add_argument(
      '--enable-secure-boot',
      action='store_true',
      dest='enable_secure_boot',
      help='Enables secure boot for the runtime. Disabled by default.',
      default=False,
  )
  runtime_template_group.add_argument(
      '--network-tags',
      type=arg_parsers.ArgList(),
      metavar='TAGS',
      help='Applies the given Compute Engine tags to the runtime.',
  )
  AddKmsKeyResourceArg(
      runtime_template_group,
      'The Cloud KMS encryption key (customer-managed encryption key) used to'
      ' protect the runtime. The key must be in the same region as the runtime.'
      ' If not specified, Google-managed encryption keys will be used.',
  )
  AddAsyncFlag(parser)


def AddDeleteRuntimeTemplateFlags(parser):
  """Construct groups and arguments specific to runtime template deletion."""
  AddRuntimeTemplateResourceArg(parser, 'to delete', is_positional=True)
  AddAsyncFlag(parser)


def AddDescribeRuntimeTemplateFlags(parser):
  """Construct groups and arguments specific to describing a runtime template."""
  AddRuntimeTemplateResourceArg(parser, 'to describe', is_positional=True)


def AddListRuntimeTemplatesFlags(parser):
  """Construct groups and arguments specific to listing runtime templates."""
  AddRegionResourceArg(parser, 'for which to list all runtime templates')
  parser.display_info.AddUriFunc(runtime_templates_util.GetRuntimeTemplateUri)


def AddFlagsToAddIamPolicyBinding(parser):
  """Construct arguments for adding an IAM policy binding to a runtime template."""
  AddRuntimeTemplateResourceArg(
      parser, 'to add IAM policy binding to', is_positional=True
  )
  iam_util.AddArgsForAddIamPolicyBinding(parser)


def AddGetIamPolicyFlags(parser):
  """Construct arguments for getting the IAM policy for a runtime template."""
  AddRuntimeTemplateResourceArg(
      parser, 'to get IAM policy for', is_positional=True
  )


def AddSetIamPolicyBindingFlags(parser):
  """Construct arguments for setting the IAM policy for a runtime template."""
  AddRuntimeTemplateResourceArg(
      parser, 'to set IAM policy for', is_positional=True
  )
  iam_util.AddArgForPolicyFile(parser)


def AddRemoveIamPolicyBindingFlags(parser):
  """Construct arguments for removing an IAM policy binding from a runtime template."""
  AddRuntimeTemplateResourceArg(
      parser, 'to remove IAM policy from', is_positional=True
  )
  iam_util.AddArgsForRemoveIamPolicyBinding(parser)


def AddAssignRuntimeFlags(parser):
  """Construct arguments for assigning a runtime."""

  AddRegionResourceArg(parser, 'to assign runtime')

  AddRuntimeTemplateResourceArg(
      parser, 'to configure the runtime with', is_positional=False
  )
  parser.add_argument(
      '--runtime-id',
      required=False,
      help=(
          'The id of the runtime to assign. If not specified, a random id will'
          ' be generated.'
      ),
  )
  parser.add_argument(
      '--display-name',
      required=True,
      help='The display name of the runtime to assign.',
  )
  parser.add_argument('--description', required=False, help='The description')
  parser.add_argument(
      '--runtime-user',
      required=False,
      help=(
          'User email for the runtime owner. Runtimes can only be used by the'
          ' owner. If a user is not provided, the gcloud user will be assumed'
          ' to be the owner. The user cannot be a service account.'
      ),
  )
  parser.add_argument(
      '--labels',
      help='Add labels to identify and group the runtime template.',
      type=arg_parsers.ArgDict(),
      metavar='KEY=VALUE',
  )

  AddAsyncFlag(parser)
