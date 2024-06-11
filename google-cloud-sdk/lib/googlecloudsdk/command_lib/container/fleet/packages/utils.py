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
"""Helper utilities for fleet packages commands."""

import glob
import os

from googlecloudsdk.core import yaml

_DEFAULT_API_VERSION = 'v1alpha'
_RESOURCE_BUNDLE_PROJECT_SEGMENT = 1
_RESOURCE_BUNDLE_LOCATION_SEGMENT = 3

ROLLOUTS_DESCRIBE_ROLLING_TRUNCATED_MESSAGES_FORMAT = """table(info.rolloutStrategyInfo.rollingStrategyInfo.clusters.membership.basename():label=CLUSTER,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.current.version:label=CURRENT_VERSION,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.current.syncState:label=CURRENT_STATE,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.desired.version:label=DESIRED_VERSION,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.desired.syncState:label=DESIRED_STATE,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.startTime:label=START_TIME,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.endTime:label=END_TIME,
                    trim_message():label=MESSAGE)"""

ROLLOUTS_DESCRIBE_ALLATONCE_TRUNCATED_MESSAGES_FORMAT = """table(info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.membership.basename():label=CLUSTER,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.current.version:label=CURRENT_VERSION,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.current.syncState:label=CURRENT_STATE,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.desired.version:label=DESIRED_VERSION,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.desired.syncState:label=DESIRED_STATE,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.startTime:label=START_TIME,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.endTime:label=END_TIME,
                    trim_message():label=MESSAGE)"""

ROLLOUTS_DESCRIBE_ROLLING_FULL_MESSAGES_FORMAT = """table(info.rolloutStrategyInfo.rollingStrategyInfo.clusters.membership.basename():label=CLUSTER,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.current.version:label=CURRENT_VERSION,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.current.syncState:label=CURRENT_STATE,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.desired.version:label=DESIRED_VERSION,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.desired.syncState:label=DESIRED_STATE,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.startTime:label=START_TIME,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.endTime:label=END_TIME,
                    all_messages():label=MESSAGES)"""

ROLLOUTS_DESCRIBE_ALLATONCE_FULL_MESSAGES_FORMAT = """table(info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.membership.basename():label=CLUSTER,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.current.version:label=CURRENT_VERSION,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.current.syncState:label=CURRENT_STATE,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.desired.version:label=DESIRED_VERSION,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.desired.syncState:label=DESIRED_STATE,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.startTime:label=START_TIME,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.endTime:label=END_TIME,
                    all_messages():label=MESSAGES)"""


def ApiVersion():
  return _DEFAULT_API_VERSION


def FormatForRolloutsDescribe(rollout, args, less=True):
  """Sets format for `rollouts describe` depending on rollout strategy.

  Args:
    rollout: Rollout from `rollouts describe`
    args: Command line args
    less: Whether to show truncate rollout messages

  Returns:
    None
  """
  if rollout is None:
    return
  if rollout.info and rollout.info.rolloutStrategyInfo:
    if rollout.info.rolloutStrategyInfo.rollingStrategyInfo:
      if less:
        args.format = ROLLOUTS_DESCRIBE_ROLLING_TRUNCATED_MESSAGES_FORMAT
      else:
        args.format = ROLLOUTS_DESCRIBE_ROLLING_FULL_MESSAGES_FORMAT
      args.flatten = ['info.rolloutStrategyInfo.rollingStrategyInfo.clusters[]']
    if rollout.info.rolloutStrategyInfo.allAtOnceStrategyInfo:
      if less:
        args.format = ROLLOUTS_DESCRIBE_ALLATONCE_TRUNCATED_MESSAGES_FORMAT
      else:
        args.format = ROLLOUTS_DESCRIBE_ALLATONCE_FULL_MESSAGES_FORMAT
      args.flatten = [
          'info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters[]'
      ]


