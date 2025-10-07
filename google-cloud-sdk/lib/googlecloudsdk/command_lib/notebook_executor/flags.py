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
"""Utilities for flags for `gcloud notebook-executor` commands."""

from googlecloudsdk.api_lib.notebook_executor import executions as executions_util
from googlecloudsdk.api_lib.notebook_executor import schedules as schedules_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.colab_enterprise import flags as colab_flags
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core import properties


def _GetRegionAttributeConfig(for_workbench=False):
  if (for_workbench):
    fallthroughs = []
  else:
    fallthroughs = [deps.PropertyFallthrough(properties.VALUES.colab.region)]
  return concepts.ResourceParameterAttributeConfig(
      name='region',
      help_text='Cloud region for the {resource}.',
      fallthroughs=fallthroughs,
  )


def _AddExecutionResourceArg(parser, verb, for_workbench=False):
  """Add a resource argument for an execution to the parser.

  Args:
    parser: argparse parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    for_workbench: bool, whether the flag is added for a workbench execution.
  """

  def GetExecutionResourceSpec(resource_name='notebook execution job'):
    return concepts.ResourceSpec(
        'aiplatform.projects.locations.notebookExecutionJobs',
        resource_name=resource_name,
        projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
        locationsId=_GetRegionAttributeConfig(for_workbench),
    )

  concept_parsers.ConceptParser.ForResource(
      'execution',
      GetExecutionResourceSpec(),
      'Unique resource name of the execution {}.'.format(verb),
      required=True,
  ).AddToParser(parser)


def AddScheduleResourceArg(parser, verb):
  """Add a resource argument for a schedule to the parser.

  Args:
    parser: argparse parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """

  def GetScheduleResourceSpec(resource_name='schedule'):
    """Add a resource argument for a schedule to the parser.

    Args:
      resource_name: str, the name of the resource to use in attribute help
        text.

    Returns:
      A concepts.ResourceSpec for a schedule.
    """
    return concepts.ResourceSpec(
        'aiplatform.projects.locations.schedules',
        resource_name=resource_name,
        projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
        locationsId=_GetRegionAttributeConfig(),
    )

  concept_parsers.ConceptParser.ForResource(
      'schedule',
      GetScheduleResourceSpec(),
      'Unique, system-generated resource name of the schedule {}.'.format(verb),
      required=True,
  ).AddToParser(parser)


def AddDataformRepositoryResourceArg(parser):
  """Add a resource argument for a Dataform repository to the parser.

  Args:
    parser: argparse parser for the command.

  """
  def GetDataformRepositoryResourceSpec(resource_name='dataform repository'):
    return concepts.ResourceSpec(
        'dataform.projects.locations.repositories',
        resource_name=resource_name,
        projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
        locationsId=_GetRegionAttributeConfig(),
    )

  dataform_repository_resource = presentation_specs.ResourcePresentationSpec(
      '--dataform-repository-name',
      GetDataformRepositoryResourceSpec(),
      'Unique name of the Dataform repository to source input notebook from.',
      required=True,
      # This hides the region flag for the dataform repository, but as a GCP
      # resource the dataform flag will still accept a fully qualified name
      # ('projects/*/locations/*/repositories/*') or just the repository ID.
      flag_name_overrides={'region': ''},
  )
  concept_parsers.ConceptParser(
      [dataform_repository_resource],
      # By default the region flag will be the execution region.
      command_level_fallthroughs={
          '--dataform-repository-name.region': ['--region']
      },
  ).AddToParser(parser)


def _AddRegionResourceArg(parser, verb, for_workbench=False):
  """Add a resource argument for a Vertex AI region to the parser.

  Args:
    parser: argparse parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    for_workbench: bool, whether the flag is added for a workbench execution.

  """
  region_resource_spec = concepts.ResourceSpec(
      'aiplatform.projects.locations',
      resource_name='region',
      locationsId=_GetRegionAttributeConfig(for_workbench),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )

  concept_parsers.ConceptParser.ForResource(
      '--region',
      region_resource_spec,
      'Cloud region {}.'.format(verb),
      required=True,
  ).AddToParser(parser)


