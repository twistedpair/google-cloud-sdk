# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Flags and helpers for the compute node templates commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.util.args import labels_util


def MakeNodeTemplateArg():
  return compute_flags.ResourceArgument(
      resource_name='node templates',
      regional_collection='compute.nodeTemplates',
      region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION)


def _BinarySizeOrAny(default_unit):
  """Parses the value 'any' or a binary size converted to the default unit."""
  # pylint: disable=protected-access
  bytes_per_unit = arg_parsers.GetBinarySizePerUnit(default_unit)
  def _Parse(value):
    value = value.lower()
    if value == 'any':
      return value
    size = arg_parsers.BinarySize(default_unit=default_unit)(value)
    converted_size = size // bytes_per_unit
    return str(converted_size)
  return _Parse


def _IntOrAny():
  def _Parse(value):
    value = value.lower()
    if value == 'any':
      return value
    # Validate that an integer is passed.
    value = int(value)
    return str(value)
  return _Parse


def AddCreateArgsToParser(parser):
  """Add flags for creating a node template to the argument parser."""
  parser.add_argument(
      '--description',
      help='An optional description of this resource.')
  parser.add_argument(
      '--node-affinity-labels',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(
          key_type=labels_util.KEY_FORMAT_VALIDATOR,
          value_type=labels_util.VALUE_FORMAT_VALIDATOR),
      action=arg_parsers.UpdateAction,
      help='Labels to use for node affinity, which will be used in instance '
           'scheduling. This corresponds to the `--node-affinity` flag on '
           '`compute instances create` and `compute instance-templates '
           'create`.')
  node_type_group = parser.add_group(mutex=True, required=True)
  node_type_group.add_argument(
      '--node-type',
      help="""\
          The node type to use for nodes in node groups using this template.
          The type of a node determines what resources are available to
          instances running on the node.

          See the following for more information:

              $ gcloud alpha compute sole-tenancy node-types""")
  node_type_group.add_argument(
      '--node-requirements',
      type=arg_parsers.ArgDict(
          spec={
              'vCPU': _IntOrAny(),
              'memory': _BinarySizeOrAny('MB'),
              'localSSD': _BinarySizeOrAny('GB'),
          }),
      help="""\
The requirements for nodes. Google Compute Engine will automatically
choose a node type that fits the requirements on Node Group creation.
If multiple node types match your defined criteria, the NodeType with
the least amount of each resource will be selected. You can specify 'any'
to indicate any non-zero value for a certain resource.

The following keys are allowed:

*vCPU*:::: The number of committed cores available to the node.

*memory*:::: The amount of memory available to the node. This value
should include unit (eg. 3072MB or 9GB). If no units are specified,
*MB is assumed*.

*localSSD*:::: Optional. The amount of SSD space available on the
node. This value should include unit (eg. 3072MB or 9GB). If no
units are specified, *GB is assumed*. If this key is not specified, local SSD is
unconstrained.
      """)
