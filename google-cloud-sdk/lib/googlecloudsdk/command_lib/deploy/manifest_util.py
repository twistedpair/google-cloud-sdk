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


import collections
import dataclasses
import datetime
import enum
import re
from typing import Any, Callable, Optional

from apitools.base.py import encoding
from dateutil import parser
from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.command_lib.deploy import automation_util
from googlecloudsdk.command_lib.deploy import custom_target_type_util
from googlecloudsdk.command_lib.deploy import delivery_pipeline_util
from googlecloudsdk.command_lib.deploy import deploy_policy_util
from googlecloudsdk.command_lib.deploy import exceptions
from googlecloudsdk.command_lib.deploy import target_util
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.resource import resource_property
import jsonschema

PIPELINE_UPDATE_MASK = '*,labels'
API_VERSION_V1BETA1 = 'deploy.cloud.google.com/v1beta1'
API_VERSION_V1 = 'deploy.cloud.google.com/v1'
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
ID_FIELD = 'id'
ADVANCE_ROLLOUT_RULE_FIELD = 'advanceRolloutRule'
PROMOTE_RELEASE_RULE_FIELD = 'promoteReleaseRule'
REPAIR_ROLLOUT_RULE_FIELD = 'repairRolloutRule'
TIMED_PROMOTE_RELEASE_RULE_FIELD = 'timedPromoteReleaseRule'
DESTINATION_TARGET_ID_FIELD = 'destinationTargetId'
SOURCE_PHASES_FIELD = 'sourcePhases'
PHASES_FIELD = 'phases'
DESTINATION_PHASE_FIELD = 'destinationPhase'
DISABLE_ROLLBACK_IF_ROLLOUT_PENDING = 'disableRollbackIfRolloutPending'
TARGET_FIELD = 'target'
METADATA_FIELDS = [ANNOTATIONS_FIELD, LABELS_FIELD, NAME_FIELD]
EXCLUDE_FIELDS = [
    'createTime',
    'customTargetTypeId',
    'etag',
    'targetId',
    'uid',
    'updateTime',
] + METADATA_FIELDS
JOBS_FIELD = 'jobs'
RETRY_FIELD = 'retry'
ATTEMPTS_FIELD = 'attempts'
ROLLBACK_FIELD = 'rollback'
REPAIR_PHASES_FIELD = 'repairPhases'
BACKOFF_MODE_FIELD = 'backoffMode'
SCHEDULE_FIELD = 'schedule'
TIME_ZONE_FIELD = 'timeZone'
LABELS_FIELD = 'labels'


@enum.unique
class ResourceKind(enum.Enum):
  TARGET = 'Target'
  DELIVERY_PIPELINE = 'DeliveryPipeline'
  AUTOMATION = 'Automation'
  CUSTOM_TARGET_TYPE = 'CustomTargetType'
  DEPLOY_POLICY = 'DeployPolicy'

  def __str__(self):
    return self.value


@dataclasses.dataclass
class _TransformContext:
  kind: ResourceKind
  name: str
  project: str
  region: str
  manifest: dict[str, Any]
  field: str


def ParseDeployConfig(
    messages: list[Any], manifests: list[dict[str, Any]], region: str
) -> dict[ResourceKind, list[Any]]:
  """Parses the declarative definition of the resources into message.

  Args:
    messages: module containing the definitions of messages for Cloud Deploy.
    manifests: [str], the list of parsed resource yaml definitions.
    region: str, location ID.

  Returns:
    A dictionary of ResourceKind and list of messages.
  Raises:
    exceptions.CloudDeployConfigError, if the declarative definition is
    incorrect.
  """
  project = properties.VALUES.core.project.GetOrFail()

  manifests_with_metadata = collections.defaultdict(list)
  for i, manifest in enumerate(manifests):
    kind = _GetKind(manifest, i)
    name = _GetName(manifest, i)
    manifests_with_metadata[(kind, name)].append(manifest)

  _CheckDuplicateResourceNames(manifests_with_metadata)

  resources_by_kind = collections.defaultdict(list)
  for (kind, name), manifests in manifests_with_metadata.items():
    resources_by_kind[kind].append(
        # Thanks to _CheckDuplicateResourceNames(), we know manifests has
        # exactly one element.
        _ParseManifest(kind, name, manifests[0], project, region, messages)
    )
  return resources_by_kind