def _AddRuntimeTemplateResourceArg(parser):
  """Add a resource argument for a runtime template to the parser.

  Args:
    parser: argparse parser for the command.
  """

  def GetRuntimeTemplateResourceSpec(resource_name='notebook runtime template'):
    return concepts.ResourceSpec(
        'aiplatform.projects.locations.notebookRuntimeTemplates',
        resource_name=resource_name,
        projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
        locationsId=_GetRegionAttributeConfig(),
    )

  runtime_template_resource = presentation_specs.ResourcePresentationSpec(
      '--notebook-runtime-template',
      GetRuntimeTemplateResourceSpec(),
      'The runtime template specifying the compute configuration for the'
      ' notebook execution. The runtime template should be in the same region'
      ' as the execution.',
      required=True,
      # This hides the region flag for the runtime template, but as a GCP
      # resource the flag will still accept a fully qualified name
      # ('projects/*/locations/*/notebookRuntimeTemplates/*') or just the ID.
      flag_name_overrides={'region': ''},
  )
  concept_parsers.ConceptParser(
      [runtime_template_resource],
      # By default the region flag will be the execution region.
      command_level_fallthroughs={
          '--notebook-runtime-template.region': ['--region']
      },
  ).AddToParser(parser)


def AddCreateExecutionFlags(parser, is_schedule=False, for_workbench=False):
  """Adds flags for creating an execution to the parser."""
  execution_group = parser.add_group(
      help='Configuration of the execution job.',
      required=True,
  )
  if is_schedule:
    execution_group.add_argument(
        '--execution-display-name',
        help='The display name of the execution.',
        required=True,
    )
  else:
    _AddRegionResourceArg(parser, 'to create', for_workbench)
    execution_group.add_argument(
        '--display-name',
        help='The display name of the execution.',
        required=True,
    )
    parser.add_argument(
        '--execution-job-id',
        help=(
            'The id to assign to the execution job. If not specified, a random'
            ' id will be generated.'
        ),
        hidden=True,
    )
    base.ASYNC_FLAG.AddToParser(parser)

  notebook_source_group = execution_group.add_group(
      help='Source of the notebook to execute.',
      required=True,
      mutex=True,
  )
  if not for_workbench:
    dataform_source_group = notebook_source_group.add_group(
        help='The Dataform repository containing the notebook. Any notebook'
        ' created from the Colab UI is automatically stored in a Dataform'
        ' repository. The repository name can be found via the Dataform'
        ' API by listing repositories in the same project and region as the'
        ' notebook.'
    )
    AddDataformRepositoryResourceArg(dataform_source_group)
    dataform_source_group.add_argument(
        '--commit-sha',
        help='The commit SHA to read from the Dataform repository. If unset,'
        ' the file will be read from HEAD.',
    )
  gcs_source_group = notebook_source_group.add_group(
      help='The Cloud Storage notebook source.',
  )
  gcs_source_group.add_argument(
      '--gcs-notebook-uri',
      help=(
          'The Cloud Storage uri pointing to the notebook. Format: '
          'gs://bucket/notebook_file.ipynb'
      ),
      required=True,
  )
  gcs_source_group.add_argument(
      '--generation',
      help=(
          'The version of the Cloud Storage object to read. If unset, the'
          ' current version of the object will be used.'
      ),
  )
  if not is_schedule:
    notebook_source_group.add_argument(
        '--direct-content',
        help=(
            'The direct notebook content as IPYNB. This can be a local filepath'
            ' to an .ipynb file or can be set to `-` to read content from'
            ' stdin.'
        ),
    )
  execution_group.add_argument(
      '--execution-timeout',
      help=(
          "The max running time of the execution job, as a duration. See '$"
          " gcloud topic datetimes' for details on formatting the input"
          ' duration.'
      ),
      type=arg_parsers.Duration(),
      default='24h',
  )
  if for_workbench:
    custom_env_spec_group = execution_group.add_group(
        help='Compute configuration of the execution job.',
    )
    colab_flags.AddCustomEnvSpecFlags(custom_env_spec_group)
    colab_flags.AddKmsKeyResourceArg(
        execution_group,
        'The Cloud KMS encryption key (customer-managed encryption key) used to'
        ' protect the execution. The key must be in the same region as the'
        ' execution. If not specified, Google-managed encryption will be used.',
    )
    execution_group.add_argument(
        '--kernel-name',
        help='The kernel name to use for the execution.',
        default='python3',
    )
    execution_group.add_argument(
        '--service-account',
        help='The service account to run the execution as',
        required=True,
    )
  else:
    _AddRuntimeTemplateResourceArg(execution_group)
    execution_identity_group = execution_group.add_group(
        help='Identity to run the execution as.',
        mutex=True,
        required=True,
    )
    execution_identity_group.add_argument(
        '--user-email',
        help='The user email to run the execution as. This requires the'
        ' provided runtime template to have end user credentials enabled.',
    )
    execution_identity_group.add_argument(
        '--service-account',
        help='The service account to run the execution as.',
        required=False,
    )
  execution_group.add_argument(
      '--gcs-output-uri',
      help=(
          'The Cloud Storage location to upload notebook execution results to.'
          ' Format: gs://bucket-name.'
      ),
      required=True,
  )


