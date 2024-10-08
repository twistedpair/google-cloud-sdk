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
"""Notebook-executor executions api helper."""

from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io


def ParseExecutionOperation(operation_name):
  """Parse operation relative resource name to the operation reference object.

  Args:
    operation_name: The execution operation resource name

  Returns:
    The operation reference object
  """
  if '/notebookExecutionJobs/' in operation_name:
    try:
      return resources.REGISTRY.ParseRelativeName(
          operation_name,
          collection=(
              'aiplatform.projects.locations.notebookExecutionJobs.operations'
          ),
      )
    except resources.WrongResourceCollectionException:
      pass
  return resources.REGISTRY.ParseRelativeName(
      operation_name, collection='aiplatform.projects.locations.operations'
  )


def GetParentForExecutionOrSchedule(args):
  """Get the parent Location resource name for the execution or schedule resource.

  Args:
    args: Argparse object from Command.Run

  Returns:
    The resource name in the form projects/{project}/locations/{location}.
  """
  return args.CONCEPTS.region.Parse().RelativeName()


def GetExecutionResourceName(args):
  """Get the resource name for the execution.

  Args:
    args: Argparse object from Command.Run

  Returns:
    The resource name in the form
    projects/{project}/locations/{location}/notebookExecutionJobs/{execution_job_id}.
  """
  return args.CONCEPTS.execution.Parse().RelativeName()


def GetDataformRepositorySourceFromArgs(args, messages):
  """Get the dataform repository source from the args.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.

  Returns:
    DataformRepositorySource message for the execution.
  """
  def GetDataformRepositoryResourceName(args):
    return args.CONCEPTS.dataform_repository_name.Parse().RelativeName()

  if args.IsSpecified('dataform_repository_name'):
    return messages.GoogleCloudAiplatformV1beta1NotebookExecutionJobDataformRepositorySource(
        dataformRepositoryResourceName=GetDataformRepositoryResourceName(args),
        commitSha=args.commit_sha,
    )
  return None


def GetGcsNotebookSourceFromArgs(args, messages):
  """Get the GCS notebook source from the args.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.

  Returns:
    GcsNotebookSource message for the execution.
  """
  gcs_notebook_source = (
      messages.GoogleCloudAiplatformV1beta1NotebookExecutionJobGcsNotebookSource
  )
  if args.IsSpecified('gcs_notebook_uri'):
    return gcs_notebook_source(
        uri=args.gcs_notebook_uri,
        generation=args.generation,
    )
  return None


def GetDirectNotebookSourceFromArgs(args, messages):
  """Create direct notebook source message from the args.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.

  Returns:
      DirectNotebookSource message for the execution.
  """
  notebook_source = messages.GoogleCloudAiplatformV1beta1NotebookExecutionJobDirectNotebookSource  # pylint: disable=line-too-long
  if args.IsSpecified('direct_content'):
    return notebook_source(
        # Gcloud client will handle base64 encoding of the byte string read
        # from disk.
        content=console_io.ReadFromFileOrStdin(args.direct_content,
                                               binary=True)
    )
  return None


def GetExecutionTimeoutFromArgs(args):
  """Get the execution timeout from the args.

  Args:
    args: Argparse object from Command.Run

  Returns:
    Serialized Duration message for the execution timeout.
  """
  # Need to convert Duration to string format since request uses http/json.
  return str(args.execution_timeout) + 's'


def GetRuntimeTemplateResourceName(args):
  """Get the notebook runtime template resource name from the args.

  Args:
    args: Argparse object from Command.Run

  Returns:
    The notebook runtime template resource name.
  """
  return args.CONCEPTS.notebook_runtime_template.Parse().RelativeName()


def GetExecutionUri(resource):
  """Get the URL for an execution resource."""
  execution = resources.REGISTRY.ParseRelativeName(
      relative_name=resource.name,
      collection='aiplatform.projects.locations.notebookExecutionJobs',
  )
  return execution.SelfLink()


def CreateNotebookExecutionJob(args, messages, for_schedule=False):
  """Creates the NotebookExecutionJob message for the create request.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the AIPlatform API.
    for_schedule: Whether this execution is used to create a schedule.

  Returns:
    Instance of the NotebookExecutionJob message.
  """
  return messages.GoogleCloudAiplatformV1beta1NotebookExecutionJob(
      dataformRepositorySource=GetDataformRepositorySourceFromArgs(
          args, messages
      ),
      directNotebookSource=None
      if for_schedule
      else GetDirectNotebookSourceFromArgs(args, messages),
      displayName=args.execution_display_name
      if for_schedule
      else args.display_name,
      executionTimeout=GetExecutionTimeoutFromArgs(args),
      executionUser=args.user_email,
      gcsNotebookSource=GetGcsNotebookSourceFromArgs(args, messages),
      gcsOutputUri=args.gcs_output_uri,
      notebookRuntimeTemplateResourceName=GetRuntimeTemplateResourceName(args),
      serviceAccount=args.service_account,
  )


def CreateExecutionCreateRequestForSchedule(args, messages):
  """Builds a NotebookExecutionJobsCreateRequest message for a CreateSchedule request.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the NotebookExecutionJobsCreateRequest message.
  """
  parent = GetParentForExecutionOrSchedule(args)
  notebook_execution_job = CreateNotebookExecutionJob(
      args, messages, for_schedule=True
  )
  return messages.GoogleCloudAiplatformV1beta1CreateNotebookExecutionJobRequest(
      notebookExecutionJob=notebook_execution_job,
      parent=parent,
  )


def CreateExecutionCreateRequest(args, messages):
  """Builds a NotebookExecutionJobsCreateRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the NotebookExecutionJobsCreateRequest message.
  """
  parent = GetParentForExecutionOrSchedule(args)
  notebook_execution_job = CreateNotebookExecutionJob(args, messages)
  return messages.AiplatformProjectsLocationsNotebookExecutionJobsCreateRequest(
      googleCloudAiplatformV1beta1NotebookExecutionJob=notebook_execution_job,
      notebookExecutionJobId=args.execution_job_id,
      parent=parent,
  )


def CreateExecutionDeleteRequest(args, messages):
  """Builds a NotebookExecutionJobsDeleteRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the NotebookExecutionJobsDeleteRequest message.
  """

  return (
      messages.AiplatformProjectsLocationsNotebookExecutionJobsDeleteRequest(
          name=GetExecutionResourceName(args),
      )
  )


def CreateExecutionGetRequest(args, messages):
  """Builds a NotebookExecutionsJobGetRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the NotebookExecutionsJobGetRequest message.
  """

  return (
      messages.AiplatformProjectsLocationsNotebookExecutionJobsGetRequest(
          name=GetExecutionResourceName(args),
      )
  )


def CreateExecutionListRequest(args, messages):
  """Builds a NotebookExecutionJobsListRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the NotebookExecutionJobsListRequest message.
  """
  return (
      messages.AiplatformProjectsLocationsNotebookExecutionJobsListRequest(
          parent=GetParentForExecutionOrSchedule(args),
      )
  )
