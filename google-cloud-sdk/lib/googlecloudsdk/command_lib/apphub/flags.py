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
"""Apphub Command Lib Flags."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.apphub import utils as apphub_utils
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def AddTopologyUpdateFlags(parser):
  """Adds flags to topology update command.

  Flags include:
    --enable
    --disable

  Args:
    parser: The argparser.
  """

  state_group = parser.add_group(mutex=True, help='Manage topology state.')
  state_group.add_argument(
      '--enable',
      action='store_const',
      const=True,
      help='Enable topology.',
  )
  state_group.add_argument(
      '--disable',
      action='store_const',
      const=True,
      help='Disable topology.',
  )


def AddTelemetryUpdateFlags(parser):
  """Adds flags to telemetry update command.

  Flags include:
    --enable-monitoring
    --disable-monitoring

  Args:
    parser: The argparser.
  """

  state_group = parser.add_group(
      mutex=True, help='Manage telemetry monitoring state.'
  )
  state_group.add_argument(
      '--enable-monitoring',
      action='store_const',
      const=True,
      help='Enable telemetry monitoring.',
  )
  state_group.add_argument(
      '--disable-monitoring',
      action='store_const',
      const=True,
      help='Disable telemetry monitoring.',
  )


def GetLocationResourceSpec():
  return concepts.ResourceSpec(
      'apphub.projects.locations',
      resource_name='location',
      locationsId=_DefaultToGlobalLocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def _DefaultToGlobalLocationAttributeConfig(help_text=None):
  """Create basic attributes that fallthrough location to global in resource argument.

  Args:
    help_text: If set, overrides default help text

  Returns:
    Resource argument parameter config
  """
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      fallthroughs=[
          deps.Fallthrough(
              function=apphub_utils.DefaultToGlobal,
              hint='global is the only supported location',
          )
      ],
      help_text=help_text if help_text else ('Name of the {resource}.'),
  )


def GetLocationResourceArg(
    arg_name='location',
    help_text=None,
    positional=False,
    required=False,
):
  """Constructs and returns the Location Resource Argument."""

  help_text = help_text or 'Location'

  return concept_parsers.ConceptParser.ForResource(
      '{}{}'.format('' if positional else '--', arg_name),
      GetLocationResourceSpec(),
      help_text,
      required=required,
  )


def GetServiceProjectResourceSpec(arg_name='service_project', help_text=None):
  """Constructs and returns the Resource specification for Service project."""

  def ServiceProjectAttributeConfig():
    return concepts.ResourceParameterAttributeConfig(
        name=arg_name,
        help_text=help_text,
    )

  return concepts.ResourceSpec(
      'apphub.projects.locations.serviceProjectAttachments',
      resource_name='ServiceProjectAttachment',
      serviceProjectAttachmentsId=ServiceProjectAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=_DefaultToGlobalLocationAttributeConfig(),
  )


def GetServiceProjectResourceArg(
    arg_name='service_project', help_text=None, positional=True, required=True
):
  """Constructs and returns the Service Project Resource Argument."""

  help_text = help_text or 'Name for the Service Project'

  return concept_parsers.ConceptParser.ForResource(
      '{}{}'.format('' if positional else '--', arg_name),
      GetServiceProjectResourceSpec(),
      help_text,
      required=required,
  )


def AddDescribeServiceProjectFlags(parser):
  GetServiceProjectResourceArg().AddToParser(parser)


def AddListServiceProjectFlags(parser):
  GetLocationResourceArg().AddToParser(parser)


def AddServiceProjectFlags(parser):
  GetServiceProjectResourceArg().AddToParser(parser)
  parser.add_argument(
      '--async',
      dest='async_',
      action='store_true',
      default=False,
      help='async operation.',
  )


def AddRemoveServiceProjectFlags(parser):
  GetServiceProjectResourceArg().AddToParser(parser)
  parser.add_argument(
      '--async',
      dest='async_',
      action='store_true',
      default=False,
      help='async operation.',
  )