def _GetKind(manifest: dict[str, Any], doc_index: int) -> ResourceKind:
  """Parses the kind of a resource."""
  api_version = manifest.get('apiVersion')
  if not api_version:
    raise exceptions.CloudDeployConfigError.for_unnamed_manifest(
        doc_index, 'missing required field "apiVersion"'
    )
  if api_version not in {API_VERSION_V1BETA1, API_VERSION_V1}:
    raise exceptions.CloudDeployConfigError.for_unnamed_manifest(
        doc_index, f'api version "{api_version}" not supported'
    )
  kind = manifest.get('kind')
  if kind is None:
    raise exceptions.CloudDeployConfigError.for_unnamed_manifest(
        doc_index, 'missing required field "kind"'
    )
  # In Python 3.12+ we can just use `if kind not in ResourceKind`
  if kind not in [str(r) for r in ResourceKind]:
    raise exceptions.CloudDeployConfigError.for_unnamed_manifest(
        doc_index, f'kind "{kind}" not supported'
    )
  return ResourceKind(kind)


def _GetName(manifest: dict[str, Any], doc_index: int) -> str:
  """Parses the name of a resource."""
  metadata = manifest.get('metadata')
  if not metadata or not metadata.get(NAME_FIELD):
    raise exceptions.CloudDeployConfigError.for_unnamed_manifest(
        doc_index, 'missing required field "metadata.name"'
    )
  return metadata['name']


def _CheckDuplicateResourceNames(
    manifests_by_name_and_kind: dict[tuple[ResourceKind, str], list[Any]],
) -> None:
  """Checks if there are any duplicate resource names per resource type."""
  dups = collections.defaultdict(list)
  for (kind, name), manifests in manifests_by_name_and_kind.items():
    if len(manifests) > 1:
      dups[kind].append(name)
  errors = []
  for kind, names in dups.items():
    errors.append(f'{kind} has duplicate name(s): {names}')
  if errors:
    raise exceptions.CloudDeployConfigError(errors)


def _RemoveApiVersionAndKind(
    value: dict[str, Any], transform_context: _TransformContext
) -> None:
  """Removes the apiVersion and kind fields from the manifest."""
  del value
  del transform_context.manifest['apiVersion']
  del transform_context.manifest['kind']


def _MetadataYamlToProto(
    metadata: dict[str, Any], transform_context: _TransformContext
) -> None:
  """Moves the fields in metadata to the top level of the manifest."""
  manifest = transform_context.manifest
  manifest[ANNOTATIONS_FIELD] = metadata.get(ANNOTATIONS_FIELD)
  manifest[LABELS_FIELD] = metadata.get(LABELS_FIELD)
  # I think allowing description in metadata was an accident, not intentional...
  # It's supposed to be a top level field. But even some of our own tests do
  # this, so I think we have to assume customers might have too.
  if 'description' in metadata:
    manifest['description'] = metadata['description']
  name = metadata.get(NAME_FIELD)
  resource_ref = _ref_creators[transform_context.kind](
      name, transform_context.project, transform_context.region
  )
  # Name() does _not_ return the resource name. It returns the part of the name
  # after the resource type. For example, for targets, it returns everything
  # after `/targets/`. So this tells us if the user provided an invalid resource
  # ID, which would lead to a confusing error when we try to call the API.
  if '/' in resource_ref.Name():
    raise exceptions.CloudDeployConfigError.for_resource_field(
        transform_context.kind,
        name,
        'metadata.name',
        f'invalid resource ID "{resource_ref.Name()}"',
    )
  manifest[NAME_FIELD] = resource_ref.RelativeName()
  del manifest['metadata']


def _ConvertLabelsToSnakeCase(
    labels: dict[str, str], transform_context: _TransformContext
) -> dict[str, str]:
  """Convert labels from camelCase to snake_case."""
  del transform_context
  # See go/unified-cloud-labels-proposal.
  return {resource_property.ConvertToSnakeCase(k): v for k, v in labels.items()}


def _UpdateOldAutomationSelector(
    selector: dict[str, Any], transform_context: _TransformContext
) -> dict[str, Any]:
  """Converts an old automation selector to the new format."""
  targets = []
  for target in selector:
    targets.append(target[TARGET_FIELD])
  transform_context.manifest['selector'] = {'targets': targets}


