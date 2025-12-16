# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Flags for the compute global vm extension policies commands."""

import functools
import textwrap

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.core.util import files


def AddPolicyDescription(parser):
  """Adds the Description flag."""
  parser.add_argument(
      '--description',
      help='An optional text description for the extension policy.',
  )


def AddPolicyPriority(parser):
  """Adds the Priority flag."""

  def ValidatePriority(arg_value, min_val, max_val) -> int:
    """Custom type function to validate an integer within a specified range."""
    try:
      value = int(arg_value)
    except ValueError:
      raise compute_flags.BadArgumentException(
          f"'{arg_value}' is not a valid integer."
      )

    if not (min_val <= value <= max_val):
      raise compute_flags.BadArgumentException(
          f"Value '{value}' is not in the range [{min_val}-{max_val}]."
      )
    return value

  parser.add_argument(
      '--priority',
      type=functools.partial(ValidatePriority, min_val=0, max_val=65535),
      default=1000,
      help=textwrap.dedent("""\
      The priority of the policy. Lower the number, higher the priority.
      When two policies try to apply the same extension to a VM, the policy with
      higher priority takes precedence. If the priorities are the same, the
      policy with the more recent update timestamp takes precedence. If a policy
      is deleted, the extension remains installed on the VM if a lower-priority
      policy still applies.

      Range from 0 to 65535. Default is 1000.
      """),
  )


def AddPolicyInclusionLabels(parser):
  """Adds the InclusionLabels flag."""
  parser.add_argument(
      '--inclusion-labels',
      action='append',
      default=[],
      help=textwrap.dedent("""\
      A list of inclusion labels to select the target VMs.

      The expected format for a single selector is "key1=value1,key2=value2".
      A VM is selected if it has ALL the inclusion labels.

      When the option is specified multiple times, it assumes a logical OR between the selectors.

      For example, if the inclusion labels are ["env=prod,workload=frontend", "workload=backend"], the following VMs will be selected:
      - VM1: env=prod, workload=frontend, something=else
      - VM2: env=prod, workload=backend
      But not:
      - VM3: env=prod

      If not specified, ALL VMs in the project/folder will be selected.
      """),
  )


def AddExtensions(parser):
  """Adds the Extensions flag."""
  parser.add_argument(
      '--extensions',
      required=True,
      action=arg_parsers.StoreOnceAction,
      default=[],
      metavar='EXTENSION_NAME',
      type=arg_parsers.ArgList(min_length=1),
      help='One or more extensions to be added to the policy.',
  )


def AddExtensionVersion(parser):
  """Adds --version flag."""
  parser.add_argument(
      '--version',
      type=arg_parsers.ArgDict(min_length=1),
      default={},
      metavar='KEY=VALUE',
      action=arg_parsers.StoreOnceAction,
      required=False,
      help=textwrap.dedent("""\
      A comma separated key:value list where the key is the extension name and the value is the
      desired version for the given extension. The extension name must be one of the extensions
      specified in the --extensions flag. If no version is specified for an
      extension, the latest version will be used and will be upgraded automatically.

      E.g. --version=filestore=123ABC,ops-agent=456DEF

      Raises:
        ArgumentTypeError: If the extension name is not specified in the
        --extensions flag.
      """),
  )


def AddExtensionConfigs(parser):
  """Adds the --config flag."""
  parser.add_argument(
      '--config',
      type=arg_parsers.ArgDict(min_length=1),
      default={},
      metavar='KEY=VALUE',
      action=arg_parsers.StoreOnceAction,
      required=False,
      help=textwrap.dedent("""\
      A comma separated key:value list where the key is the extension name and the value is the
      desired config for the given extension. The extension name must be one of the extensions
      specified in the --extensions flag.

      E.g. --config=filestore='filestore config',ops-agent='ops agent config'

      Raises:
        ArgumentTypeError: If the extension name is not specified in the
        --extensions flag.
      """),
  )


def AddExtensionConfigsFromFile(parser):
  """Adds the --config-from-file flag."""
  parser.add_argument(
      '--config-from-file',
      type=arg_parsers.ArgDict(min_length=1),
      default={},
      metavar='KEY=FILE_PATH',
      action=arg_parsers.StoreOnceAction,
      required=False,
      help=textwrap.dedent("""\
      Same as --config except that the value for the entry will be read from a
      local file. The extension name must be one of the extensions specified in
      the --extensions flag.

      It is an error to specify the same extension in both --config and
      --config-from-file.
      """),
  )


