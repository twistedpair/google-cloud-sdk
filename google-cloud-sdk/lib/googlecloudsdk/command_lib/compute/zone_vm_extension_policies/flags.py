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

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.util.args import labels_util


def AddPolicyDescription(parser):
  """Adds the Description flag."""
  parser.add_argument(
      '--description',
      help='An optional textual description for the this extension policy.',
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
      help="""
      The priority of the policy. Lower the number, higher the priority.
      When two policies tries to apply the same extension, the one with the higher priority takes precedence.
      If the priority is the same, the one with the more recent update timestamp takes precedence.
      When a policy is deleted, the extension would remain installed on the VM if a lower priority policy still applies.

      Range from 0 to 65535. Default is 1000.
      """,
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
      help="""
      A comma separated key:value list where the key is the extension name and the value is the
      desired version for the given extension. The extension name must be one of the extensions
      specified in the --extensions flag. If no version is specified for an
      extension, the latest version will be used and will be upgraded automatically.

      E.g. --version=filestore=123ABC,ops-agent=456DEF
      """)


def AddExtensionConfigs(parser):
  """Adds the --config flag."""
  parser.add_argument(
      '--config',
      type=arg_parsers.ArgDict(min_length=1),
      default={},
      metavar='KEY=VALUE',
      action=arg_parsers.StoreOnceAction,
      required=False,
      help="""
      A comma separated key:value list where the key is the extension name and the value is the
      desired config for the given extension. The extension name must be one of the extensions
      specified in the --extensions flag.

      E.g. --config=filestore=,ops-agent=
      """)


def AddPolicyInclusionLabels(parser):
  """Adds the InclusionLabels flag."""
  parser.add_argument(
      '--inclusion-labels',
      action='append',
      default=[],
      help="""
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
      """,
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


def ParseExtensionConfigs(extensions, configs):
  """Parses the extension configs."""
  if not configs:
    return
  extensions_set = set(extensions)
  config_extensions_set = set(configs.keys())
  extra_extensions = config_extensions_set - extensions_set
  if extra_extensions:
    raise ValueError(
        f'Extensions {extra_extensions} from --config are not specified in the \
        --extensions flag. {extensions}'
    )


def ParseExtensionVersions(extensions, versions):
  """Parses the extension versions."""
  if not versions:
    return
  extensions_set = set(extensions)
  versions_extensions_set = set(versions.keys())
  extra_extensions = versions_extensions_set - extensions_set
  if extra_extensions:
    raise ValueError(
        f'Extensions {extra_extensions} from --version are not specified in \
        the --extensions flag. {extensions}'
    )


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
    return [
        messages.VmExtensionPolicy.ExtensionPoliciesValue.AdditionalProperty(
            key=extension,
            value=messages.VmExtensionPolicyExtensionPolicy(
                stringConfig=(args.config or {}).get(extension),
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



