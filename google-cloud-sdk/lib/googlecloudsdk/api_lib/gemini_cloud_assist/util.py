# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""API lib for Gemini Cloud Assist."""
import datetime
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.gemini import cloud_assist
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.core import resources


VERSION_MAP = {base.ReleaseTrack.ALPHA: 'v1', base.ReleaseTrack.BETA: 'v1'}


# The messages module can also be accessed from client.MESSAGES_MODULE
def GetMessagesModule(release_track=base.ReleaseTrack.ALPHA):
  """Returns the messages module for the given release track.

  Args:
    release_track: The release track to use.

  Returns:
    The messages module for the given release track.
  """
  return apis.GetMessagesModule(
      'geminicloudassist', VERSION_MAP.get(release_track)
  )


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA):
  """Returns the client instance for the given release track.

  Args:
    release_track: The release track to use.

  Returns:
    The client instance for the given release track.
  """
  return apis.GetClientInstance(
      'geminicloudassist', VERSION_MAP.get(release_track)
  )


def GetInvestigation(investigations_resource_name):
  """Returns the investigation for the given investigation resource.

  Args:
    investigations_resource_name: The name of the investigation resource.

  Returns:
    The investigation for the given investigation resource.
  """
  client = GetClientInstance()
  messages = GetMessagesModule()
  return client.projects_locations_investigations.Get(
      messages.GeminicloudassistProjectsLocationsInvestigationsGetRequest(
          name=investigations_resource_name
      )
  )


def CreateInvestigation(
    investigation_resource,
    title,
    issue,
    start_time,
    end_time,
    relevant_resources,
):
  """Creates the investigation for the given investigation resource.

  Args:
    investigation_resource: The investigation resource to create.
    title: The title of the investigation.
    issue: The issue of the investigation.
    start_time: The start time of the investigation.
    end_time: The end time of the investigation.
    relevant_resources: The resources of the investigation.

  Returns:
    The created investigation.
  """
  client = GetClientInstance()
  messages = GetMessagesModule()
  investigation_id = investigation_resource.RelativeName().split('/')[-1]
  investigation = messages.Investigation(observations={})
  if investigation_id != '-':
    investigation.name = investigation_resource.RelativeName()
  else:
    investigation_id = None

  investigation.observations.additionalProperties.append(
      messages.Investigation.ObservationsValue.AdditionalProperty(
          key='user.project',
          value=messages.Observation(
              id='user.project',
              text=investigation_resource.Parent()
              .Parent()
              .RelativeName()
              .split('/')[-1],
              observationType=messages.Observation.ObservationTypeValueValuesEnum.OBSERVATION_TYPE_STRUCTURED_INPUT,
              observerType=messages.Observation.ObserverTypeValueValuesEnum.OBSERVER_TYPE_USER,
          ),
      )
  )

  if title:
    investigation.title = title

  if issue or start_time or end_time or relevant_resources:
    observation = messages.Observation(
        id='user.input.log',
        title='User Provided Issue',
        observationType=messages.Observation.ObservationTypeValueValuesEnum.OBSERVATION_TYPE_CLOUD_LOG,
        observerType=messages.Observation.ObserverTypeValueValuesEnum.OBSERVER_TYPE_USER,
    )
    if issue:
      observation.text = issue

    if start_time and end_time:
      observation.timeIntervals.append(
          messages.Interval(
              startTime=start_time.isoformat(), endTime=end_time.isoformat()
          )
      )
    elif start_time:
      observation.timeIntervals.append(
          messages.Interval(startTime=start_time.isoformat())
      )
    elif end_time:
      observation.timeIntervals.append(
          messages.Interval(endTime=end_time.isoformat())
      )
    else:
      half_an_hour_ago = datetime.datetime.now(
          datetime.timezone.utc
      ) - datetime.timedelta(minutes=30)
      observation.timeIntervals.append(
          messages.Interval(startTime=half_an_hour_ago.isoformat())
      )

    if relevant_resources:
      observation.relevantResources = relevant_resources

    investigation.observations.additionalProperties.append(
        messages.Investigation.ObservationsValue.AdditionalProperty(
            key=observation.id,
            value=observation,
        )
    )

  return client.projects_locations_investigations.Create(
      messages.GeminicloudassistProjectsLocationsInvestigationsCreateRequest(
          parent=investigation_resource.Parent().RelativeName(),
          investigationId=investigation_id,
          investigation=investigation,
      )
  )