def AddDeleteExecutionFlags(parser, for_workbench=False):
  """Adds flags for deleting an execution to the parser.

  Args:
    parser: argparse parser for the command.
    for_workbench: bool, whether the flags are for a workbench execution.

  """
  _AddExecutionResourceArg(parser, 'to delete', for_workbench)
  base.ASYNC_FLAG.AddToParser(parser)


def AddDescribeExecutionFlags(parser, for_workbench=False):
  """Adds flags for describing an execution to the parser.

  Args:
    parser: argparse parser for the command.
    for_workbench: bool, whether the flag is added for a workbench execution.
  """
  _AddExecutionResourceArg(parser, 'to describe', for_workbench)


def AddListExecutionsFlags(parser, for_workbench=False):
  """Construct groups and arguments specific to listing executions.

  Args:
    parser: argparse parser for the command.
    for_workbench: bool, whether the flag is added for a workbench execution.
  """
  _AddRegionResourceArg(
      parser, 'for which to list all executions', for_workbench
  )
  parser.display_info.AddUriFunc(executions_util.GetExecutionUri)


def AddDescribeScheduleFlags(parser):
  """Add flags for describing a schedule to the parser."""
  AddScheduleResourceArg(parser, 'to describe')


def AddDeleteScheduleFlags(parser):
  """Adds flags for deleting a schedule to the parser."""
  AddScheduleResourceArg(parser, 'to delete')
  base.ASYNC_FLAG.AddToParser(parser)


def AddPauseScheduleFlags(parser):
  """Adds flags for pausing a schedule to the parser."""
  AddScheduleResourceArg(parser, 'to pause')


def AddResumeScheduleFlags(parser):
  """Adds flags for resuming a schedule to the parser."""
  AddScheduleResourceArg(parser, 'to resume')
  parser.add_argument(
      '--enable-catch-up',
      help=(
          'Enables backfilling missed runs when the schedule is resumed from'
          ' PAUSED state. If enabled, all missed runs will be scheduled and new'
          ' runs will be scheduled after the backfill is complete.'
      ),
      action='store_true',
      dest='enable_catch_up',
      default=False,
  )


