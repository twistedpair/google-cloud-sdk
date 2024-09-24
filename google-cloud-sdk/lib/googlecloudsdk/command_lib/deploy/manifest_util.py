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
"""Utilities for parsing the cloud deploy resource to yaml definition."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import re

from dateutil import parser
from googlecloudsdk.calliope import exceptions as c_exceptions
from googlecloudsdk.command_lib.deploy import automation_util
from googlecloudsdk.command_lib.deploy import deploy_util
from googlecloudsdk.command_lib.deploy import exceptions
from googlecloudsdk.command_lib.deploy import target_util
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

PIPELINE_UPDATE_MASK = '*,labels'
DELIVERY_PIPELINE_KIND_V1BETA1 = 'DeliveryPipeline'
TARGET_KIND_V1BETA1 = 'Target'
AUTOMATION_KIND = 'Automation'
CUSTOM_TARGET_TYPE_KIND = 'CustomTargetType'
DEPLOY_POLICY_KIND = 'DeployPolicy'
API_VERSION_V1BETA1 = 'deploy.cloud.google.com/v1beta1'
API_VERSION_V1 = 'deploy.cloud.google.com/v1'
USAGE_CHOICES = ['RENDER', 'DEPLOY']
ACTION_CHOICES = [
    'ADVANCE',
    'APPROVE',
    'CANCEL',
    'CREATE',
    'IGNORE_JOB',
    'RETRY_JOB',
    'ROLLBACK',
    'TERMINATE_JOBRUN',
]
DAY_OF_WEEK_CHOICES = [
    'MONDAY',
    'TUESDAY',
    'WEDNESDAY',
    'THURSDAY',
    'FRIDAY',
    'SATURDAY',
    'SUNDAY',
]
INVOKER_CHOICES = ['USER', 'DEPLOY_AUTOMATION']
# If changing these fields also change them in the UI code.
NAME_FIELD = 'name'
ADVANCE_ROLLOUT_FIELD = 'advanceRollout'
PROMOTE_RELEASE_FIELD = 'promoteRelease'
REPAIR_ROLLOUT_FIELD = 'repairRollout'
WAIT_FIELD = 'wait'
LABELS_FIELD = 'labels'
ANNOTATIONS_FIELD = 'annotations'
SELECTOR_FIELD = 'selector'
RULES_FIELD = 'rules'
TARGET_ID_FIELD = 'targetId'
ID_FIELD = 'id'
ADVANCE_ROLLOUT_RULE_FIELD = 'advanceRolloutRule'
PROMOTE_RELEASE_RULE_FIELD = 'promoteReleaseRule'
REPAIR_ROLLOUT_RULE_FIELD = 'repairRolloutRule'
ROLLOUT_RESTRICTIONS_FIELD = 'rolloutRestriction'
TIMED_PROMOTE_RELEASE_RULE_FIELD = 'timedPromoteReleaseRule'
DESTINATION_TARGET_ID_FIELD = 'destinationTargetId'
SOURCE_PHASES_FIELD = 'sourcePhases'
PHASES_FIELD = 'phases'
DESTINATION_PHASE_FIELD = 'destinationPhase'
DISABLE_ROLLBACK_IF_ROLLOUT_PENDING = 'disableRollbackIfRolloutPending'
TARGET_FIELD = 'target'
METADATA_FIELDS = [ANNOTATIONS_FIELD, LABELS_FIELD]
EXCLUDE_FIELDS = [
    'createTime',
    'etag',
    'uid',
    'updateTime',
    NAME_FIELD,
] + METADATA_FIELDS
JOBS_FIELD = 'jobs'
RETRY_FIELD = 'retry'
ATTEMPTS_FIELD = 'attempts'
ROLLBACK_FIELD = 'rollback'
REPAIR_PHASES_FIELD = 'repairPhases'
BACKOFF_MODE_FIELD = 'backoffMode'
BACKOFF_CHOICES = ['BACKOFF_MODE_LINEAR', 'BACKOFF_MODE_EXPONENTIAL']
BACKOFF_CHOICES_SHORT = ['LINEAR', 'EXPONENTIAL']
TARGETS_FIELD = 'targets'
SCHEDULE_FIELD = 'schedule'
TIME_ZONE_FIELD = 'timeZone'


def ParseDeployConfig(messages, manifests, region):
  """Parses the declarative definition of the resources into message.

  Args:
    messages: module containing the definitions of messages for Cloud Deploy.
    manifests: [str], the list of parsed resource yaml definitions.
    region: str, location ID.

  Returns:
    A dictionary of resource kind and message.
  Raises:
    exceptions.CloudDeployConfigError, if the declarative definition is
    incorrect.
  """
  resource_dict = {
      DELIVERY_PIPELINE_KIND_V1BETA1: [],
      TARGET_KIND_V1BETA1: [],
      AUTOMATION_KIND: [],
      CUSTOM_TARGET_TYPE_KIND: [],
      DEPLOY_POLICY_KIND: [],
  }
  project = properties.VALUES.core.project.GetOrFail()
  _ValidateConfig(manifests)
  for manifest in manifests:
    _ParseV1Config(
        messages, manifest['kind'], manifest, project, region, resource_dict
    )

  return resource_dict


def _ValidateConfig(manifests):
  """Validates the manifests.

  Args:
     manifests: [str], the list of parsed resource yaml definitions.

  Raises:
    exceptions.CloudDeployConfigError, if there are errors in the manifests
    (e.g. required field is missing, duplicate resource names).
  """
  resource_type_to_names = collections.defaultdict(list)
  for manifest in manifests:
    api_version = manifest.get('apiVersion')
    if not api_version:
      raise exceptions.CloudDeployConfigError(
          'missing required field .apiVersion'
      )
    resource_type = manifest.get('kind')
    if resource_type is None:
      raise exceptions.CloudDeployConfigError('missing required field .kind')
    api_version = manifest['apiVersion']
    if api_version not in {API_VERSION_V1BETA1, API_VERSION_V1}:
      raise exceptions.CloudDeployConfigError(
          'api version {} not supported'.format(api_version)
      )
    metadata = manifest.get('metadata')
    if not metadata or not metadata.get(NAME_FIELD):
      raise exceptions.CloudDeployConfigError(
          'missing required field .metadata.name in {}'.format(
              manifest.get('kind')
          )
      )
    # Populate a dictionary with resource_type: [names].
    # E.g. [TARGET: "target1, target2"]
    resource_type_to_names[resource_type].append(metadata.get(NAME_FIELD))
  _CheckDuplicateResourceNames(resource_type_to_names)


def _CheckDuplicateResourceNames(resource_type_to_names):
  """Checks if there are any duplicate resource names per resource type.

  Args:
     resource_type_to_names: dict[str,[str]], dict of resource type and names.

  Raises:
    exceptions.CloudDeployConfigError, if there are duplicate names for a given
    resource type.
  """
  errors = []
  for k, names in resource_type_to_names.items():
    dups = set()
    # For a given resource type, iterate through the resource names and check
    # for duplicates.
    for name in names:
      if names.count(name) > 1:
        dups.add(name)
    if dups:
      errors.append('{} has duplicate name(s): {}'.format(k, dups))
  if errors:
    raise exceptions.CloudDeployConfigError(errors)


def _ParseV1Config(messages, kind, manifest, project, region, resource_dict):
  """Parses the Cloud Deploy v1 and v1beta1 resource specifications into message.

       This specification version is KRM complied and should be used after
       private review.

  Args:
     messages: module containing the definitions of messages for Cloud Deploy.
     kind: str, name of the resource schema.
     manifest: dict[str,str], cloud deploy resource yaml definition.
     project: str, gcp project.
     region: str, ID of the location.
     resource_dict: dict[str,optional[message]], a dictionary of resource kind
       and message.

  Raises:
    exceptions.CloudDeployConfigError, if the declarative definition is
    incorrect.
  """
  metadata = manifest.get('metadata')
  if kind == DELIVERY_PIPELINE_KIND_V1BETA1:
    resource_type = deploy_util.ResourceType.DELIVERY_PIPELINE
    resource, resource_ref = _CreateDeliveryPipelineResource(
        messages, metadata[NAME_FIELD], project, region
    )
  elif kind == TARGET_KIND_V1BETA1:
    resource_type = deploy_util.ResourceType.TARGET
    resource, resource_ref = _CreateTargetResource(
        messages, metadata[NAME_FIELD], project, region
    )
  elif kind == AUTOMATION_KIND:
    resource_type = deploy_util.ResourceType.AUTOMATION
    resource, resource_ref = _CreateAutomationResource(
        messages, metadata[NAME_FIELD], project, region
    )
  elif kind == CUSTOM_TARGET_TYPE_KIND:
    resource_type = deploy_util.ResourceType.CUSTOM_TARGET_TYPE
    resource, resource_ref = _CreateCustomTargetTypeResource(
        messages, metadata[NAME_FIELD], project, region
    )
  elif kind == DEPLOY_POLICY_KIND:
    resource_type = deploy_util.ResourceType.DEPLOY_POLICY
    resource, resource_ref = _CreateDeployPolicyResource(
        messages, metadata[NAME_FIELD], project, region
    )
  else:
    raise exceptions.CloudDeployConfigError(
        'kind {} not supported'.format(kind)
    )

  if '/' in resource_ref.Name():
    raise exceptions.CloudDeployConfigError(
        'resource ID "{}" contains /.'.format(resource_ref.Name())
    )

  for field in manifest:
    if field not in ['apiVersion', 'kind', 'metadata', 'deliveryPipeline']:
      value = manifest.get(field)
      if field == 'executionConfigs':
        SetExecutionConfig(messages, resource, resource_ref, value)
        continue
      if field == 'deployParameters' and kind == TARGET_KIND_V1BETA1:
        SetDeployParametersForTarget(messages, resource, resource_ref, value)
        continue
      if field == 'customTarget' and kind == TARGET_KIND_V1BETA1:
        SetCustomTarget(resource, value, project, region)
        continue
      if field == 'associatedEntities' and kind == TARGET_KIND_V1BETA1:
        SetAssociatedEntities(messages, resource, resource_ref, value)
        continue
      if field == 'serialPipeline' and kind == DELIVERY_PIPELINE_KIND_V1BETA1:
        serial_pipeline = manifest.get('serialPipeline')
        _EnsureIsType(
            serial_pipeline,
            dict,
            'failed to parse pipeline {}, serialPipeline is defined incorrectly'
            .format(resource_ref.Name()),
        )
        stages = serial_pipeline.get('stages')
        _EnsureIsType(
            stages,
            list,
            'failed to parse pipeline {}, stages are defined incorrectly'
            .format(resource_ref.Name()),
        )
        for stage in stages:
          SetDeployParametersForPipelineStage(messages, resource_ref, stage)
      if field == SELECTOR_FIELD and kind == AUTOMATION_KIND:
        SetAutomationSelector(messages, resource, value)
        continue
      if field == RULES_FIELD and kind == AUTOMATION_KIND:
        SetAutomationRules(messages, resource, resource_ref, value)
        continue
      if field == RULES_FIELD and kind == DEPLOY_POLICY_KIND:
        rules = manifest.get('rules')
        _EnsureIsType(
            rules,
            list,
            'failed to parse deploy policy {}, rules are defined incorrectly'
            .format(resource_ref.Name()),
        )
        SetPolicyRules(messages, resource, rules)
        continue
      if field == 'selectors' and kind == DEPLOY_POLICY_KIND:
        selectors = manifest.get('selectors')
        _EnsureIsType(
            selectors,
            list,
            'failed to parse deploy policy {}, selectors are defined'
            ' incorrectly'.format(resource_ref.Name()),
        )
      setattr(resource, field, value)

  # Sets the properties in metadata.
  for field in metadata:
    if field not in [NAME_FIELD, ANNOTATIONS_FIELD, LABELS_FIELD]:
      setattr(resource, field, metadata.get(field))
  deploy_util.SetMetadata(
      messages,
      resource,
      resource_type,
      metadata.get(ANNOTATIONS_FIELD),
      metadata.get(LABELS_FIELD),
  )

  resource_dict[kind].append(resource)


def SetPolicyRules(messages, policy, rules):
  """Sets the rules field of cloud deploy policy message.

  Args:
    messages: module containing the definitions of messages for Cloud Deploy.
    policy:  googlecloudsdk.generated_clients.apis.clouddeploy.DeployPolicy
      message.
    rules: [googlecloudsdk.generated_clients.apis.clouddeploy.PolicyRule], list
      of PolicyRule messages.

  Raises:
    arg_parsers.ArgumentTypeError: if usage is not a valid enum.
  """
  # Go through each rule and parse the rolloutRestriction field.
  for pv_rule in rules:
    rollout_restriction_message = messages.RolloutRestriction()
    if pv_rule.get(ROLLOUT_RESTRICTIONS_FIELD):
      rollout_restriction = pv_rule.get(ROLLOUT_RESTRICTIONS_FIELD)
      _SetRolloutRestriction(
          messages, rollout_restriction_message, rollout_restriction, policy
      )
    else:
      policy.rules.append(pv_rule)


def _SetRolloutRestriction(
    messages, rollout_restriction_message, rollout_restriction, policy
):
  """Sets the rolloutRestriction field of cloud deploy policy message.

  Args:
    messages: module containing the definitions of messages for Cloud Deploy.
    rollout_restriction_message:
      googlecloudsdk.generated_clients.apis.clouddeploy.RolloutRestriction
      message.
    rollout_restriction: value of the rolloutRestriction field in the manifest.
    policy:  googlecloudsdk.generated_clients.apis.clouddeploy.DeployPolicy
      message.

  Raises:
    arg_parsers.ArgumentTypeError: if usage is not a valid enum.
  """
  for field in rollout_restriction:
    # The value of actions and invokers are enums, so they need special
    # treatment. timeWindow also needs special treatment because it has an
    # enum within it.
    if field != 'actions' and field != 'invokers' and field != 'timeWindows':
      # If the field doesn't need special treatment (e.g. id) set it
      # on the rolloutRestriction message.
      setattr(
          rollout_restriction_message, field, rollout_restriction.get(field)
      )

  actions = rollout_restriction.get('actions', [])
  for action in actions:
    rollout_restriction_message.actions.append(
        # converts a string literal in rolloutRestriction.actions to an Enum.
        arg_utils.ChoiceToEnum(
            action,
            messages.RolloutRestriction.ActionsValueListEntryValuesEnum,
            valid_choices=ACTION_CHOICES,
        )
    )

  invokers = rollout_restriction.get('invokers', [])
  for invoker in invokers:
    rollout_restriction_message.invokers.append(
        # converts a string literal in rolloutRestriction.invokers to an Enum.
        arg_utils.ChoiceToEnum(
            invoker,
            messages.RolloutRestriction.InvokersValueListEntryValuesEnum,
            valid_choices=INVOKER_CHOICES,
        )
    )
  # Parse and set the timeWindow field on the restrictRollout message.
  time_windows = rollout_restriction.get('timeWindows')
  time_windows_message = messages.TimeWindows()
  _SetTimeWindows(messages, time_windows_message, time_windows)
  rollout_restriction_message.timeWindows = time_windows_message
  # Set the rolloutRestriction field on the policy rule message.
  policy_rule_message = messages.PolicyRule()
  policy_rule_message.rolloutRestriction = rollout_restriction_message
  policy.rules.append(policy_rule_message)


def _SetTimeWindows(messages, time_windows_message, time_windows):
  """Sets the timeWindow field of cloud deploy resource message.

  Args:
    messages: module containing the definitions of messages for Cloud Deploy.
    time_windows_message:
      googlecloudsdk.generated_clients.apis.clouddeploy.TimeWindows message.
    time_windows: value of the timeWindows field.

  Raises:
    arg_parsers.ArgumentTypeError: if usage is not a valid enum.
  """
  setattr(time_windows_message, 'timeZone', time_windows.get('timeZone'))

  # Go through each oneTimeWindow and parse the fields.
  one_time_windows = time_windows.get('oneTimeWindows', [])
  for one_time_window in one_time_windows:
    _SetOneTimeWindow(messages, one_time_window, time_windows_message)

  # Go through each weeklyWindow and parse the fields.
  weekly_windows = time_windows.get('weeklyWindows', [])
  for weekly_window in weekly_windows:
    _SetWeeklyWindow(messages, weekly_window, time_windows_message)


def _SetOneTimeWindow(messages, one_time_window, time_windows_message):
  """Sets the oneTimeWindow field of a timeWindows message.

  Args:
    messages: module containing the definitions of messages for Cloud Deploy.
    one_time_window: value of the oneTimeWindow field.
    time_windows_message:
      googlecloudsdk.generated_clients.apis.clouddeploy.TimeWindows message.

  Raises:
    c_exceptions.InvalidArgumentException: if the start or end field is not a
    valid ISO 8601 string.
  """
  one_time_window_message = messages.OneTimeWindow()
  for field in one_time_window:
    if field not in ['start', 'end']:
      setattr(one_time_window_message, field, one_time_window.get(field))
  # Parse the ISO 8601 string from YAML into the date and time fields.
  if one_time_window.get('start'):
    _SetDateTimeFields(
        one_time_window, one_time_window_message, messages, 'start'
    )
  if one_time_window.get('end'):
    _SetDateTimeFields(
        one_time_window, one_time_window_message, messages, 'end'
    )
  time_windows_message.oneTimeWindows.append(one_time_window_message)


def _SetDateTimeFields(
    one_time_window, one_time_window_message, messages, field_name
):
  """Sets the start/end date time fields on the oneTimeWindow message.

  Args:
    one_time_window: value of the oneTimeWindow field.
    one_time_window_message:
      googlecloudsdk.generated_clients.apis.clouddeploy.OneTimeWindow message.
    messages: module containing the definitions of messages for Cloud Deploy.
    field_name: the field to set (start or end).

  Raises:
    c_exceptions.InvalidArgumentException: if the start or end field is not a
    valid ISO 8601 string.
  """
  try:
    date_time = parser.isoparse(one_time_window.get(field_name))
  except ValueError:
    raise c_exceptions.InvalidArgumentException(
        field_name,
        'invalid date string: "{}". Must be a valid date in ISO 8601 format'
        ' (e.g. {}: 2024-12-24 17:00)'.format(
            one_time_window.get(field_name), field_name
        ),
    )
  # Set the date field (e.g. startDate or endDate).
  date_obj = _ConvertDate(date_time, messages)
  date_field = '{}Date'.format(field_name)
  setattr(one_time_window_message, date_field, date_obj)
  # Set the time field (e.g. startTime or endTime)
  time_obj = _ConvertTime(date_time, messages)
  time_field = '{}Time'.format(field_name)
  setattr(one_time_window_message, time_field, time_obj)


def _ConvertDate(date_time_obj, messages):
  """Converts a dateTime object to a Date message."""
  return messages.Date(
      year=date_time_obj.year, month=date_time_obj.month, day=date_time_obj.day
  )


def _ConvertTime(date_time_obj, messages):
  """Converts a dateTime object to a TimeOfDay message."""
  return messages.TimeOfDay(
      hours=date_time_obj.hour,
      minutes=date_time_obj.minute,
      seconds=date_time_obj.second,
      nanos=date_time_obj.microsecond * 1000,
  )


def _SetWeeklyWindow(messages, weekly_window, time_windows_message):
  """Sets the weeklyWindow field of a timeWindows message.

  Args:
    messages: module containing the definitions of messages for Cloud Deploy.
    weekly_window: value of the weeklyWindow field.
    time_windows_message:
      googlecloudsdk.generated_clients.apis.clouddeploy.TimeWindows message.

  Raises:
    arg_parsers.ArgumentTypeError: if usage is not a valid enum.
  """
  weekly_window_message = messages.WeeklyWindow()
  for field in weekly_window:
    if field != 'daysOfWeek':
      setattr(weekly_window_message, field, weekly_window.get(field))
  days_of_week = weekly_window.get('daysOfWeek') or []
  for d in days_of_week:
    weekly_window_message.daysOfWeek.append(
        # converts a string literal in weeklyWindow.daysOfWeek to an Enum.
        arg_utils.ChoiceToEnum(
            d,
            messages.WeeklyWindow.DaysOfWeekValueListEntryValuesEnum,
            valid_choices=DAY_OF_WEEK_CHOICES,
        )
    )
  time_windows_message.weeklyWindows.append(weekly_window_message)


def _CreateTargetResource(messages, target_name_or_id, project, region):
  """Creates target resource with full target name and the resource reference."""
  resource = messages.Target()
  resource_ref = target_util.TargetReference(target_name_or_id, project, region)
  resource.name = resource_ref.RelativeName()

  return resource, resource_ref


def _CreateDeliveryPipelineResource(
    messages, delivery_pipeline_name, project, region
):
  """Creates delivery pipeline resource with full delivery pipeline name and the resource reference."""
  resource = messages.DeliveryPipeline()
  resource_ref = resources.REGISTRY.Parse(
      delivery_pipeline_name,
      collection='clouddeploy.projects.locations.deliveryPipelines',
      params={
          'projectsId': project,
          'locationsId': region,
          'deliveryPipelinesId': delivery_pipeline_name,
      },
  )
  resource.name = resource_ref.RelativeName()

  return resource, resource_ref


def _CreateAutomationResource(messages, name, project, region):
  resource = messages.Automation()
  resource_ref = automation_util.AutomationReference(name, project, region)
  resource.name = resource_ref.RelativeName()

  return resource, resource_ref


def _CreateCustomTargetTypeResource(messages, name, project, region):
  """Creates custom target type resource with full name and the resource reference."""
  resource = messages.CustomTargetType()
  resource_ref = resources.REGISTRY.Parse(
      name,
      collection='clouddeploy.projects.locations.customTargetTypes',
      params={
          'projectsId': project,
          'locationsId': region,
          'customTargetTypesId': name,
      },
  )
  resource.name = resource_ref.RelativeName()

  return resource, resource_ref


def _CreateDeployPolicyResource(messages, name, project, region):
  """Creates deploy policy resource with full name and the resource reference."""
  resource = messages.DeployPolicy()
  resource_ref = resources.REGISTRY.Parse(
      name,
      collection='clouddeploy.projects.locations.deployPolicies',
      params={
          'projectsId': project,
          'locationsId': region,
          'deployPoliciesId': name,
      },
  )
  resource.name = resource_ref.RelativeName()

  return resource, resource_ref


def ProtoToManifest(resource, resource_ref, kind):
  """Converts a resource message to a cloud deploy resource manifest.

  The manifest can be applied by 'deploy apply' command.

  Args:
    resource: message in googlecloudsdk.generated_clients.apis.clouddeploy.
    resource_ref: cloud deploy resource object.
    kind: kind of the cloud deploy resource

  Returns:
    A dictionary that represents the cloud deploy resource.
  """
  manifest = collections.OrderedDict(
      apiVersion=API_VERSION_V1, kind=kind, metadata={}
  )

  for k in METADATA_FIELDS:
    v = getattr(resource, k)
    # Skips the 'zero' values in the message.
    if v:
      manifest['metadata'][k] = v
  # Sets the name to resource ID instead of the full name.
  if kind == AUTOMATION_KIND:
    manifest['metadata'][NAME_FIELD] = (
        resource_ref.AsDict()['deliveryPipelinesId'] + '/' + resource_ref.Name()
    )
  else:
    manifest['metadata'][NAME_FIELD] = resource_ref.Name()

  for f in resource.all_fields():
    if f.name in EXCLUDE_FIELDS:
      continue
    v = getattr(resource, f.name)
    # Skips the 'zero' values in the message.
    if v:
      if f.name == SELECTOR_FIELD and kind == AUTOMATION_KIND:
        ExportAutomationSelector(manifest, v)
        continue
      if f.name == RULES_FIELD and kind == AUTOMATION_KIND:
        ExportAutomationRules(manifest, v)
        continue
      manifest[f.name] = v

  return manifest


def SetExecutionConfig(messages, target, target_ref, execution_configs):
  """Sets the executionConfigs field of cloud deploy resource message.

  Args:
    messages: module containing the definitions of messages for Cloud Deploy.
    target:  googlecloudsdk.generated_clients.apis.clouddeploy.Target message.
    target_ref: protorpc.messages.Message, target resource object.
    execution_configs:
      [googlecloudsdk.generated_clients.apis.clouddeploy.ExecutionConfig], list
      of ExecutionConfig messages.

  Raises:
    arg_parsers.ArgumentTypeError: if usage is not a valid enum.
  """
  _EnsureIsType(
      execution_configs,
      list,
      'failed to parse target {}, executionConfigs are defined incorrectly'
      .format(target_ref.Name()),
  )
  for config in execution_configs:
    execution_config_message = messages.ExecutionConfig()
    for field in config:
      # the value of usages field has enum, which needs special treatment.
      if field != 'usages':
        setattr(execution_config_message, field, config.get(field))
    usages = config.get('usages') or []
    for usage in usages:
      execution_config_message.usages.append(
          # converts a string literal in executionConfig.usages to an Enum.
          arg_utils.ChoiceToEnum(
              usage,
              messages.ExecutionConfig.UsagesValueListEntryValuesEnum,
              valid_choices=USAGE_CHOICES,
          )
      )

    target.executionConfigs.append(execution_config_message)


def SetDeployParametersForPipelineStage(messages, pipeline_ref, stage):
  """Sets the deployParameter field of cloud deploy delivery pipeline stage message.

  Args:
   messages: module containing the definitions of messages for Cloud Deploy.
   pipeline_ref: protorpc.messages.Message, delivery pipeline resource object.
   stage: dict[str,str], cloud deploy stage yaml definition.
  """

  deploy_parameters = stage.get('deployParameters')
  if deploy_parameters is None:
    return

  _EnsureIsType(
      deploy_parameters,
      list,
      'failed to parse stages of pipeline {}, deployParameters are defined'
      ' incorrectly'.format(pipeline_ref.Name()),
  )
  dps_message = getattr(messages, 'DeployParameters')
  dps_values = []

  for dp in deploy_parameters:
    dps_value = dps_message()
    values = dp.get('values')
    if values:
      values_message = dps_message.ValuesValue
      values_dict = values_message()
      _EnsureIsType(
          values,
          dict,
          'failed to parse stages of pipeline {}, deployParameter values are'
          'defined incorrectly'.format(pipeline_ref.Name()),
      )
      for key, value in values.items():
        values_dict.additionalProperties.append(
            values_message.AdditionalProperty(key=key, value=value)
        )
      dps_value.values = values_dict

    match_target_labels = dp.get('matchTargetLabels')
    if match_target_labels:
      mtls_message = dps_message.MatchTargetLabelsValue
      mtls_dict = mtls_message()

      for key, value in match_target_labels.items():
        mtls_dict.additionalProperties.append(
            mtls_message.AdditionalProperty(key=key, value=value)
        )
      dps_value.matchTargetLabels = mtls_dict

    dps_values.append(dps_value)

  stage['deployParameters'] = dps_values


def SetDeployParametersForTarget(
    messages, target, target_ref, deploy_parameters
):
  """Sets the deployParameters field of cloud deploy target message.

  Args:
   messages: module containing the definitions of messages for Cloud Deploy.
   target: googlecloudsdk.generated_clients.apis.clouddeploy.Target message.
   target_ref: protorpc.messages.Message, target resource object.
   deploy_parameters: dict[str,str], a dict of deploy parameters (key,value)
     pairs.
  """

  _EnsureIsType(
      deploy_parameters,
      dict,
      'failed to parse target {}, deployParameters are defined incorrectly'
      .format(target_ref.Name()),
  )

  dps_message = getattr(
      messages, deploy_util.ResourceType.TARGET.value
  ).DeployParametersValue
  dps_value = dps_message()
  for key, value in deploy_parameters.items():
    dps_value.additionalProperties.append(
        dps_message.AdditionalProperty(key=key, value=value)
    )
  target.deployParameters = dps_value


def SetAssociatedEntities(messages, target, target_ref, associated_entities):
  """Sets the associatedEntities field in the cloud deploy target message.

  Args:
    messages: module containing the definitions of messages for Cloud Deploy.
    target: googlecloudsdk.generated_clients.apis.clouddeploy.Target message.
    target_ref: protorpc.messages.Message, target resource object.
    associated_entities: dict[str, associated_entities], a dict of associated
      entities (key,value) pairs.
  """

  _EnsureIsType(
      associated_entities,
      dict,
      'failed to parse target {}, associatedEntities are defined incorrectly'
      .format(target_ref.Name()),
  )

  aes_message = getattr(
      messages, deploy_util.ResourceType.TARGET.value
  ).AssociatedEntitiesValue
  aes_value = aes_message()
  for key, value in associated_entities.items():
    aes_value.additionalProperties.append(
        aes_message.AdditionalProperty(key=key, value=value)
    )
  target.associatedEntities = aes_value


def SetCustomTarget(target, custom_target, project, region):
  """Sets the customTarget field of cloud deploy target message.

  This is handled specially because we allow providing either the ID or name for
  the custom target type referenced. When the ID is provided we need to
  construct the name.

  Args:
    target: googlecloudsdk.generated_clients.apis.clouddeploy.Target message.
    custom_target:
      googlecloudsdk.generated_clients.apis.clouddeploy.CustomTarget message.
    project: str, gcp project.
    region: str, ID of the location.
  """
  custom_target_type = custom_target.get('customTargetType')
  # If field contains '/' then we assume it's the name instead of the ID. No
  # adjustments required.
  if '/' in custom_target_type:
    target.customTarget = custom_target
    return

  custom_target_type_resource_ref = resources.REGISTRY.Parse(
      None,
      collection='clouddeploy.projects.locations.customTargetTypes',
      params={
          'projectsId': project,
          'locationsId': region,
          'customTargetTypesId': custom_target_type,
      },
  )
  custom_target['customTargetType'] = (
      custom_target_type_resource_ref.RelativeName()
  )
  target.customTarget = custom_target


def SetAutomationSelector(messages, automation, selectors):
  """Sets the selectors field of cloud deploy automation resource message.

  Args:
    messages: module containing the definitions of messages for Cloud Deploy.
    automation:  googlecloudsdk.generated_clients.apis.clouddeploy.Automation
      message.
    selectors:
      [googlecloudsdk.generated_clients.apis.clouddeploy.TargetAttributes], list
      of TargetAttributes messages.
  """

  automation.selector = messages.AutomationResourceSelector()
  # check this first because it's the recommended format for selector.
  if not isinstance(selectors, list):
    for target_attribute in selectors.get(TARGETS_FIELD):
      _AddTargetAttribute(messages, automation.selector, target_attribute)
  else:
    for selector in selectors:
      message = selector.get(TARGET_FIELD)
      _AddTargetAttribute(messages, automation.selector, message)


def SetAutomationRules(messages, automation, automation_ref, rules):
  """Sets the rules field of cloud deploy automation resource message.

  Args:
    messages: module containing the definitions of messages for Cloud Deploy.
    automation:  googlecloudsdk.generated_clients.apis.clouddeploy.Automation
      message.
    automation_ref: protorpc.messages.Message, automation resource object.
    rules: [automation rule message], list of messages that are usd to create
      googlecloudsdk.generated_clients.apis.clouddeploy.AutomationRule messages.
  """
  _EnsureIsType(
      rules,
      list,
      'failed to parse automation {}, rules are defined incorrectly'.format(
          automation_ref.Name()
      ),
  )

  for rule in rules:
    automation_rule = messages.AutomationRule()
    if rule.get(PROMOTE_RELEASE_RULE_FIELD) or rule.get(PROMOTE_RELEASE_FIELD):
      message = rule.get(PROMOTE_RELEASE_RULE_FIELD) or rule.get(
          PROMOTE_RELEASE_FIELD
      )
      promote_release = messages.PromoteReleaseRule(
          id=message.get(ID_FIELD) or message.get(NAME_FIELD),
          wait=_WaitMinToSec(message.get(WAIT_FIELD)),
          destinationTargetId=message.get(DESTINATION_TARGET_ID_FIELD),
          destinationPhase=message.get(DESTINATION_PHASE_FIELD),
      )
      automation_rule.promoteReleaseRule = promote_release
    if rule.get(ADVANCE_ROLLOUT_RULE_FIELD) or rule.get(ADVANCE_ROLLOUT_FIELD):
      message = rule.get(ADVANCE_ROLLOUT_RULE_FIELD) or rule.get(
          ADVANCE_ROLLOUT_FIELD
      )
      advance_rollout = messages.AdvanceRolloutRule(
          id=message.get(ID_FIELD) or message.get(NAME_FIELD),
          wait=_WaitMinToSec(message.get(WAIT_FIELD)),
          sourcePhases=message.get(SOURCE_PHASES_FIELD) or [],
      )
      automation_rule.advanceRolloutRule = advance_rollout
    if rule.get(REPAIR_ROLLOUT_RULE_FIELD) or rule.get(REPAIR_ROLLOUT_FIELD):
      message = rule.get(REPAIR_ROLLOUT_RULE_FIELD) or rule.get(
          REPAIR_ROLLOUT_FIELD
      )
      automation_rule.repairRolloutRule = messages.RepairRolloutRule(
          id=message.get(ID_FIELD) or message.get(NAME_FIELD),
          phases=message.get(PHASES_FIELD) or [],
          jobs=message.get(JOBS_FIELD) or [],
          repairPhases=_ParseRepairPhases(
              messages, message.get(REPAIR_PHASES_FIELD) or []
          ),
      )
    if rule.get(TIMED_PROMOTE_RELEASE_RULE_FIELD):
      message = rule.get(TIMED_PROMOTE_RELEASE_RULE_FIELD)
      automation_rule.timedPromoteReleaseRule = (
          messages.TimedPromoteReleaseRule(
              id=message.get(ID_FIELD) or message.get(NAME_FIELD),
              schedule=message.get(SCHEDULE_FIELD),
              timeZone=message.get(TIME_ZONE_FIELD),
              destinationTargetId=message.get(DESTINATION_TARGET_ID_FIELD),
              destinationPhase=message.get(DESTINATION_PHASE_FIELD),
          )
      )
    automation.rules.append(automation_rule)


def ExportAutomationSelector(manifest, resource_selector):
  """Exports the selector field of the Automation resource.

  Args:
    manifest: A dictionary that represents the cloud deploy Automation resource.
    resource_selector:
      googlecloudsdk.generated_clients.apis.clouddeploy.AutomationResourceSelector
      message.
  """
  manifest[SELECTOR_FIELD] = []
  for selector in getattr(resource_selector, 'targets'):
    manifest[SELECTOR_FIELD].append({TARGET_FIELD: selector})


def ExportAutomationRules(manifest, rules):
  """Exports the selector field of the Automation resource.

  Args:
    manifest: A dictionary that represents the cloud deploy Automation resource.
    rules: [googlecloudsdk.generated_clients.apis.clouddeploy.AutomationRule],
      list of AutomationRule message.
  """
  manifest[RULES_FIELD] = []
  for rule in rules:
    resource = {}
    if getattr(rule, PROMOTE_RELEASE_RULE_FIELD):
      message = getattr(rule, PROMOTE_RELEASE_RULE_FIELD)
      promote = {}
      resource[PROMOTE_RELEASE_FIELD] = promote
      promote[NAME_FIELD] = getattr(message, ID_FIELD)
      if getattr(message, DESTINATION_TARGET_ID_FIELD):
        promote[DESTINATION_TARGET_ID_FIELD] = getattr(
            message, DESTINATION_TARGET_ID_FIELD
        )
      if getattr(message, DESTINATION_PHASE_FIELD):
        promote[DESTINATION_PHASE_FIELD] = getattr(
            message, DESTINATION_PHASE_FIELD
        )
      if getattr(message, WAIT_FIELD):
        promote[WAIT_FIELD] = _WaitSecToMin(getattr(message, WAIT_FIELD))
    if getattr(rule, ADVANCE_ROLLOUT_RULE_FIELD):
      advance = {}
      resource[ADVANCE_ROLLOUT_FIELD] = advance
      message = getattr(rule, ADVANCE_ROLLOUT_RULE_FIELD)
      advance[NAME_FIELD] = getattr(message, ID_FIELD)
      if getattr(message, SOURCE_PHASES_FIELD):
        advance[SOURCE_PHASES_FIELD] = getattr(message, SOURCE_PHASES_FIELD)
      if getattr(message, WAIT_FIELD):
        advance[WAIT_FIELD] = _WaitSecToMin(getattr(message, WAIT_FIELD))
    if getattr(rule, REPAIR_ROLLOUT_RULE_FIELD):
      repair = {}
      resource[REPAIR_ROLLOUT_FIELD] = repair
      message = getattr(rule, REPAIR_ROLLOUT_RULE_FIELD)
      repair[NAME_FIELD] = getattr(message, ID_FIELD)
      if getattr(message, PHASES_FIELD):
        repair[PHASES_FIELD] = getattr(message, PHASES_FIELD)
      if getattr(message, JOBS_FIELD):
        repair[JOBS_FIELD] = getattr(message, JOBS_FIELD)
      if getattr(message, REPAIR_PHASES_FIELD):
        repair[REPAIR_PHASES_FIELD] = _ExportRepairPhases(
            getattr(message, REPAIR_PHASES_FIELD)
        )
    if getattr(rule, TIMED_PROMOTE_RELEASE_RULE_FIELD):
      message = getattr(rule, TIMED_PROMOTE_RELEASE_RULE_FIELD)
      timed_promote = {}
      resource[TIMED_PROMOTE_RELEASE_RULE_FIELD] = timed_promote
      timed_promote[NAME_FIELD] = getattr(message, ID_FIELD)
      if getattr(message, SCHEDULE_FIELD):
        timed_promote[SCHEDULE_FIELD] = getattr(message, SCHEDULE_FIELD)
      if getattr(message, TIME_ZONE_FIELD):
        timed_promote[TIME_ZONE_FIELD] = getattr(message, TIME_ZONE_FIELD)
      if getattr(message, DESTINATION_TARGET_ID_FIELD):
        timed_promote[DESTINATION_TARGET_ID_FIELD] = getattr(
            message, DESTINATION_TARGET_ID_FIELD
        )
      if getattr(message, DESTINATION_PHASE_FIELD):
        timed_promote[DESTINATION_PHASE_FIELD] = getattr(
            message, DESTINATION_PHASE_FIELD
        )
    manifest[RULES_FIELD].append(resource)


def _WaitMinToSec(wait):
  if not wait:
    return wait
  if not re.fullmatch(r'\d+m', wait):
    raise exceptions.AutomationWaitFormatError()
  mins = wait[:-1]
  # convert the minute to second
  seconds = int(mins) * 60
  return '%ss' % seconds


def _WaitSecToMin(wait):
  if not wait:
    return wait
  seconds = wait[:-1]
  # convert the minute to second
  mins = int(seconds) // 60
  return '%sm' % mins


def _EnsureIsType(value, t, msg):
  if not isinstance(value, t):
    raise exceptions.CloudDeployConfigError(msg)


def _ParseRepairPhases(messages, phases):
  """Parses RepairMode of the Automation resource."""
  modes_pb = []
  for p in phases:
    phase = messages.RepairPhaseConfig()
    if RETRY_FIELD in p:
      phase.retry = messages.Retry()
      retry = p.get(RETRY_FIELD)
      if retry:
        phase.retry.attempts = retry.get(ATTEMPTS_FIELD)
        phase.retry.wait = _WaitMinToSec(retry.get(WAIT_FIELD))
        phase.retry.backoffMode = _ParseBackoffMode(
            messages, retry.get(BACKOFF_MODE_FIELD)
        )
    if ROLLBACK_FIELD in p:
      phase.rollback = messages.Rollback()
      rollback = p.get(ROLLBACK_FIELD)
      if rollback:
        phase.rollback.destinationPhase = rollback.get(DESTINATION_PHASE_FIELD)
        phase.rollback.disableRollbackIfRolloutPending = rollback.get(
            DISABLE_ROLLBACK_IF_ROLLOUT_PENDING
        )
    modes_pb.append(phase)

  return modes_pb


def _ParseBackoffMode(messages, backoff):
  """Parses BackoffMode of the Automation resource."""
  if not backoff:
    return backoff
  if backoff in BACKOFF_CHOICES_SHORT:
    backoff = 'BACKOFF_MODE_' + backoff
  return arg_utils.ChoiceToEnum(
      backoff,
      messages.Retry.BackoffModeValueValuesEnum,
      valid_choices=BACKOFF_CHOICES,
  )


def _ExportRepairPhases(repair_phases):
  """Exports RepairMode of the Automation resource."""
  phases = []
  for p in repair_phases:
    phase = {}
    if getattr(p, RETRY_FIELD):
      retry = {}
      phase[RETRY_FIELD] = retry
      message = getattr(p, RETRY_FIELD)
      if getattr(message, WAIT_FIELD):
        retry[WAIT_FIELD] = _WaitSecToMin(getattr(message, WAIT_FIELD))
      if getattr(message, ATTEMPTS_FIELD):
        retry[ATTEMPTS_FIELD] = getattr(message, ATTEMPTS_FIELD)
      if getattr(message, BACKOFF_MODE_FIELD):
        retry[BACKOFF_MODE_FIELD] = getattr(
            message, BACKOFF_MODE_FIELD
        ).name.split('_')[2]
    if getattr(p, ROLLBACK_FIELD):
      message = getattr(p, ROLLBACK_FIELD)
      rollback = {}
      phase[ROLLBACK_FIELD] = rollback
      if getattr(message, DESTINATION_PHASE_FIELD):
        rollback[DESTINATION_PHASE_FIELD] = getattr(
            message, DESTINATION_PHASE_FIELD
        )
      if getattr(message, DISABLE_ROLLBACK_IF_ROLLOUT_PENDING):
        rollback[DISABLE_ROLLBACK_IF_ROLLOUT_PENDING] = getattr(
            message, DISABLE_ROLLBACK_IF_ROLLOUT_PENDING
        )
    phases.append(phase)

  return phases


def _AddTargetAttribute(messages, resource_selector, message):
  """Add a new TargetAttribute to the resource selector resource."""
  target_attribute = messages.TargetAttribute()
  for field in message:
    value = message.get(field)
    if field == ID_FIELD:
      setattr(target_attribute, field, value)
    if field == LABELS_FIELD:
      deploy_util.SetMetadata(
          messages,
          target_attribute,
          deploy_util.ResourceType.TARGET_ATTRIBUTE,
          None,
          value,
      )
    resource_selector.targets.append(target_attribute)