def AddRolloutPredefinedPlan(parser):
  """Adds the --rollout-predefined-plan flag."""
  parser.add_argument(
      '--rollout-predefined-plan',
      choices=[
          'fast_rollout',
          'slow_rollout'
      ],
      default=None,
      action=arg_parsers.StoreOnceAction,
      required=False,
      help=textwrap.dedent("""\
      Provide the name of a predefined rollout plan from
      [fast_rollout, slow_rollout] to be used for the rollout.

      One of either --rollout-predefined-plan or --rollout-custom-plan must be specified,
      but not both.
      """),
  )


def AddRolloutCustomPlan(parser):
  """Adds the --rollout-custom-plan flag."""
  parser.add_argument(
      '--rollout-custom-plan',
      default='',
      action=arg_parsers.StoreOnceAction,
      required=False,
      help=textwrap.dedent("""\
      Provide the name of a custom rollout plan to be used for the rollout.

      One of either --rollout-predefined-plan or --rollout-custom-plan must be specified,
      but not both.
      """),
  )


def AddRolloutConflictBehavior(parser):
  """Adds the --rollout-conflict-behavior flag."""
  parser.add_argument(
      '--rollout-conflict-behavior',
      default='',
      action=arg_parsers.StoreOnceAction,
      required=False,
      help=textwrap.dedent("""\
      Specifies the behavior of a rollout if a conflict is detected between
      a zonal policy and a global policy. See gcloud compute
      zone-vm-extension-policies for more details on zonal policies.

      The possible values are:
      * `""`: The zonal policy value is used in case of a conflict. This is the default behavior.
      * `overwrite`: The global policy overwrites the zonal policy.

      If you set `--rollout-conflict-behavior` to `overwrite` and want to revert to the default behavior,
      use the update command and omit the `--rollout-conflict-behavior`
      flag.
      """),
  )


def AddRolloutRetryUUID(parser):
  """Adds the --rollout-retry-uuid flag."""
  parser.add_argument(
      '--rollout-retry-uuid',
      default='',
      action=arg_parsers.StoreOnceAction,
      required=False,
      help=textwrap.dedent("""\
      The UUID of the rollout retry action. Only set it if this is a retry
      for an existing resource.
      """),
  )


def MakeGlobalVmExtensionPolicyArg():
  return compute_flags.ResourceArgument(
      resource_name='global vm extension policy',
      global_collection='compute.globalVmExtensionPolicies',
      required=True,
      plural=False,
  )


def AddExtensionPolicyArgs(parser):
  """Adds the flags for a VM extension policy."""
  AddPolicyDescription(parser)
  AddPolicyPriority(parser)
  AddPolicyInclusionLabels(parser)
  AddExtensions(parser)
  AddExtensionVersion(parser)
  AddExtensionConfigs(parser)
  AddExtensionConfigsFromFile(parser)
  AddRolloutPlanArgs(parser)


def AddRolloutPlanArgs(parser):
  """Adds the flags for a rollout plan."""
  AddRolloutPredefinedPlan(parser)
  AddRolloutCustomPlan(parser)


def ParseExtensionConfigs(extensions, configs, config_from_file=None):
  """Parses the extension configs."""
  extensions_set = set(extensions)
  if configs:
    config_extensions_set = set(configs.keys())
    extra_extensions = config_extensions_set - extensions_set
    if extra_extensions:
      raise exceptions.BadArgumentException(
          '--config',
          f'Extensions {extra_extensions} from --config are not specified in'
          f' the --extensions flag. {extensions}'
      )
  if config_from_file:
    config_from_file_extensions_set = set(config_from_file.keys())
    extra_extensions = config_from_file_extensions_set - extensions_set
    if extra_extensions:
      raise exceptions.BadArgumentException(
          '--config-from-file',
          f'Extensions {extra_extensions} from --config-from-file are not'
          f' specified in the --extensions flag. {extensions}'
      )
  if configs and config_from_file:
    common_extensions = set(configs.keys()) & set(config_from_file.keys())
    if common_extensions:
      raise exceptions.BadArgumentException(
          '--config and --config-from-file',
          f'Extensions {common_extensions} are specified in both --config and'
          ' --config-from-file.'
      )


def ParseRolloutPlan(rollout_predefined_plan, rollout_custom_plan):
  """Parses the rollout plan."""
  if rollout_predefined_plan and rollout_custom_plan:
    raise exceptions.BadArgumentException(
        '--rollout-predefined-plan and --rollout-custom-plan',
        'Only one of --rollout-predefined-plan and --rollout-custom-plan can be'
        ' specified.',
    )
  if not rollout_predefined_plan and not rollout_custom_plan:
    raise exceptions.BadArgumentException(
        '--rollout-predefined-plan and --rollout-custom-plan',
        'One of --rollout-predefined-plan and --rollout-custom-plan'
        ' must be specified.',
    )