def AddListSchedulesFlags(
    parser: parser_arguments.ArgumentInterceptor, for_workbench: bool = False
):
  """Construct groups and arguments specific to listing schedules.

  Args:
    parser: argparse parser for the command.
    for_workbench: whether the flags are for listing workbench schedules.
  """
  _AddRegionResourceArg(
      parser, 'for which to list all schedules', for_workbench
  )
  parser.display_info.AddUriFunc(schedules_util.GetScheduleUri)


def AddCreateOrUpdateScheduleFlags(
    parser: parser_arguments.ArgumentInterceptor,
    is_update: bool = False,
    for_workbench: bool = False,
):
  """Adds flags for creating or updating a schedule to the parser.

  Args:
    parser: argparse parser for the command.
    is_update: whether the flags are for updating a schedule.
    for_workbench: whether the flags are for a workbench schedule.
  """
  schedule_group = parser.add_group(
      help='Configuration of the schedule.',
      required=True,
  )
  if not is_update:
    _AddRegionResourceArg(parser, 'to create', for_workbench=for_workbench)
    # TODO: b/369896947 - Add support for updating execution once schedules API
    # supports partial updates to NotebookExecutionJobCreateRequest.
    AddCreateExecutionFlags(
        schedule_group, is_schedule=True, for_workbench=for_workbench
    )
  else:
    AddScheduleResourceArg(parser, 'to update')
  schedule_group.add_argument(
      '--display-name',
      help='The display name of the schedule.',
      required=True if not is_update else False,
  )
  schedule_group.add_argument(
      '--start-time',
      help=(
          'The timestamp after which the first run can be scheduled. Defaults'
          ' to the schedule creation time. Must be in the RFC 3339'
          ' (https://www.rfc-editor.org/rfc/rfc3339.txt) format. E.g.'
          ' "2026-01-01T00:00:00Z" or "2026-01-01T00:00:00-05:00"'
      ),
      type=arg_parsers.Datetime.ParseUtcTime,
  )
  schedule_group.add_argument(
      '--end-time',
      help=(
          'Timestamp after which no new runs can be scheduled. If specified,'
          ' the schedule will be completed when either end_time is reached or'
          ' when scheduled_run_count >= max_run_count. If neither end time nor'
          ' max_run_count is specified, new runs will keep getting scheduled'
          ' until this Schedule is paused or deleted. Must be in the RFC 3339'
          ' (https://www.rfc-editor.org/rfc/rfc3339.txt) format. E.g.'
          ' "2026-01-01T00:00:00Z" or "2026-01-01T00:00:00-05:00"'
      ),
      type=arg_parsers.Datetime.ParseUtcTime,
  )
  schedule_group.add_argument(
      '--max-runs',
      help='The max runs for the schedule.',
      type=int,
  )
  schedule_group.add_argument(
      '--cron-schedule',
      help=(
          'Cron schedule (https://en.wikipedia.org/wiki/Cron) to launch'
          ' scheduled runs. To explicitly set a timezone to the cron tab, apply'
          ' a prefix in the cron tab: "CRON_TZ=${IANA_TIME_ZONE}" or'
          ' "TZ=${IANA_TIME_ZONE}". The ${IANA_TIME_ZONE} may only be a valid'
          ' string from IANA time zone database. For example,'
          ' "CRON_TZ=America/New_York 1 * * * *", or "TZ=America/New_York 1 * *'
          ' * *".'
      ),
      required=True if not is_update else False,
  )
  schedule_group.add_argument(
      '--max-concurrent-runs',
      help=(
          'Maximum number of runs that can be started concurrently for this'
          ' Schedule. This is the limit for starting the scheduled requests and'
          ' not the execution of the notebook execution jobs created by the'
          ' requests.'
      ),
      type=int,
      default=1 if not is_update else None,
  )
  schedule_group.add_argument(
      '--enable-queueing',
      help=(
          'Enables new scheduled runs to be queued when max_concurrent_runs'
          ' limit is reached. If set to true, new runs will be'
          ' queued instead of skipped.'
      ),
      action='store_true',
      dest='enable_queueing',
      default=False if not is_update else None,
  )