def _RenameOldAutomationRules(
    rule: dict[str, Any], transform_context: _TransformContext
) -> dict[str, Any]:
  """Renames the old automation rule fields to the new format."""
  del transform_context
  if PROMOTE_RELEASE_FIELD in rule:
    rule[PROMOTE_RELEASE_RULE_FIELD] = rule[PROMOTE_RELEASE_FIELD]
    del rule[PROMOTE_RELEASE_FIELD]
  if ADVANCE_ROLLOUT_FIELD in rule:
    rule[ADVANCE_ROLLOUT_RULE_FIELD] = rule[ADVANCE_ROLLOUT_FIELD]
    del rule[ADVANCE_ROLLOUT_FIELD]
  if REPAIR_ROLLOUT_FIELD in rule:
    rule[REPAIR_ROLLOUT_RULE_FIELD] = rule[REPAIR_ROLLOUT_FIELD]
    del rule[REPAIR_ROLLOUT_FIELD]
  return rule


def _ConvertAutomationRuleNameFieldToId(
    rule: dict[str, Any], transform_context: _TransformContext
) -> dict[str, Any]:
  """Move the name field to the id field."""
  if rule is not None and NAME_FIELD in rule:
    if ID_FIELD in rule:
      raise exceptions.CloudDeployConfigError.for_resource(
          transform_context.kind,
          transform_context.name,
          'automation rule has both name and id fields',
      )
    rule[ID_FIELD] = rule[NAME_FIELD]
    del rule[NAME_FIELD]
  return rule


def _AddEmptyRepairAutomationRetryMessage(
    repair_phase: dict[str, Any], transform_context: _TransformContext
) -> dict[str, Any]:
  """Add an empty retry field if it's defined in the manifest but set to None."""
  del transform_context
  if RETRY_FIELD in repair_phase and repair_phase[RETRY_FIELD] is None:
    repair_phase[RETRY_FIELD] = {}
  return repair_phase


def _ConvertRepairAutomationBackoffModeEnumValuesToProtoFormat(
    value: str, transform_context
) -> str:
  """Converts the backoffMode values to the proto enum names."""
  del transform_context

  if not value.startswith('BACKOFF_MODE_'):
    return 'BACKOFF_MODE_' + value


def _ConvertAutomationWaitMinToSec(
    wait: str, transform_context: _TransformContext
) -> str:
  """Converts the wait time from (for example) "5m" to "300s"."""
  del transform_context
  if not re.fullmatch(r'\d+m', wait):
    raise exceptions.AutomationWaitFormatError()
  mins = wait[:-1]
  # convert the minute to second
  seconds = int(mins) * 60
  return '%ss' % seconds


def _ConvertPolicyOneTimeWindowToProtoFormat(
    value: dict[str, Any], transform_context: _TransformContext
) -> dict[str, Any]:
  """Converts the one time window to proto format."""
  proto_format = {}
  if value.get('start'):
    _SetDateTimeFields(value['start'], 'start', proto_format, transform_context)
  if value.get('end'):
    _SetDateTimeFields(value['end'], 'end', proto_format, transform_context)
  # Any other (unknown) fields will cause errors in the proto conversion so we
  # don't need to check for them here.
  return proto_format


def _SetDateTimeFields(
    date_str: str,
    field_name: str,
    proto_format: dict[str, str],
    transform_context: _TransformContext,
) -> None:
  """Convert the date string to proto format and set those fields in proto_format."""
  try:
    date_time = parser.isoparse(date_str)
  except ValueError:
    raise exceptions.CloudDeployConfigError.for_resource_field(
        transform_context.kind,
        transform_context.name,
        field_name,
        'invalid date string: "{date_str}". Must be a valid date in ISO 8601'
        ' format (e.g. {field_name}: "2024-12-24 17:00)',
    )
  except TypeError:
    raise exceptions.CloudDeployConfigError.for_resource_field(
        transform_context.kind,
        transform_context.name,
        field_name,
        'invalid date string: {date_str}. Make sure to put quotes around the'
        ' date string (e.g. {field_name}: "2024-09-27 18:30:31.123") so that it'
        ' is interpreted as a string and not a yaml timestamp.',
    )
  if date_time.tzinfo is not None:
    raise exceptions.CloudDeployConfigError.for_resource_field(
        transform_context.kind,
        transform_context.name,
        field_name,
        'invalid date string: {date_str}. Do not include a timezone or timezone'
        ' offset in the date string. Specify the timezone in the timeZone'
        ' field.',
    )
  date_obj = {
      'year': date_time.year,
      'month': date_time.month,
      'day': date_time.day,
  }
  time_obj = {
      'hours': date_time.hour,
      'minutes': date_time.minute,
      'seconds': date_time.second,
      'nanos': date_time.microsecond * 1000,
  }
  date_field = f'{field_name}Date'
  proto_format[date_field] = date_obj
  time_field = f'{field_name}Time'
  proto_format[time_field] = time_obj


