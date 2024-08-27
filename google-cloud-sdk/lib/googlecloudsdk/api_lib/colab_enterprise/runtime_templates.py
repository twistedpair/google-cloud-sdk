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
"""colab-enterprise runtime-templates api helper."""

from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.core import resources


def GetParentForRuntimeTemplate(args):
  """Get the parent Location resource name for the runtime template.

  Args:
    args: Argparse object from Command.Run

  Returns:
    The resource name in the form projects/{project}/locations/{location}.
  """

  if args.IsSpecified('region'):
    region = args.CONCEPTS.region.Parse()
    return region.RelativeName()
  raise ValueError(
      'Region must be specified. See here for choices:'
      ' https://cloud.google.com/colab/docs/locations'
  )


def ParseRuntimeTemplateOperation(operation_name):
  """Parse operation relative resource name to the operation reference object.

  Args:
    operation_name: The operation resource name

  Returns:
    The operation reference object
  """
  if '/notebookRuntimeTemplates/' in operation_name:
    try:
      return resources.REGISTRY.ParseRelativeName(
          operation_name,
          collection='aiplatform.projects.locations.notebookRuntimeTemplates.operations',
      )
    except resources.WrongResourceCollectionException:
      pass
  return resources.REGISTRY.ParseRelativeName(
      operation_name, collection='aiplatform.projects.locations.operations'
  )


def GetRuntimeTemplateUri(resource):
  """Transform a runtime template resource into a URL."""
  runtime_template = resources.REGISTRY.ParseRelativeName(
      relative_name=resource.name,
      collection='aiplatform.projects.locations.notebookRuntimeTemplates',
  )
  return runtime_template.SelfLink()


def GetMachineSpecFromArgs(args, messages):
  """Constructs the machine spec from command line args.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.

  Returns:
      Machine spec config for the runtime template.
  """
  machine_spec_config = messages.GoogleCloudAiplatformV1beta1MachineSpec
  accelerator_type_enum = None
  if args.IsSpecified('accelerator_type'):
    accelerator_type_enum = arg_utils.ChoiceEnumMapper(
        arg_name='accelerator-type',
        message_enum=machine_spec_config.AcceleratorTypeValueValuesEnum,
        include_filter=lambda x: x != 'UNSPECIFIED' not in x,
    ).GetEnumForChoice(arg_utils.EnumNameToChoice(args.accelerator_type))
  return machine_spec_config(
      machineType=args.machine_type,
      acceleratorType=accelerator_type_enum,
      acceleratorCount=args.accelerator_count,
  )


def FormatDiskTypeForApiRequest(disk_type):
  """Translates disk type user input to a format accepted by the API.

  The command input is kept in the enum format to be consistent with other
  arguments like accelerator type.

  Args:
    disk_type: The disk type enum value from user (eg PD_STANDARD).

  Returns:
    The disk type string value validated by AIPlatform API (eg pd-standard).
  """
  return disk_type.lower().replace('_', '-')


def GetPersistentDiskSpecFromArgs(args, messages):
  """Constructs the persistent disk spec from command line args.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.

  Returns:
    Persistent disk spec config for the runtime template.
  """
  # Keep the string input, disk type is not represented as an enum in API.
  disk_type = None
  disk_size = None
  persistent_disk_spec_config = (
      messages.GoogleCloudAiplatformV1beta1PersistentDiskSpec
  )
  if args.IsSpecified('disk_type'):
    disk_type = FormatDiskTypeForApiRequest(args.disk_type)
  if args.IsSpecified('disk_size_gb'):
    disk_size = args.disk_size_gb
  return persistent_disk_spec_config(
      diskType=disk_type, diskSizeGb=disk_size
  )


def GetNetworkSpecFromArgs(args, messages):
  """Constructs the network spec from command line args.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.

  Returns:
    Network spec config for the runtime template.
  """
  network_spec_config = messages.GoogleCloudAiplatformV1beta1NetworkSpec
  network_relative_name = None
  subnetwork_relative_name = None
  if args.IsSpecified('network'):
    network_relative_name = args.CONCEPTS.network.Parse().RelativeName()
  if args.IsSpecified('subnetwork'):
    subnetwork_relative_name = args.CONCEPTS.subnetwork.Parse().RelativeName()

  return network_spec_config(
      network=network_relative_name,
      subnetwork=subnetwork_relative_name,
      enableInternetAccess=args.enable_internet_access,
  )


def GetLabelsFromArgs(args, messages):
  """Constructs the labels from command line args.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.

  Returns:
    Labels for the runtime template.
  """
  if args.IsSpecified('labels'):
    labels_message = (
        messages.GoogleCloudAiplatformV1beta1NotebookRuntimeTemplate.LabelsValue
    )
    return labels_message(
        additionalProperties=[
            labels_message.AdditionalProperty(key=key, value=value)
            for key, value in args.labels.items()
        ]
    )
  return None


def GetIdleShutdownConfigFromArgs(args, messages):
  """Constructs the idle shutdown config from command line args.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.

  Returns:
    Idle shutdown config for the runtime template.
  """
  idle_shutdown_config = (
      messages.GoogleCloudAiplatformV1beta1NotebookIdleShutdownConfig
  )
  if args.IsSpecified('idle_shutdown_timeout'):
    duration_seconds = args.idle_shutdown_timeout
    if duration_seconds == 0:
      return idle_shutdown_config(idleShutdownDisabled=True)
    # Need to convert Duration to string format since request uses http/json.
    duration_serialized = str(duration_seconds) + 's'
    return idle_shutdown_config(
        idleShutdownDisabled=False, idleTimeout=duration_serialized
    )
  return None