def _LoadResourcesFromFile(path):
  if not (path.endswith('.yaml') or path.endswith('.yml')):
    return []
  if os.path.isdir(path):
    return []
  resources = []
  loaded_resources = yaml.load_all_path(path)
  for resource in loaded_resources:
    if resource:
      dumped_resource = yaml.dump(resource)
      resources.append(dumped_resource)
  return resources


def _AllFilesUnderDir(path):
  if not path.endswith('/'):
    path += '/'
  glob_path = os.path.dirname(path) + '/**/*'
  return glob.glob(
      pathname=glob_path, recursive=True
  )


def _VariantNameFromPath(path):
  file_name = path.split('/')[-1]
  variant_name = file_name.split('.')[0]
  return variant_name


def _VariantNameFromDir(path):
  if not path.endswith('/'):
    path += '/'
  variant_name = path.split('/')[-2]
  return variant_name


def _ExpandPathForUserAndVars(path):
  user_expanded_path = os.path.expanduser(path)
  vars_expanded_path = os.path.expandvars(user_expanded_path)
  return vars_expanded_path


def GlobPatternFromSourceAndVariantsPattern(source, variants_pattern=None):
  """Creates glob pattern by combining source and variants_pattern.

  Args:
    source: Directory or source configuration file.
    variants_pattern: Optional variants_pattern for use with source.

  Returns:
    A glob_pattern for use with 'VariantsFromGlobPattern'. If source
    is a directory, the pattern is applied within the directory. If source is
    not a directory i.e., a file, the pattern is not applied.

    Ex: source=/cfg/, variants_pattern='*.yaml'; returns '/cfg/*.yaml'.
        source=manifest.yaml, variants_pattern=*; returns manifest.yaml.
  """
  if not variants_pattern:
    return source
  expanded_source = _ExpandPathForUserAndVars(source)
  expanded_variants_pattern = _ExpandPathForUserAndVars(variants_pattern)
  if os.path.isdir(expanded_source):
    return os.path.join(expanded_source, expanded_variants_pattern)
  else:
    return expanded_source


def ValidateSource(source):
  expanded_source = _ExpandPathForUserAndVars(source)
  if not os.path.isdir(expanded_source) and not os.path.isfile(expanded_source):
    raise ValueError(
        f'Source must be a directory or file, got {expanded_source}.'
    )


def VariantsFromGlobPattern(glob_pattern):
  """Returns a dictionary of input-format variants discovered from a glob.

  Gets all files from user-supplied glob pattern and creates variant(s). There
  will be a single variant 'default' if the inputted glob pattern has no
  wildcards, and multiple variants if there are wildcards. These variant(s)
  can be used for more advanced deployment setups.

  Args:
    glob_pattern: Pattern compatible with python's glob library

  Returns:
    A dict of input-formatted variants, for example:
      {'us-a': [resources...], 'us-b': [resources...]}
  """
  user_expanded_glob = os.path.expanduser(glob_pattern)
  expanded_glob = os.path.expandvars(user_expanded_glob)
  paths = glob.glob(expanded_glob)
  variants = {}
  if len(paths) == 1:
    if os.path.isfile(paths[0]):
      resources = _LoadResourcesFromFile(paths[0])
      if resources:
        variants['default'] = resources
    elif os.path.isdir(paths[0]):
      files_list = _AllFilesUnderDir(paths[0])
      all_resources = []
      for file in files_list:
        full_file_path = os.path.join(paths[0], file)
        resources = _LoadResourcesFromFile(full_file_path)
        if resources:
          all_resources.extend(resources)
      if all_resources:
        variants['default'] = all_resources
  elif len(paths) > 1:
    for path in paths:
      if os.path.isfile(path):
        resources = _LoadResourcesFromFile(path)
        if resources:
          variant_name = _VariantNameFromPath(path)
          variants[variant_name] = resources
      elif os.path.isdir(path):
        files_list = _AllFilesUnderDir(path)
        all_resources = []
        for file in files_list:
          full_file_path = os.path.join(path, file)
          resources = _LoadResourcesFromFile(full_file_path)
          if resources:
            all_resources.extend(resources)
        if all_resources:
          variant_name = _VariantNameFromDir(path)
          variants[variant_name] = all_resources
  return variants


