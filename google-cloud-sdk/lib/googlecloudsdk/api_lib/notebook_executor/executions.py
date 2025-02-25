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

import types

from googlecloudsdk.api_lib.colab_enterprise import runtime_templates as runtime_templates_util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io


Namespace = parser_extensions.Namespace


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


def ValidateAndGetWorkbenchExecution(args, messages, service):
  """Checks that the execution is a Workbench execution and returns it if so.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.
    service: The service to use for the API call.

  Returns:
    The execution if it is a Workbench execution.

  Raises:
    InvalidArgumentException: If the execution is not a Workbench execution.

  """
  execution = service.Get(
      CreateExecutionGetRequest(args, messages)
  )
  if not IsWorkbenchExecution(execution):
    raise exceptions.InvalidArgumentException(
        'EXECUTION',
        'Execution is not of Workbench type. To manage Colab Enterprise'
        ' executions use `gcloud colab` instead.',
    )
  return execution


def ValidateAndGetColabExecution(args, messages, service):
  """Checks that the execution is of Colab Enterprise type and returns it if so.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.
    service: The service to use for the API call.

  Returns:
    The execution if it is a Colab Enterprise execution.

  Raises:
    InvalidArgumentException: If the execution is a Workbench execution.
  """
  execution = service.Get(
      CreateExecutionGetRequest(args, messages)
  )
  if IsWorkbenchExecution(execution):
    raise exceptions.InvalidArgumentException(
        'EXECUTION',
        'Execution is not of Colab Enterprise type. To manage Workbench'
        ' executions use `gcloud beta workbench` instead.',
    )
  return execution


def IsWorkbenchExecution(execution):
  """Filter for Workbench executions.

  Args:
    execution: The execution item to check.

  Returns:
    True if the execution is a Workbench execution.
  """
  # TODO(b/384799644) - replace with API-side filtering when available.
  return execution.kernelName is not None


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
  """Get the runtime template resource name from the args.

  Args:
    args: Argparse object from Command.Run

  Returns:
    The notebook runtime template resource name.
  """
  return args.CONCEPTS.notebook_runtime_template.Parse().RelativeName()


def GetCustomEnvironmentSpec(args, messages):
  """Get the custom environment spec from the args for a Workbench execution.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.

  Returns:
    CustomEnvironmentSpec message for the execution.
  """
  custom_environment_spec = (
      messages.GoogleCloudAiplatformV1beta1NotebookExecutionJobCustomEnvironmentSpec
  )
  return custom_environment_spec(
      machineSpec=runtime_templates_util.GetMachineSpecFromArgs(args, messages),
      networkSpec=runtime_templates_util.GetNetworkSpecFromArgs(args, messages),
      persistentDiskSpec=runtime_templates_util.GetPersistentDiskSpecFromArgs(
          args, messages
      ),
  )


def GetExecutionUri(resource):
  """Get the URL for an execution resource."""
  execution = resources.REGISTRY.ParseRelativeName(
      relative_name=resource.name,
      collection='aiplatform.projects.locations.notebookExecutionJobs',
  )
  return execution.SelfLink()


def CreateNotebookExecutionJob(
    args, messages, workbench_execution, for_schedule=False):
  """Creates the NotebookExecutionJob message for the create request.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the AIPlatform API.
    workbench_execution: Whether this execution is for a Workbench notebook.
    for_schedule: Whether this execution is used to create a schedule.

  Returns:
    Instance of the NotebookExecutionJob message.
  """
  if workbench_execution:
    dataform_repository_source = None
    custom_environment_spec = GetCustomEnvironmentSpec(args, messages)
    workbench_runtime = (
        messages.GoogleCloudAiplatformV1beta1NotebookExecutionJobWorkbenchRuntime()
    )
    execution_user = None
    runtime_template_name = None
    encryption_spec = runtime_templates_util.CreateEncryptionSpecConfig(
        args, messages
    )
    kernel_name = args.kernel_name
  else:
    dataform_repository_source = GetDataformRepositorySourceFromArgs(
        args, messages
    )
    custom_environment_spec = None
    workbench_runtime = None
    execution_user = args.user_email
    runtime_template_name = GetRuntimeTemplateResourceName(args)
    encryption_spec = None
    kernel_name = None

  return messages.GoogleCloudAiplatformV1beta1NotebookExecutionJob(
      dataformRepositorySource=dataform_repository_source,
      directNotebookSource=None
      if for_schedule
      else GetDirectNotebookSourceFromArgs(args, messages),
      displayName=args.execution_display_name
      if for_schedule
      else args.display_name,
      executionTimeout=GetExecutionTimeoutFromArgs(args),
      executionUser=execution_user,
      gcsNotebookSource=GetGcsNotebookSourceFromArgs(args, messages),
      gcsOutputUri=args.gcs_output_uri,
      notebookRuntimeTemplateResourceName=runtime_template_name,
      customEnvironmentSpec=custom_environment_spec,
      serviceAccount=args.service_account,
      encryptionSpec=encryption_spec,
      workbenchRuntime=workbench_runtime,
      kernelName=kernel_name,
  )


def CreateExecutionCreateRequestForSchedule(
    args: Namespace,
    messages: types.ModuleType,
    for_workbench: bool = False,
):
  """Builds a NotebookExecutionJobsCreateRequest message for a CreateSchedule request.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.
    for_workbench: Indicates whether this is a Workbench execution.

  Returns:
    Instance of the NotebookExecutionJobsCreateRequest message.
  """
  parent = GetParentForExecutionOrSchedule(args)
  notebook_execution_job = CreateNotebookExecutionJob(
      args, messages, workbench_execution=for_workbench, for_schedule=True
  )
  return messages.GoogleCloudAiplatformV1beta1CreateNotebookExecutionJobRequest(
      notebookExecutionJob=notebook_execution_job,
      parent=parent,
  )


def CreateExecutionCreateRequest(args, messages, for_workbench=False):
  """Builds a NotebookExecutionJobsCreateRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.
    for_workbench: Indicates whether this is a Workbench execution.

  Returns:
    Instance of the NotebookExecutionJobsCreateRequest message.
  """
  parent = GetParentForExecutionOrSchedule(args)
  notebook_execution_job = CreateNotebookExecutionJob(
      args, messages, workbench_execution=for_workbench
  )
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
  return messages.AiplatformProjectsLocationsNotebookExecutionJobsListRequest(
      parent=GetParentForExecutionOrSchedule(args),
  )
