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
"""Flags for the compute zone vm extension policies commands."""

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

      If not specified, ALL VMs in the zone will be selected.
      """),
  )


def AddZoneFlag(parser):
  """Adds the zone flag."""
  parser.add_argument(
      '--zone',
      required=True,
      help="""
      The zone to list the extension policies from.
      """,
  )


def MakeZoneVmExtensionPolicyArg():
  return compute_flags.ResourceArgument(
      resource_name='zone vm extension policy',
      zonal_collection='compute.zoneVmExtensionPolicies',
      required=True,
      plural=False,
      zone_explanation=compute_flags.ZONE_PROPERTY_EXPLANATION,
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


def BuildZoneVmExtensionPolicy(resource_ref, args, messages):
  """Builds the VmExtensionPolicy resource given the resource reference and args."""

  def BuildInclusionLabelsValue(inclusion_labels):
    return [
        messages.VmExtensionPolicyLabelSelector.InclusionLabelsValue.AdditionalProperty(
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
        messages.VmExtensionPolicy.ExtensionPoliciesValue.AdditionalProperty(
            key=extension,
            value=messages.VmExtensionPolicyExtensionPolicy(
                stringConfig=configs.get(extension),
                pinnedVersion=(args.version or {}).get(extension),
            ),
        )
        for extension in args.extensions
    ]

  return messages.VmExtensionPolicy(
      name=resource_ref.Name(),
      description=args.description,
      priority=args.priority,
      extensionPolicies=messages.VmExtensionPolicy.ExtensionPoliciesValue(
          additionalProperties=BuildExtensionPoliciesValue()
      ),
      instanceSelectors=[
          messages.VmExtensionPolicyInstanceSelector(
              labelSelector=messages.VmExtensionPolicyLabelSelector(
                  inclusionLabels=messages.VmExtensionPolicyLabelSelector.InclusionLabelsValue(
                      additionalProperties=BuildInclusionLabelsValue(
                          inclusion_label
                      )
                  ),
              )
          )
          for inclusion_label in args.inclusion_labels
      ],
  )