def CalculateTimeInterval(start_time, end_time, observation):
  """Calculates the time interval for the given start and end times.

  Args:
    start_time: The start time of the investigation.
    end_time: The end time of the investigation.
    observation: The observation to get the existing time interval from.

  Returns:
    The calculated time interval.
  """
  start_time_str, end_time_str = None, None
  if observation and len(observation.timeIntervals) >= 1:
    start_time_str = observation.timeIntervals[0].startTime
    end_time_str = observation.timeIntervals[0].endTime

  if start_time:
    start_time_str = (
        # Treat min start time as clear
        start_time.isoformat()
        if start_time != datetime.datetime.min
        else None
    )
  if end_time:
    end_time_str = (
        # Treat max end time as clear
        end_time.isoformat()
        if end_time != datetime.datetime.max
        else None
    )

  return GetMessagesModule().Interval(
      startTime=start_time_str, endTime=end_time_str
  )


def UpdateInvestigation(
    investigation_resource,
    title,
    issue,
    start_time,
    end_time,
    relevant_resources,
):
  """Updates the investigation for the given investigation resource.

  Args:
    investigation_resource: The investigation resource to create.
    title: The title of the investigation. Pass an empty string to clear.
    issue: The issue of the investigation.
    start_time: The start time of the investigation. Pass datetime.datetime.min
      to clear.
    end_time: The end time of the investigation. Pass datetime.datetime.max to
      clear.
    relevant_resources: The resources of the investigation. Pass an empty array
      to clear.

  Returns:
    The updated investigation.
  """
  # We need to do a read-modify-patch because we can't directly patch
  # observation time intervals, only replace them outright.
  old_investigation = GetInvestigation(investigation_resource.RelativeName())

  client = GetClientInstance()
  messages = GetMessagesModule()
  investigation = messages.Investigation(observations={})
  mask = []

  investigation.name = investigation_resource.RelativeName()

  investigation.observations.additionalProperties.append(
      messages.Investigation.ObservationsValue.AdditionalProperty(
          key='user.project',
          value=messages.Observation(
              id='user.project',
              text=investigation_resource.Parent()
              .Parent()
              .RelativeName()
              .split('/')[-1],
              observationType=messages.Observation.ObservationTypeValueValuesEnum.OBSERVATION_TYPE_STRUCTURED_INPUT,
              observerType=messages.Observation.ObserverTypeValueValuesEnum.OBSERVER_TYPE_USER,
          ),
      )
  )
  mask.append('observations.`user.project`')

  if title is not None:
    mask.append('title')
    investigation.title = title

  if (
      issue is not None
      or start_time
      or end_time
      or relevant_resources is not None
  ):
    observation = messages.Observation(
        id='user.input.log',
        title='User Provided Issue',
        observationType=messages.Observation.ObservationTypeValueValuesEnum.OBSERVATION_TYPE_CLOUD_LOG,
        observerType=messages.Observation.ObserverTypeValueValuesEnum.OBSERVER_TYPE_USER,
    )
    mask.append('observations.`user.input.log`.id')
    mask.append('observations.`user.input.log`.title')
    mask.append('observations.`user.input.log`.observationType')
    mask.append('observations.`user.input.log`.observerType')

    if issue is not None:
      mask.append('observations.`user.input.log`.text')
      observation.text = issue

    if start_time or end_time:
      mask.append('observations.`user.input.log`.timeIntervals')

      # We need to read the old observation to get the existing time interval.
      old_observation = None
      for obs in old_investigation.observations.additionalProperties:
        if obs.key == 'user.input.log':
          old_observation = obs.value
          break

      observation.timeIntervals.append(
          CalculateTimeInterval(
              start_time,
              end_time,
              old_observation,
          )
      )

    if relevant_resources is not None:
      mask.append('observations.`user.input.log`.relevantResources')
      observation.relevantResources = relevant_resources

    investigation.observations.additionalProperties.append(
        messages.Investigation.ObservationsValue.AdditionalProperty(
            key=observation.id,
            value=observation,
        )
    )

  return client.projects_locations_investigations.Patch(
      messages.GeminicloudassistProjectsLocationsInvestigationsPatchRequest(
          name=investigation_resource.RelativeName(),
          updateMask=','.join(mask),
          investigation=investigation,
      )
  )