def GetEucConfigFromArgs(args, messages):
  """Constructs the euc config from command line args.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.

  Returns:
    Euc config for the runtime template.
  """
  return messages.GoogleCloudAiplatformV1beta1NotebookEucConfig(
      eucDisabled=not (args.enable_euc)
  )


def GetShieldedVmConfigFromArgs(args, messages):
  """Constructs the shielded vm config from command line args.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.

  Returns:
    Shielded vm config for the runtime template.
  """
  return messages.GoogleCloudAiplatformV1beta1ShieldedVmConfig(
      enableSecureBoot=args.enable_secure_boot,
  )


def GetNetworkTagsFromArgs(args):
  return args.network_tags if args.IsSpecified('network_tags') else []


def CreateEncryptionSpecConfig(args, messages):
  """Constructs the encryption spec from the kms key resource arg.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.

  Returns:
    Encryption spec for the runtime template.
  """
  encryption_spec = messages.GoogleCloudAiplatformV1beta1EncryptionSpec
  if args.IsSpecified('kms_key'):
    return encryption_spec(
        kmsKeyName=args.CONCEPTS.kms_key.Parse().RelativeName()
    )
  # Runtime template will use Google-managed encryption key if kms not specified
  return None


def GetRuntimeTemplateResourceName(args):
  """Get the resource name for the runtime template.

  Args:
    args: Argparse object from Command.Run

  Returns:
    The resource name in the form
    projects/{project}/locations/{location}/notebookRuntimeTemplates/{runtime_template_id}.
  """
  return args.CONCEPTS.runtime_template.Parse().RelativeName()


def CreateRuntimeTemplate(args, messages):
  """Creates the RuntimeTemplate message for the create request.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the RuntimeTemplate message.
  """
  return messages.GoogleCloudAiplatformV1beta1NotebookRuntimeTemplate(
      name=args.runtime_template_id,
      displayName=args.display_name,
      description=args.description,
      machineSpec=GetMachineSpecFromArgs(args, messages),
      dataPersistentDiskSpec=GetPersistentDiskSpecFromArgs(args, messages),
      networkSpec=GetNetworkSpecFromArgs(args, messages),
      labels=GetLabelsFromArgs(args, messages),
      idleShutdownConfig=GetIdleShutdownConfigFromArgs(args, messages),
      eucConfig=GetEucConfigFromArgs(args, messages),
      shieldedVmConfig=GetShieldedVmConfigFromArgs(args, messages),
      networkTags=GetNetworkTagsFromArgs(args),
      encryptionSpec=CreateEncryptionSpecConfig(args, messages),
  )


def CreateRuntimeTemplateCreateRequest(args, messages):
  """Builds a CreateNotebookRuntimeTemplateRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the CreateNotebookRuntimeTemplateRequest message.
  """

  parent = GetParentForRuntimeTemplate(args)
  runtime_template = CreateRuntimeTemplate(args, messages)
  return (
      messages.AiplatformProjectsLocationsNotebookRuntimeTemplatesCreateRequest(
          googleCloudAiplatformV1beta1NotebookRuntimeTemplate=runtime_template,
          notebookRuntimeTemplateId=args.runtime_template_id,
          parent=parent,
      )
  )


def CreateRuntimeTemplateDeleteRequest(args, messages):
  """Builds a DeleteNotebookRuntimeTemplateRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the DeleteNotebookRuntimeTemplateRequest message.
  """

  return (
      messages.AiplatformProjectsLocationsNotebookRuntimeTemplatesDeleteRequest(
          name=GetRuntimeTemplateResourceName(args),
      )
  )


def CreateRuntimeTemplateGetRequest(args, messages):
  """Builds a GetNotebookRuntimeTemplateRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the GetNotebookRuntimeTemplateRequest message.
  """

  return (
      messages.AiplatformProjectsLocationsNotebookRuntimeTemplatesGetRequest(
          name=GetRuntimeTemplateResourceName(args),
      )
  )


def CreateRuntimeTemplateListRequest(args, messages):
  """Builds a ListNotebookRuntimeTemplatesRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the ListNotebookRuntimeTemplatesRequest message.
  """

  return (
      messages.AiplatformProjectsLocationsNotebookRuntimeTemplatesListRequest(
          parent=GetParentForRuntimeTemplate(args),
      )
  )


def CreateRuntimeTemplateGetIamPolicyRequest(args, messages):
  """Builds a RuntimeTemplatesGetIamPolicyRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the RuntimeTemplatesGetIamPolicyRequest message.
  """
  return messages.AiplatformProjectsLocationsNotebookRuntimeTemplatesGetIamPolicyRequest(
      resource=GetRuntimeTemplateResourceName(args))


def CreateRuntimeTemplateSetIamPolicyRequest(iam_policy, args, messages):
  """Builds a RuntimeTemplatesSetIamPolicyRequest message.

  Args:
    iam_policy: The IAM policy to set.
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the RuntimeTemplatesSetIamPolicyRequest message.
  """
  google_iam_set_policy_request = messages.GoogleIamV1SetIamPolicyRequest(
      policy=iam_policy)
  return messages.AiplatformProjectsLocationsNotebookRuntimeTemplatesSetIamPolicyRequest(
      googleIamV1SetIamPolicyRequest=google_iam_set_policy_request,
      resource=GetRuntimeTemplateResourceName(args)
  )


def CreateRuntimeTemplateSetIamPolicyRequestFromFile(args, messages):
  """Reads policy file from args to build a RuntimeTemplatesSetIamPolicyRequest.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the RuntimeTemplatesSetIamPolicyRequest message.
  """
  policy = iam_util.ParsePolicyFile(
      args.policy_file, messages.GoogleIamV1Policy)
  return CreateRuntimeTemplateSetIamPolicyRequest(policy, args, messages)