def _ConvertPolicyWeeklyWindowTimes(
    value: str, transform_context: _TransformContext
) -> dict[str, str]:
  """Convert the weekly window times to proto format."""
  # First, check if the hour is 24. If so replace with 00, because
  # fromisoformat() doesn't support 24.
  hour_24 = False
  if value.startswith('24:'):
    hour_24 = True
    value = value.replace('24', '00', 1)
  try:
    time_obj = datetime.time.fromisoformat(value)
  except ValueError:
    raise exceptions.CloudDeployConfigError.for_resource_field(
        transform_context.kind,
        transform_context.name,
        transform_context.field,
        f'invalid time string: "{value}"',
    )
  hour_value = time_obj.hour
  if hour_24:
    hour_value = 24
  return {
      'hours': hour_value,
      'minutes': time_obj.minute,
      'seconds': time_obj.second,
      'nanos': time_obj.microsecond * 1000,
  }


def _ReplaceCustomTargetType(
    value: str, transform_context: _TransformContext
) -> str:
  """Converts a custom target type ID or name to a resource name.

  This is handled specially because we allow providing either the ID or name for
  the custom target type referenced. When the ID is provided we need to
  construct the name.

  Args:
    value: the current value of the customTargetType field.
    transform_context: _TransformContext, data about the current parsing
      context.

  Returns:
    The custom target type resource name.
  """
  # If field contains '/' then we assume it's the name instead of the ID. No
  # adjustments required.
  if '/' in value:
    return value

  return custom_target_type_util.CustomTargetTypeReference(
      value, transform_context.project, transform_context.region
  ).RelativeName()


@dataclasses.dataclass
class TransformConfig:
  """Represents a field that needs transformation during parsing.

  Attributes:
    kinds: The ResourceKinds that this transformation applies to.
    fields: A dot separated list of fields that require special handling. These
      are relative to the top level of the manifest and can contain `[]` to
      represent an array field.
    replace: A function that is called when the field is encountered. The return
      value will be used in place of the original value.
    move: A function that is called when the field is encountered. This is used
      for fields that should be moved to a different location in the manifest.
      The function should modify the transform_context.manifest in place.
    schema: An optional JSON schema that is used to validate the field.
  """

  kinds: set[ResourceKind]
  # A dot separated list of fields that require special handling.
  fields: dict[str]
  # One of `replace` or `move` must be set. The first argument is the value of
  # the field specified in `fields`.
  # If `replace` is set, the function should return the new value and the
  # parsing code will handle the substitution.
  # If `move` is set, the function should modify the transform_context.manifest
  # in place and the parsing code will skip the field.
  replace: Optional[Callable[[Any, _TransformContext], Any]] = None
  move: Optional[Callable[[Any, _TransformContext], None]] = None
  schema: Optional[dict[str, Any]] = None


