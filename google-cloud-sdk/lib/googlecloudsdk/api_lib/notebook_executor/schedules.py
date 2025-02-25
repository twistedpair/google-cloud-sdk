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
"""Notebook-executor schedules api helper."""

import types

from googlecloudsdk.api_lib.notebook_executor import executions as executions_util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import times
from googlecloudsdk.generated_clients.apis.aiplatform.v1beta1 import aiplatform_v1beta1_client


AiplatformV1beta1 = aiplatform_v1beta1_client.AiplatformV1beta1
Namespace = parser_extensions.Namespace


def GetScheduleResourceName(args):
  """Get the resource name for the schedule.

  Args:
    args: Argparse object from Command.Run

  Returns:
    The resource name in the form
    projects/{project}/locations/{location}/schedules/{schedule_id}.
  """
  return args.CONCEPTS.schedule.Parse().RelativeName()


def ParseScheduleOperation(operation_name):
  """Parse operation relative resource name to the operation reference object.

  Args:
    operation_name: The schedule operation resource name

  Returns:
    The operation reference object
  """
  if '/schedules/' in operation_name:
    try:
      return resources.REGISTRY.ParseRelativeName(
          operation_name,
          collection=(
              'aiplatform.projects.locations.schedules.operations'
          ),
      )
    except resources.WrongResourceCollectionException:
      pass
  return resources.REGISTRY.ParseRelativeName(
      operation_name, collection='aiplatform.projects.locations.operations'
  )


def GetScheduleUri(resource):
  """Get the URL for a schedule resource."""
  return resources.REGISTRY.ParseRelativeName(
      relative_name=resource.name,
      collection='aiplatform.projects.locations.schedules',
  ).SelfLink()


def GetStartTime(args):
  """Get the start time for the schedule."""
  return times.FormatDateTime(args.start_time) if args.start_time else None


def GetEndTime(args):
  """Get the end time for the schedule."""
  return times.FormatDateTime(args.end_time) if args.end_time else None


def CreateSchedule(
    args: Namespace,
    messages: types.ModuleType,
    for_update: bool = False,
    for_workbench: bool = False,
):
  """Builds a Schedule message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.
    for_update: Whether the schedule is to be used in an update request.
    for_workbench: Whether the schedule is for a Workbench execution.

  Returns:
    Instance of the Schedule message.
  """
  execution_create_request = None
  if not for_update:
    execution_create_request = (
        executions_util.CreateExecutionCreateRequestForSchedule(
            args, messages, for_workbench
        )
    )
  return messages.GoogleCloudAiplatformV1beta1Schedule(
      displayName=args.display_name,
      startTime=GetStartTime(args),
      endTime=GetEndTime(args),
      maxRunCount=args.max_runs,
      cron=args.cron_schedule,
      maxConcurrentRunCount=args.max_concurrent_runs,
      allowQueueing=args.enable_queueing,
      createNotebookExecutionJobRequest=execution_create_request,
  )


def FilterWorkbenchSchedule(schedule):
  """List filter for Workbench schedules.

  Args:
    schedule: The schedule item returned from List API to check.

  Returns:
    True if the schedule is for a Workbench notebook execution.
  """
  return executions_util.IsWorkbenchExecution(
      schedule.createNotebookExecutionJobRequest.notebookExecutionJob
  )


def ValidateAndGetColabSchedule(
    args: Namespace,
    messages: types.ModuleType,
    service: AiplatformV1beta1.ProjectsLocationsSchedulesService,
):
  """Checks if the schedule is for a Colab Enterprise notebook execution and returns the schedule if so.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.
    service: The service to use to make the request.

  Returns:
    The schedule if it is of Colab Enterprise type.

  Raises:
    InvalidArgumentException: If the schedule is not of notebook execution type
    or is of Workbench type.
  """
  schedule = service.Get(CreateScheduleGetRequest(args, messages))
  notebook_execution_job_request = schedule.createNotebookExecutionJobRequest
  if notebook_execution_job_request is None:
    raise exceptions.InvalidArgumentException(
        'SCHEDULE', 'Schedule is not of notebook execution type.'
    )
  if executions_util.IsWorkbenchExecution(
      notebook_execution_job_request.notebookExecutionJob
  ):
    raise exceptions.InvalidArgumentException(
        'SCHEDULE',
        'Schedule is not of Colab Enterprise type. To manage Workbench'
        ' schedules use `gcloud beta workbench` instead.',
    )
  return schedule


