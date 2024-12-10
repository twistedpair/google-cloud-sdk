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
"""colab-enterprise runtimes api helper."""

from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def GetParentForRuntime(args):
  """Get the parent Location resource name for the runtime.

  Args:
    args: Argparse object from Command.Run

  Returns:
    The resource name in the form projects/{project}/locations/{location}.
  """

  region = args.CONCEPTS.region.Parse()
  return region.RelativeName()


def ParseRuntimeOperation(operation_name):
  """Parse operation relative resource name to the operation reference object.

  Args:
    operation_name: The operation resource name

  Returns:
    The operation reference object
  """
  if '/notebookRuntimes/' in operation_name:
    try:
      return resources.REGISTRY.ParseRelativeName(
          operation_name,
          collection=(
              'aiplatform.projects.locations.notebookRuntimes.operations'
          ),
      )
    except resources.WrongResourceCollectionException:
      pass
  return resources.REGISTRY.ParseRelativeName(
      operation_name, collection='aiplatform.projects.locations.operations'
  )


def GetRuntimeUri(resource):
  """Transform a runtime resource into a URL."""
  runtime = resources.REGISTRY.ParseRelativeName(
      relative_name=resource.name,
      collection='aiplatform.projects.locations.notebookRuntimes',
  )
  return runtime.SelfLink()


def GetLabelsFromArgs(args, messages):
  """Constructs the labels from command line args.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the aiplatform API.

  Returns:
    Labels for the runtime.
  """
  if args.IsSpecified('labels'):
    labels_message = (
        messages.GoogleCloudAiplatformV1beta1NotebookRuntime.LabelsValue
    )
    return labels_message(
        additionalProperties=[
            labels_message.AdditionalProperty(key=key, value=value)
            for key, value in args.labels.items()
        ]
    )
  return None


def GetRuntimeUserFromArgsOrProperties(args):
  """Gets runtime user from command line args if provided; else default to caller.

  Args:
    args: Argparse object from Command.Run

  Returns:
    Runtime user of the runtime.
  """

  if args.IsSpecified('runtime_user'):
    return args.runtime_user
  else:
    return properties.VALUES.core.account.Get()


def GetRuntimeResourceName(args):
  """Get the resource name for the notebook runtime.

  Args:
    args: Argparse object from Command.Run

  Returns:
    The resource name in the form
    projects/{project}/locations/{location}/notebookRuntimes/{runtime_id}.
  """
  return args.CONCEPTS.runtime.Parse().RelativeName()


def CreateRuntimeMessage(args, messages):
  """Creates the NotebookRuntime message for the AssignNotebookRuntime request.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the NotebookRuntime message.
  """
  return messages.GoogleCloudAiplatformV1beta1NotebookRuntime(
      name=args.runtime_id,
      runtimeUser=GetRuntimeUserFromArgsOrProperties(args),
      displayName=args.display_name,
      description=args.description,
      labels=GetLabelsFromArgs(args, messages),
  )


def CreateRuntimeAssignRequestMessage(args, messages):
  """Builds a AssignNotebookRuntimeRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the AssignNotebookRuntimeRequest message.
  """

  parent = GetParentForRuntime(args)
  runtime = CreateRuntimeMessage(args, messages)

  return messages.AiplatformProjectsLocationsNotebookRuntimesAssignRequest(
      googleCloudAiplatformV1beta1AssignNotebookRuntimeRequest=messages.GoogleCloudAiplatformV1beta1AssignNotebookRuntimeRequest(
          notebookRuntime=runtime,
          notebookRuntimeId=args.runtime_id,
          notebookRuntimeTemplate=args.CONCEPTS.runtime_template.Parse().RelativeName(),
      ),
      parent=parent,
  )


def CreateRuntimeGetRequestMessage(args, messages):
  """Builds a GetNotebookRuntimeRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the GetNotebookRuntimeRequest message.
  """

  return messages.AiplatformProjectsLocationsNotebookRuntimesGetRequest(
      name=GetRuntimeResourceName(args),
  )


def CreateRuntimeListRequestMessage(args, messages):
  """Builds a ListNotebookRuntimeRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the ListNotebookRuntimeRequest message.
  """

  return messages.AiplatformProjectsLocationsNotebookRuntimesListRequest(
      parent=GetParentForRuntime(args),
  )


def CreateRuntimeDeleteRequestMessage(args, messages):
  """Builds a DeleteNotebookRuntimeRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the DeleteNotebookRuntimeRequest message.
  """

  return messages.AiplatformProjectsLocationsNotebookRuntimesDeleteRequest(
      name=GetRuntimeResourceName(args),
  )


def CreateRuntimeUpgradeRequestMessage(args, messages):
  """Builds a UpgradeNotebookRuntimeRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the UpgradeNotebookRuntimeRequest message.
  """

  return messages.AiplatformProjectsLocationsNotebookRuntimesUpgradeRequest(
      googleCloudAiplatformV1beta1UpgradeNotebookRuntimeRequest=messages.GoogleCloudAiplatformV1beta1UpgradeNotebookRuntimeRequest(),
      name=GetRuntimeResourceName(args),
  )


def CreateRuntimeStartRequestMessage(args, messages):
  """Builds a StartNotebookRuntimeRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the StartNotebookRuntimeRequest message.
  """

  return messages.AiplatformProjectsLocationsNotebookRuntimesStartRequest(
      googleCloudAiplatformV1beta1StartNotebookRuntimeRequest=messages.GoogleCloudAiplatformV1beta1StartNotebookRuntimeRequest(),
      name=GetRuntimeResourceName(args),
  )


def CreateRuntimeStopRequestMessage(args, messages):
  """Builds a StopNotebookRuntimeRequest message.

  Args:
    args: Argparse object from Command.Run
    messages: Module containing messages definition for the specified API.

  Returns:
    Instance of the StopNotebookRuntimeRequest message.
  """

  return messages.AiplatformProjectsLocationsNotebookRuntimesStopRequest(
      googleCloudAiplatformV1beta1StopNotebookRuntimeRequest=messages.GoogleCloudAiplatformV1beta1StopNotebookRuntimeRequest(),
      name=GetRuntimeResourceName(args),
  )