_PARSE_TRANSFORMS = [
    TransformConfig(
        kinds=set(ResourceKind),
        fields=['apiVersion'],
        move=_RemoveApiVersionAndKind,
    ),
    TransformConfig(
        kinds=set(ResourceKind),
        fields=['metadata'],
        move=_MetadataYamlToProto,
        schema={
            'type': 'object',
            'required': ['name'],
            'properties': {
                'name': {'type': 'string'},
                'description': {'type': 'string'},
                'annotations': {
                    'type': 'object',
                    'additionalProperties': {'type': 'string'},
                },
                'labels': {
                    'type': 'object',
                    'additionalProperties': {'type': 'string'},
                },
            },
            'additionalProperties': False,
        },
    ),
    TransformConfig(
        kinds=set(ResourceKind),
        fields=['labels'],
        replace=_ConvertLabelsToSnakeCase,
        schema={'type': 'object', 'additionalProperties': {'type': 'string'}},
    ),
    TransformConfig(
        kinds=[ResourceKind.AUTOMATION],
        fields=['selector[]'],
        move=_UpdateOldAutomationSelector,
        schema={
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {'target': {'type': 'object'}},
                'required': ['target'],
                'additionalProperties': True,
            },
        },
    ),
    TransformConfig(
        kinds=[ResourceKind.AUTOMATION],
        fields=['rules[]'],
        replace=_RenameOldAutomationRules,
    ),
    TransformConfig(
        kinds=[ResourceKind.AUTOMATION],
        fields=[
            'rules[].repairRolloutRule',
            'rules[].advanceRolloutRule',
            'rules[].promoteReleaseRule',
            'rules[].timedPromoteReleaseRule',
        ],
        replace=_ConvertAutomationRuleNameFieldToId,
    ),
    TransformConfig(
        kinds=[ResourceKind.AUTOMATION],
        fields=['rules[].repairRolloutRule.repairPhases[]'],
        replace=_AddEmptyRepairAutomationRetryMessage,
    ),
    TransformConfig(
        kinds=[ResourceKind.AUTOMATION],
        fields=['rules[].repairRolloutRule.repairPhases[].retry.backoffMode'],
        replace=_ConvertRepairAutomationBackoffModeEnumValuesToProtoFormat,
        schema={'type': 'string'},
    ),
    TransformConfig(
        kinds=[ResourceKind.AUTOMATION],
        fields=[
            'rules[].repairRolloutRule.repairPhases[].retry.wait',
            'rules[].advanceRolloutRule.wait',
            'rules[].promoteReleaseRule.wait',
        ],
        replace=_ConvertAutomationWaitMinToSec,
        schema={'type': 'string'},
    ),
    TransformConfig(
        kinds=[ResourceKind.DEPLOY_POLICY],
        fields=['rules[].rolloutRestriction.timeWindows.oneTimeWindows[]'],
        replace=_ConvertPolicyOneTimeWindowToProtoFormat,
    ),
    TransformConfig(
        kinds=[ResourceKind.DEPLOY_POLICY],
        fields=[
            'rules[].rolloutRestriction.timeWindows.weeklyWindows[].startTime',
            'rules[].rolloutRestriction.timeWindows.weeklyWindows[].endTime',
        ],
        replace=_ConvertPolicyWeeklyWindowTimes,
        schema={'type': 'string'},
    ),
    TransformConfig(
        kinds=[ResourceKind.TARGET],
        fields=['customTarget.customTargetType'],
        replace=_ReplaceCustomTargetType,
        schema={'type': 'string'},
    ),
]


_ref_creators = {
    ResourceKind.AUTOMATION: automation_util.AutomationReference,
    ResourceKind.CUSTOM_TARGET_TYPE: (
        custom_target_type_util.CustomTargetTypeReference
    ),
    ResourceKind.DELIVERY_PIPELINE: (
        delivery_pipeline_util.DeliveryPipelineReference
    ),
    ResourceKind.DEPLOY_POLICY: deploy_policy_util.DeployPolicyReference,
    ResourceKind.TARGET: target_util.TargetReference,
}

_message_types = {
    ResourceKind.AUTOMATION: lambda messages: messages.Automation,
    ResourceKind.CUSTOM_TARGET_TYPE: lambda messages: messages.CustomTargetType,
    ResourceKind.DELIVERY_PIPELINE: lambda messages: messages.DeliveryPipeline,
    ResourceKind.DEPLOY_POLICY: lambda messages: messages.DeployPolicy,
    ResourceKind.TARGET: lambda messages: messages.Target,
}


def _ParseManifest(
    kind: ResourceKind,
    name: str,
    manifest: dict[str, Any],
    project: str,
    region: str,
    messages: list[Any],
) -> Any:
  """Parses a v1beta1/v1 config manifest into a message using proto transforms.

  The parser calls a series of transforms on the manifest dictionary to convert
  it into a form expected by the proto message definitions. This transformed
  dictionary is then passed to `messages_util.DictToMessageWithErrorCheck` to
  convert it into the actual proto message.

  Args:
    kind: str, The kind of the resource (e.g., 'Target').
    name: str, The name of the resource.
    manifest: dict[str, Any], The cloud deploy resource YAML definition as a
      dict.
    project: str, The GCP project ID.
    region: str, The ID of the location.
    messages: The module containing the definitions of messages for Cloud
      Deploy.

  Returns:
    The parsed resource as a message object (e.g., messages.Target), or an
    empty dictionary if the kind is not TARGET_KIND_V1BETA1.

  Raises:
    exceptions.CloudDeployConfigError: If there are errors in the manifest
      because of invalid data.
  """
  ApplyTransforms(manifest, _PARSE_TRANSFORMS, kind, name, project, region)
  try:
    resource = messages_util.DictToMessageWithErrorCheck(
        manifest, _message_types[kind](messages)
    )
  except messages_util.DecodeError as e:
    raise exceptions.CloudDeployConfigError.for_resource(
        kind, name, str(e)
    ) from e
  return resource