def TransformTrimMessage(resource):
  """Trims rollout-level message if it's too long.

  Args:
    resource: A RolloutInfo resource

  Returns:
    Message limited to 40 characters
  """
  truncated_message_length = 40
  messages = _GetMessagesFromResource(resource)
  if not messages:
    return ''
  if len(messages) >= 1 and len(messages[0]) > truncated_message_length:
    return messages[0][:truncated_message_length] + '...'
  return messages[0]


def _GetMessagesFromResource(resource):
  """Gathers messages from different levels of a Rollout resource.

  Args:
    resource: A RolloutInfo resource, from `... rollouts describe ...`

  Returns:
    A list of messages from the Rollout resource.
  """
  messages = []
  if resource is None:
    return messages
  info_message = resource.get('info', {}).get('message', '')
  if info_message:
    messages.append(info_message)
  cluster_infos = (
      resource.get('info', {})
      .get('rolloutStrategyInfo', {})
      .get('rollingStrategyInfo', {})
      .get('clusters', [])
  )
  if cluster_infos:
    if isinstance(cluster_infos, dict):
      for cluster_info in cluster_infos.values():
        if 'messages' in cluster_info:
          messages.extend(cluster_info['messages'])
        if 'current' in cluster_info and 'messages' in cluster_info['current']:
          messages.extend(cluster_info['current']['messages'])
  cluster_infos = (
      resource.get('info', {})
      .get('rolloutStrategyInfo', {})
      .get('allAtOnceStrategyInfo', {})
      .get('clusters', [])
  )
  if cluster_infos:
    if isinstance(cluster_infos, dict):
      for cluster_info in cluster_infos.values():
        if 'messages' in cluster_info:
          messages.extend(cluster_info['messages'])
        if 'current' in cluster_info and 'messages' in cluster_info['current']:
          messages.extend(cluster_info['current']['messages'])
    elif isinstance(cluster_infos, list):
      for cluster_info in cluster_infos:
        if 'messages' in cluster_info:
          messages.extend(cluster_info['messages'])
        curr_messages = cluster_info.get('current', {}).get('messages', [])
        if curr_messages:
          messages.extend(curr_messages)
  info_errors = resource.get('info', {}).get('errors', [])
  if info_errors:
    for error in info_errors:
      info_message = error.get('errorMessage', '')
      if info_message:
        messages.append(info_message)

  return messages


def TransformAllMessages(resource):
  """Gathers messages from all levels from a Rollout resource.

  Args:
    resource: A RolloutInfo resource, from `... rollouts describe ...`

  Returns:
    All messages on a Rollout, including sync-level, cluster-level, and
    rollout-level messages.
  """
  messages = _GetMessagesFromResource(resource)
  if not messages:
    return ''
  elif len(messages) == 1:
    return messages[0]
  return messages


def TransformListFleetPackageErrors(resource):
  """Gathers errors from 'info.Errors' and returns their errorMessages."""
  messages = []
  if resource is None:
    return ''

  errors = resource.get('info', {}).get('errors', [])
  for error in errors:
    error_message = error.get('errorMessage', '')
    if error_message:
      messages.append(error_message)

  if not messages:
    return ''
  elif len(messages) == 1:
    return messages[0]
  return messages


def UpsertFleetPackageName(fleet_package, fully_qualified_name):
  """Upserts the correct fleet package name into fleet package resource.

  Args:
    fleet_package: A user-inputted FleetPackage which may or may not have a name
    fully_qualified_name: The fully qualified name of the FleetPackage resource.

  Returns:
    A FleetPackage that definitely has the correct fully qualified name.
  """
  if not fleet_package.name:
    fleet_package.name = fully_qualified_name
  return fleet_package