def ParseExtensionVersions(extensions, versions):
  """Parses the extension versions."""
  if not versions:
    return
  extensions_set = set(extensions)
  versions_extensions_set = set(versions.keys())
  extra_extensions = versions_extensions_set - extensions_set
  if extra_extensions:
    raise exceptions.BadArgumentException(
        '--version',
        f'Extensions {extra_extensions} from --version are not specified in'
        f' the --extensions flag. {extensions}'
    )


def InsertRetryUuid(args, gve_policy=None, rollout_operation_input=None):
  """Inserts the retry UUID into the resource if it exists."""
  # This function is used by Update and Delete. The Update command uses a
  # gve_policy resource, and the Delete command uses a rollout_operation_input
  # resource.
  if gve_policy and rollout_operation_input:
    raise exceptions.BadArgumentException(
        '--rollout-retry-uuid',
        'Only one of gve_policy and rollout_operation_input can be set.',
    )
  if args.rollout_retry_uuid:
    if gve_policy:
      gve_policy.rolloutOperation.rolloutInput.retryUuid = (
          args.rollout_retry_uuid
      )
    elif rollout_operation_input:
      rollout_operation_input.retryUuid = args.rollout_retry_uuid


def _GetConfigs(args):
  """Returns a dictionary of extension configs."""
  configs = {}
  if args.config:
    configs.update(args.config)
  if getattr(args, 'config_from_file', None):
    for extension, file_path in args.config_from_file.items():
      try:
        configs[extension] = files.ReadFileContents(file_path)
      except files.Error as e:
        raise exceptions.BadFileException(
            f'Could not read config file [{file_path}] for extension'
            f' [{extension}]: {e}'
        )
  return configs


def BuildRolloutOperationInput(args, messages):
  """Builds the RolloutOperation input resource given the resource reference and args."""

  ParseRolloutPlan(args.rollout_predefined_plan, args.rollout_custom_plan)
  rollout_predefined_plan = None
  if args.rollout_predefined_plan:
    rollout_predefined_plan = messages.GlobalVmExtensionPolicyRolloutOperationRolloutInput.PredefinedRolloutPlanValueValuesEnum(
        args.rollout_predefined_plan.upper()
        )

  return messages.GlobalVmExtensionPolicyRolloutOperationRolloutInput(
      predefinedRolloutPlan=rollout_predefined_plan,
      name=args.rollout_custom_plan or None,
      conflictBehavior=getattr(args, 'rollout_conflict_behavior', None) or None,
  )


def BuildGlobalVmExtensionPolicy(resource_ref, args, messages):
  """Builds the VmExtensionPolicy resource given the resource reference and args."""

  def BuildInclusionLabelsValue(inclusion_labels):
    return [
        messages.GlobalVmExtensionPolicyLabelSelector.InclusionLabelsValue.AdditionalProperty(
            key=key,
            value=value,
        )
        for key, value in (
            labels_util.ValidateAndParseLabels(inclusion_labels.split(','))
            or {}
        ).items()
    ]

  def BuildExtensionPoliciesValue():
    configs = _GetConfigs(args)
    return [
        messages.GlobalVmExtensionPolicy.ExtensionPoliciesValue.AdditionalProperty(
            key=extension,
            value=messages.GlobalVmExtensionPolicyExtensionPolicy(
                stringConfig=configs.get(extension),
                pinnedVersion=(args.version or {}).get(extension),
            ),
        )
        for extension in args.extensions
    ]

  ParseExtensionConfigs(args.extensions, args.config, args.config_from_file)
  ParseExtensionVersions(args.extensions, args.version)

  return messages.GlobalVmExtensionPolicy(
      name=resource_ref.Name(),
      description=args.description,
      priority=args.priority,
      extensionPolicies=messages.GlobalVmExtensionPolicy.ExtensionPoliciesValue(
          additionalProperties=BuildExtensionPoliciesValue()
      ),
      instanceSelectors=[
          messages.GlobalVmExtensionPolicyInstanceSelector(
              labelSelector=messages.GlobalVmExtensionPolicyLabelSelector(
                  inclusionLabels=messages.GlobalVmExtensionPolicyLabelSelector.InclusionLabelsValue(
                      additionalProperties=BuildInclusionLabelsValue(
                          inclusion_label
                      )
                  ),
              )
          )
          for inclusion_label in args.inclusion_labels
      ],
      rolloutOperation=messages.GlobalVmExtensionPolicyRolloutOperation(
          rolloutInput=BuildRolloutOperationInput(args, messages)
      ),
  )