def AddApiVersionAndKind(
    value: Any, transform_context: _TransformContext
) -> None:
  """Adds the API version and kind to the manifest."""
  del value
  transform_context.manifest['apiVersion'] = API_VERSION_V1
  transform_context.manifest['kind'] = transform_context.kind.value


def _RemoveField(value: Any, transform_context: _TransformContext) -> None:
  """Removes the field from the manifest."""
  del value
  del transform_context.manifest[transform_context.field]


def _MetadataProtoToYaml(
    value: Any, transform_context: _TransformContext
) -> None:
  """Converts the metadata proto to YAML."""
  del value
  transform_context.manifest['metadata'] = {}
  for k in METADATA_FIELDS:
    if k in transform_context.manifest:
      transform_context.manifest['metadata'][k] = (
          transform_context.manifest.get(k)
      )


def _ConvertAutomationWaitSecToMin(
    wait: str, transform_context: _TransformContext
) -> str:
  del transform_context
  if not wait:
    return wait
  seconds = wait[:-1]
  # convert the minute to second
  mins = int(seconds) // 60
  return '%sm' % mins


def ConvertPolicyOneTimeWindowToYamlFormat(
    one_time_window: dict[str, Any], transform_context: _TransformContext
) -> dict[str, Any]:
  """Exports the oneTimeWindows field of the Deploy Policy resource."""
  one_time = {}
  start_date_time = _DateTimeIsoString(
      one_time_window['startDate'],
      one_time_window['startTime'],
      transform_context,
  )
  end_date_time = _DateTimeIsoString(
      one_time_window['endDate'], one_time_window['endTime'], transform_context
  )
  one_time['start'] = start_date_time
  one_time['end'] = end_date_time
  return one_time


def _DateTimeIsoString(
    date_obj: dict[str, str],
    time_obj: dict[str, str],
    transform_context: _TransformContext,
) -> str:
  """Converts a date and time to a string."""
  date_str = _FormatDate(date_obj)
  time_str = ConvertTimeProtoToString(time_obj, transform_context)
  return f'{date_str} {time_str}'


def _FormatDate(date: dict[str, str]) -> str:
  """Converts a date object to a string."""
  return f"{date['year']:04}-{date['month']:02}-{date['day']:02}"


def ConvertTimeProtoToString(
    time_obj: dict[str, str], transform_context: _TransformContext
) -> str:
  """Converts a time object to a string."""
  del transform_context
  hours = time_obj.get('hours') or 0
  minutes = time_obj.get('minutes') or 0
  time_str = f'{hours:02}:{minutes:02}'
  if time_obj.get('seconds') or time_obj.get('nanos'):
    seconds = time_obj.get('seconds') or 0
    time_str += f':{seconds:02}'
  if time_obj.get('nanos'):
    millis = time_obj.get('nanos') / 1000000
    time_str += f'.{millis:03.0f}'
  return time_str