def ValidateAndGetWorkbenchSchedule(
    args: Namespace,
    messages: types.ModuleType,
    service: AiplatformV1beta1.ProjectsLocationsSchedulesService,
):
  """Checks if the schedule is for a Workbench notebook execution and returns the schedule if so.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.
    service: The service to use to make the request.

  Returns:
    The schedule if it is of Workbench type.

  Raises:
    InvalidArgumentException: If the schedule is not of notebook execution type.
  """
  schedule = service.Get(
      CreateScheduleGetRequest(args, messages)
  )
  notebook_execution_job_request = schedule.createNotebookExecutionJobRequest
  if notebook_execution_job_request is None:
    raise exceptions.InvalidArgumentException(
        'SCHEDULE', 'Schedule is not of notebook execution type.'
    )
  if notebook_execution_job_request.notebookExecutionJob.kernelName is None:
    raise exceptions.InvalidArgumentException(
        'SCHEDULE',
        'Schedule is not of Workbench type. To manage Colab Enterprise'
        ' schedules use `gcloud colab schedules` instead.',
    )
  return schedule


def CreateScheduleGetRequest(args, messages):
  """Builds a SchedulesGetRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the SchedulesGetRequest message.
  """

  return (
      messages.AiplatformProjectsLocationsSchedulesGetRequest(
          name=GetScheduleResourceName(args),
      )
  )


def CreateScheduleDeleteRequest(args, messages):
  """Builds a SchedulesDeleteRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the SchedulesDeleteRequest message.
  """

  return (
      messages.AiplatformProjectsLocationsSchedulesDeleteRequest(
          name=GetScheduleResourceName(args),
      )
  )


def CreateSchedulePauseRequest(args, messages):
  """Builds a SchedulesPauseRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the SchedulesPauseRequest message.
  """

  return (
      messages.AiplatformProjectsLocationsSchedulesPauseRequest(
          name=GetScheduleResourceName(args),
      )
  )


def CreateScheduleResumeRequest(args, messages):
  """Builds a SchedulesResumeRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the SchedulesResumeRequest message.
  """
  resume_schedule_request = (
      messages.GoogleCloudAiplatformV1beta1ResumeScheduleRequest(
          catchUp=args.enable_catch_up
      )
  )
  return (
      messages.AiplatformProjectsLocationsSchedulesResumeRequest(
          name=GetScheduleResourceName(args),
          googleCloudAiplatformV1beta1ResumeScheduleRequest=(
              resume_schedule_request
          ),
      )
  )


def CreateScheduleListRequest(args, messages):
  """Builds a SchedulesListRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the SchedulesListRequest message.
  """
  return messages.AiplatformProjectsLocationsSchedulesListRequest(
      parent=executions_util.GetParentForExecutionOrSchedule(args),
      filter='create_notebook_execution_job_request:*',
  )


def CreateScheduleCreateRequest(
    args: Namespace, messages: types.ModuleType, for_workbench: bool = False
):
  """Builds a SchedulesCreateRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.
    for_workbench: Whether the schedule is for a Workbench execution.

  Returns:
    Instance of the SchedulesCreateRequest message.
  """
  return messages.AiplatformProjectsLocationsSchedulesCreateRequest(
      parent=executions_util.GetParentForExecutionOrSchedule(args),
      googleCloudAiplatformV1beta1Schedule=CreateSchedule(
          args, messages, for_update=False, for_workbench=for_workbench
      ),
  )


def CreateScheduleUpdateMask(args):
  """Builds a field mask for the schedule update request.

  Args:
    args: Argparse object from Command.Run

  Returns:
    Field mask for the schedule update request.
  """
  mask_fields = []
  args_to_field_map = {
      'display_name': 'display_name',
      'start_time': 'start_time',
      'end_time': 'end_time',
      'max_runs': 'max_run_count',
      'cron_schedule': 'cron',
      'max_concurrent_runs': 'max_concurrent_run_count',
      'enable_queueing': 'allow_queueing',
  }
  for key, value in args_to_field_map.items():
    if args.IsSpecified(key):
      mask_fields.append(value)
  return ','.join(map(str, mask_fields))


def CreateSchedulePatchRequest(args, messages):
  """Builds a SchedulesPatchRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the SchedulesPatchRequest message.
  """
  return messages.AiplatformProjectsLocationsSchedulesPatchRequest(
      name=GetScheduleResourceName(args),
      googleCloudAiplatformV1beta1Schedule=CreateSchedule(
          args, messages, for_update=True
      ),
      updateMask=CreateScheduleUpdateMask(args),
  )
