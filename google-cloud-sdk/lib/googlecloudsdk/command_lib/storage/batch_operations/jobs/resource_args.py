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
"""Shared resource args for batch-operations jobs commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps as deps_lib
from googlecloudsdk.command_lib.util.concepts import concept_parsers

_SBO_CLH_LOCATION_GLOBAL = 'global'


def location_attribute_config():
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text=(
          'Batch-operations supported Google Cloud location for the {resource}.'
      ),
      fallthroughs=[
          # All batch operations jobs are sent to the global-clh.
          deps_lib.ValueFallthrough(_SBO_CLH_LOCATION_GLOBAL)
      ],
  )


def batch_job_attribute_config():
  return concepts.ResourceParameterAttributeConfig(
      name='batch-job', help_text='Batch Job ID for the {resource}.'
  )


def get_batch_job_resource_spec():
  return concepts.ResourceSpec(
      'storagebatchoperations.projects.locations.jobs',
      resource_name='batch-job',
      jobsId=batch_job_attribute_config(),
      locationsId=location_attribute_config(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def add_batch_job_resource_arg(parser, verb):
  """Adds a resource argument for storage batch-operations job.

  Args:
    parser: The argparser parser to add the resource arg to.
    verb: str, the verb to describe the resource, such as 'to create'
  """
  concept_parsers.ConceptParser.ForResource(
      'batch_job',
      get_batch_job_resource_spec(),
      'The batch job {}.'.format(verb),
      required=True,
      # Hide the location flag since all batch operations jobs are sent to the
      # global-clh and we don't want to expose this to the user.
      flag_name_overrides={'location': ''},
  ).AddToParser(parser)
