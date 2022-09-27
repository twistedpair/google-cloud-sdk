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

"""Shared resource arguments for Cloud Batch commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core import properties


def LocationAttributeConfig():
  fts = [deps.PropertyFallthrough(properties.VALUES.batch.location)]
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='Google Cloud location for the {resource}.',
      fallthroughs=fts)


def JobAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='job',
      help_text='The job ID for the {resource}.')


def TaskGroupAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='task_group',
      help_text='The task_group ID for the {resource}.')


def TaskAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='task',
      help_text='The task ID for the {resource}.')


def GetLocationResourceSpec():
  return concepts.ResourceSpec(
      'batch.projects.locations',
      resource_name='location',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)


def GetJobResourceSpec():
  return concepts.ResourceSpec(
      'batch.projects.locations.jobs',
      resource_name='job',
      jobsId=JobAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)


def GetTaskResourceSpec():
  return concepts.ResourceSpec(
      'batch.projects.locations.jobs.taskGroups.tasks',
      resource_name='task',
      tasksId=TaskAttributeConfig(),
      taskGroupsId=TaskGroupAttributeConfig(),
      jobsId=JobAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)


def AddLocationResourceArgs(parser):
  """Add the location resource argument.

  Args:
    parser: the parser for the command.
  """
  arg_specs = [
      presentation_specs.ResourcePresentationSpec(
          '--location',
          GetLocationResourceSpec(),
          ('The Batch location resource. If you omit this flag, the default'
           'location is used if you set the batch/location property.'
           'Otherwise, omitting this flag lists jobs across all locations.'),
          required=False,
      ),
  ]

  concept_parsers.ConceptParser(arg_specs).AddToParser(parser)


def AddJobFlagResourceArgs(parser):
  """Add the job resource argument as flag.

  Args:
    parser: the parser for the command.
  """
  arg_specs = [
      presentation_specs.ResourcePresentationSpec(
          '--job',
          GetJobResourceSpec(),
          ('The Batch job resource. If not specified,'
           'the current batch/location is used.'),
          required=True,
      ),
  ]

  concept_parsers.ConceptParser(arg_specs).AddToParser(parser)


def AddJobResourceArgs(parser):
  """Add the job resource argument as positional.

  Args:
    parser: the parser for the command.
  """
  arg_specs = [
      presentation_specs.ResourcePresentationSpec(
          'JOB',
          GetJobResourceSpec(),
          ('The Batch job resource. If not specified,'
           'the current batch/location is used.'),
          required=True,
      ),
  ]

  concept_parsers.ConceptParser(arg_specs).AddToParser(parser)


def AddTaskResourceArgs(parser):
  """Add the task resource argument.

  Args:
    parser: the parser for the command.
  """
  arg_specs = [
      presentation_specs.ResourcePresentationSpec(
          'TASK',
          GetTaskResourceSpec(),
          ('The Batch task resource. If not specified,'
           'the current batch/location is used.'),
          required=True,
      ),
  ]

  concept_parsers.ConceptParser(arg_specs).AddToParser(parser)
