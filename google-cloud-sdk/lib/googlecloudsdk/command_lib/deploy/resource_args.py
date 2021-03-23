# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Resource flags and helpers for the deploy command group."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties


def DeliveryPipelineAttributeConfig():
  """Creates the delivery pipeline resource attribute."""
  return concepts.ResourceParameterAttributeConfig(
      name='delivery-pipeline',
      fallthroughs=[
          deps.PropertyFallthrough(
              properties.FromString('deploy/delivery_pipeline'))
      ],
      help_text='The delivery pipeline associated with the {resource}. '
      ' Alternatively, set the property [deploy/delivery-pipeline].')


def AddReleaseResourceArg(parser,
                          help_text=None,
                          positional=False,
                          required=True):
  """Add --release resource argument to the parser.

  Args:
    parser: argparse.ArgumentParser, the parser for the command.
    help_text: help text for this flag.
    positional: if it is a positional flag.
    required: if it is required.
  """
  help_text = help_text or 'The name of the Release.'

  concept_parsers.ConceptParser.ForResource(
      'release' if positional else '--release',
      GetReleaseResourceSpec(),
      help_text,
      required=required,
      plural=False).AddToParser(parser)


def GetReleaseResourceSpec():
  """Constructs and returns the Resource specification for Delivery Pipeline."""
  return concepts.ResourceSpec(
      'clouddeploy.projects.locations.deliveryPipelines.releases',
      resource_name='release',
      deliveryPipelinesId=DeliveryPipelineAttributeConfig(),
      releasesId=ReleaseAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      disable_auto_completers=False)


def ReleaseAttributeConfig():
  """Creates the release resource attribute."""
  return concepts.ResourceParameterAttributeConfig(
      name='release', help_text='The release associated with the {resource}.')


def LocationAttributeConfig():
  """Creates the location resource attribute."""
  return concepts.ResourceParameterAttributeConfig(
      name='region',
      parameter_name='locationsId',
      fallthroughs=[
          deps.PropertyFallthrough(properties.FromString('deploy/region'))
      ],
      help_text='The Cloud region for the {resource}. '
      ' Alternatively, set the property [deploy/region].')