_EXPORT_TRANSFORMS = [
    TransformConfig(
        kinds=set(ResourceKind),
        # Using the always-present `name` field to make sure this transform is
        # always applied.
        fields=['name'],
        move=AddApiVersionAndKind,
    ),
    TransformConfig(
        kinds=set(ResourceKind) - set([ResourceKind.AUTOMATION]),
        fields=['name'],
        # Strip everything before the last `/` character
        replace=lambda value, transform_context: re.sub(r'.*/', '', value),
    ),
    TransformConfig(
        kinds=[ResourceKind.AUTOMATION],
        fields=['name'],
        replace=lambda value, transform_context: re.sub(
            # Keep only the deliveryPipeline ID and the automation ID:
            #   projects/.../locations/.../deliveryPipelines/foo/automations/bar
            # becomes:
            #   foo/bar
            r'.*/deliveryPipelines/([^/]+)/automations/',
            '\\1/',
            value,
        ),
    ),
    TransformConfig(
        kinds=set(ResourceKind),
        fields=['name'],
        move=_MetadataProtoToYaml,
    ),
    TransformConfig(
        kinds=set(ResourceKind),
        fields=EXCLUDE_FIELDS,
        move=_RemoveField,
    ),
    TransformConfig(
        kinds=[ResourceKind.AUTOMATION],
        fields=[
            'rules[].advanceRolloutRule.wait',
            'rules[].promoteReleaseRule.wait',
            'rules[].repairRolloutRule.repairPhases[].retry.wait',
        ],
        replace=_ConvertAutomationWaitSecToMin,
    ),
    TransformConfig(
        kinds=[ResourceKind.AUTOMATION],
        fields=[
            'rules[].repairRolloutRule.repairPhases[].retry.backoffMode',
        ],
        replace=lambda value, transform_context: value.removeprefix(
            'BACKOFF_MODE_'
        ),
    ),
    TransformConfig(
        kinds=[ResourceKind.AUTOMATION],
        fields=[
            'rules[].repairRolloutRule.repairPhases[].retry.attempts',
        ],
        # apitools converts this to a string, annoyingly. Presumably because
        # it's an int64 field and Python doesn't support ints that big? But the
        # server caps it at 10 anyway.
        replace=lambda value, transform_context: int(value),
    ),
    TransformConfig(
        kinds=[ResourceKind.DEPLOY_POLICY],
        fields=['rules[].rolloutRestriction.timeWindows.oneTimeWindows[]'],
        replace=ConvertPolicyOneTimeWindowToYamlFormat,
    ),
    TransformConfig(
        kinds=[ResourceKind.DEPLOY_POLICY],
        fields=[
            'rules[].rolloutRestriction.timeWindows.weeklyWindows[].startTime',
            'rules[].rolloutRestriction.timeWindows.weeklyWindows[].endTime',
        ],
        replace=ConvertTimeProtoToString,
    ),
]


def ProtoToManifest(
    resource: Any, resource_ref: resources.Resource, kind: ResourceKind
) -> dict[str, Any]:
  """Converts a resource message to a cloud deploy resource manifest.

  The manifest can be applied by 'deploy apply' command.

  Args:
    resource: message in googlecloudsdk.generated_clients.apis.clouddeploy.
    resource_ref: cloud deploy resource object.
    kind: kind of the cloud deploy resource

  Returns:
    A dictionary that represents the cloud deploy resource.
  """
  manifest = encoding.MessageToDict(resource)
  ApplyTransforms(
      manifest,
      _EXPORT_TRANSFORMS,
      kind,
      resource_ref.Name(),
      resource_ref.projectsId,
      resource_ref.locationsId,
  )
  return manifest


def ApplyTransforms(
    manifest: dict[str, Any],
    transforms: list[TransformConfig],
    kind: str,
    name: str,
    project: str,
    region: str,
) -> None:
  """Applies a set of transformations to the manifest."""
  for transform in transforms:
    if kind not in transform.kinds:
      continue
    for field_name in transform.fields:
      value = _GetValue(field_name, manifest)
      if value:
        transform_context = _TransformContext(
            kind,
            name,
            project,
            region,
            manifest,
            _GetFinalFieldName(field_name),
        )
        if transform.replace:
          new_value = _TransformNestedListData(
              value,
              lambda data, current_field=transform, current_transform_context=transform_context: current_field.replace(
                  data, current_transform_context
              ),
              transform_context,
              transform.schema,
          )
          _SetValue(manifest, field_name, new_value)
        else:
          if transform.schema:
            try:
              jsonschema.validate(schema=transform.schema, instance=value)
            except jsonschema.exceptions.ValidationError as e:
              raise exceptions.CloudDeployConfigError.for_resource_field(
                  kind, name, field_name, e.message
              ) from e
          transform.move(value, transform_context)