def RunInvestigationRevisionBlocking(revision_name):
  """Runs the investigation revision for the given revision name.

  Args:
    revision_name: The name of the investigation revision.

  Returns:
    The response of running the investigation revision.
  """
  client = GetClientInstance()
  messages = GetMessagesModule()
  operation = client.projects_locations_investigations_revisions.Run(
      messages.GeminicloudassistProjectsLocationsInvestigationsRevisionsRunRequest(
          name=revision_name
      )
  )
  poller = waiter.CloudOperationPollerNoResources(
      client.projects_locations_operations,
  )
  operation_ref = resources.REGISTRY.Parse(
      operation.name,
      collection='geminicloudassist.projects.locations.operations',
  )
  waiter.WaitFor(poller, operation_ref, message='Running investigation')
  return cloud_assist.ReformatInvestigation(
      GetInvestigation(revision_name.split('/revisions/')[0])
  )


def GetInvestigationIamPolicy(investigations_resource_name):
  """Returns the IAM policy for the given investigation resource.

  Args:
    investigations_resource_name: The name of the investigation resource.

  Returns:
    The IAM policy for the given investigation resource.
  """
  client = GetClientInstance()
  messages = GetMessagesModule()
  return client.projects_locations_investigations.GetIamPolicy(
      messages.GeminicloudassistProjectsLocationsInvestigationsGetIamPolicyRequest(
          resource=investigations_resource_name
      )
  )


def AddInvestigationIamPolicyBinding(
    investigations_resource_name,
    member='allUsers',
    role='roles/geminicloudassist.investigationViewer',
):
  """Adds an IAM policy binding to the given investigation resource.

  Args:
    investigations_resource_name: The name of the investigation resource.
    member: The member to add to the binding.
    role: The role to add to the binding.

  Returns:
    The updated IAM policy for the given investigation resource.
  """
  client = GetClientInstance()
  messages = GetMessagesModule()
  policy = GetInvestigationIamPolicy(investigations_resource_name)
  iam_util.AddBindingToIamPolicy(messages.Binding, policy, member, role)
  return client.projects_locations_investigations.SetIamPolicy(
      messages.GeminicloudassistProjectsLocationsInvestigationsSetIamPolicyRequest(
          resource=investigations_resource_name,
          setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy),
      )
  )


def RemoveInvestigationIamPolicyBinding(
    investigations_resource_name,
    member='allUsers',
    role='roles/geminicloudassist.investigationViewer',
):
  """Removes an IAM policy binding from the given investigation resource.

  Args:
    investigations_resource_name: The name of the investigation resource.
    member: The member to remove from the binding.
    role: The role to remove from the binding.

  Returns:
    The updated IAM policy for the given investigation resource.
  """
  client = GetClientInstance()
  messages = GetMessagesModule()
  policy = GetInvestigationIamPolicy(investigations_resource_name)
  iam_util.RemoveBindingFromIamPolicy(policy, member, role)
  return client.projects_locations_investigations.SetIamPolicy(
      messages.GeminicloudassistProjectsLocationsInvestigationsSetIamPolicyRequest(
          resource=investigations_resource_name,
          setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy),
      )
  )


def SetInvestigationIamPolicy(investigations_resource_name, policy_file):
  """Sets the IAM policy for the given investigation resource.

  Args:
    investigations_resource_name: The name of the investigation resource.
    policy_file: The path to the policy file.

  Returns:
    The updated IAM policy for the given investigation resource.
  """
  client = GetClientInstance()
  messages = GetMessagesModule()
  policy, update_mask = iam_util.ParseYamlOrJsonPolicyFile(
      policy_file, messages.Policy
  )
  result = client.projects_locations_investigations.SetIamPolicy(
      messages.GeminicloudassistProjectsLocationsInvestigationsSetIamPolicyRequest(
          resource=investigations_resource_name,
          setIamPolicyRequest=messages.SetIamPolicyRequest(
              policy=policy, updateMask=update_mask
          ),
      )
  )
  iam_util.LogSetIamPolicy(investigations_resource_name, 'investigation')
  return result