def _GetValue(path: str, manifest: dict[str, Any]) -> Any:
  """Gets the value at a dot-separated path in a dictionary.

  If the path contains [], it returns a list of values at the path. If the path
  contains multiple [], it will return nested lists. None values will appear
  where there are missing values.

  Args:
    path: str, The dot-separated path to the value.
    manifest: dict, The dictionary to search.

  Returns:
    The value at the path, or None if it doesn't exist.
  """
  if '[]' in path:
    pre, post = path.split('[]', 1)
    post = post.lstrip('.')
    current_list = _GetValue(pre, manifest)
    if not isinstance(current_list, list):
      return None  # Path before [] did not lead to a list

    results = []
    if not post:  # If there's no path after [], return the list items
      return current_list

    for item in current_list:
      result = _GetValue(post, item)
      results.append(result)
    return results

  keys = path.split('.')
  current = manifest
  for key in keys:
    if isinstance(current, dict) and key in current:
      current = current[key]
    elif isinstance(current, list):
      # Handle cases where a list is encountered but not specified with []
      return [_GetValue(key, item) for item in current]
    else:
      return None
  return current


def _TransformNestedListData(
    data: Any,
    func: Callable[[Any], Any],
    transform_context: _TransformContext = None,
    schema: Optional[Any] = None,
) -> Any:
  """Recursively applies a function to elements in a nested structure (lists or single items).

  Args:
    data: The nested structure to process.
    func: The callable to apply to non-list, non-None elements.
    transform_context: The parse context for the data.
    schema: the schema for the data

  Returns:
    A new nested structure with the function applied.
  """
  if data is None:
    return None
  if isinstance(data, list):
    new_list = []
    for item in data:
      new_list.append(
          _TransformNestedListData(item, func, transform_context, schema)
      )
    return new_list
  else:
    if schema:
      try:
        jsonschema.validate(schema=schema, instance=data)
      except jsonschema.exceptions.ValidationError as e:
        raise exceptions.CloudDeployConfigError.for_resource_field(
            transform_context.kind,
            transform_context.name,
            transform_context.field,
            e.message,
        ) from e
    return func(data)


def _SetValue(manifest: dict[str, Any], path: str, value: Any) -> None:
  """Sets the value at a dot-separated path in a dictionary.

  If value is None, deletes the value at path.
  If path contains [], it updates elements within the list. Since this is a
  companion to _GetValue, it processes nested lists the same way.

  Args:
    manifest: dict, The dictionary to update.
    path: str, The dot-separated path to the value.
    value: Any, The value to set, or None to delete.

  Raises:
    exceptions.ManifestTransformException: a mismatch between the provided path
      and the structure of the manifest or the value being set.
  """
  if '[]' in path:
    pre, post = path.split('[]', 1)
    post = post.lstrip('.')
    current_list = _GetValue(pre, manifest)

    if not isinstance(current_list, list):
      raise exceptions.ManifestTransformException(
          f'Path "{pre}" did not lead to a list in _SetValue for path "{path}"'
      )

    if not post:
      # If post is empty, replace the current list with the new value
      if not isinstance(value, list):
        raise exceptions.ManifestTransformException(
            f'New value must be a list to replace list at "{pre}"'
        )
      # This is tricky. We need to replace the list in the parent.
      keys = pre.split('.')
      parent = manifest
      for key in keys[:-1]:
        parent = parent[key]
      parent[keys[-1]] = value
      return

    if not isinstance(value, list):
      raise exceptions.ManifestTransformException(
          f'New value must be a list when path "{path}" contains []'
      )
    if len(current_list) != len(value):
      raise exceptions.ManifestTransformException(
          f'List length mismatch: len(current_list)={len(current_list)},'
          f' len(value)={len(value)} for path "{path}"'
      )

    for i, item in enumerate(current_list):
      current_value = value[i]
      if current_value is None:
        continue
      _SetValue(item, post, current_value)
    return

  keys = path.split('.')
  current = manifest
  for key in keys[:-1]:
    if key not in current:
      # Path doesn't exist, do nothing.
      return
    if not isinstance(current[key], dict):
      raise exceptions.ManifestTransformException(
          f'Value at key "{key}" is not a dictionary for path "{path}"'
      )
    current = current[key]

  last_key = keys[-1]
  if value is None:
    if last_key in current:
      del current[last_key]
  else:
    current[last_key] = value


def _GetFinalFieldName(path: str) -> str:
  """Returns the final field name from a dot-separated path."""
  keys = path.split('.')
  final_field_name = keys[-1]
  if final_field_name.endswith('[]'):
    final_field_name = final_field_name.removesuffix('[]')
  return final_field_name
