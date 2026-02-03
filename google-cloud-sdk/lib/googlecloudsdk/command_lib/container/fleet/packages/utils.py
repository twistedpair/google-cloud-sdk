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
import itertools
import os
import pathlib

from googlecloudsdk.core import yaml

_DEFAULT_API_VERSION = 'v1alpha'
_RESOURCE_BUNDLE_PROJECT_SEGMENT = 1
_RESOURCE_BUNDLE_LOCATION_SEGMENT = 3

ROLLOUTS_DESCRIBE_ROLLING_TRUNCATED_MESSAGES_FORMAT = """table(info.rolloutStrategyInfo.rollingStrategyInfo.clusters.membership.basename():label=CLUSTER,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.current.version:label=CURRENT_VERSION,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.current.syncState:label=SYNC_STATE,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.desired.version:label=DESIRED_VERSION,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.startTime:label=START_TIME,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.endTime:label=END_TIME,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.state:label=STATE,
                    trim_message():label=MESSAGE)"""

ROLLOUTS_DESCRIBE_ALLATONCE_TRUNCATED_MESSAGES_FORMAT = """table(info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.membership.basename():label=CLUSTER,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.current.version:label=CURRENT_VERSION,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.current.syncState:label=SYNC_STATE,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.desired.version:label=DESIRED_VERSION,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.startTime:label=START_TIME,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.endTime:label=END_TIME,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.state:label=STATE,
                    trim_message():label=MESSAGE)"""

ROLLOUTS_DESCRIBE_ROLLING_FULL_MESSAGES_FORMAT = """table(info.rolloutStrategyInfo.rollingStrategyInfo.clusters.membership.basename():label=CLUSTER,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.current.version:label=CURRENT_VERSION,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.current.syncState:label=SYNC_STATE,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.desired.version:label=DESIRED_VERSION,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.startTime:label=START_TIME,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.endTime:label=END_TIME,
                    info.rolloutStrategyInfo.rollingStrategyInfo.clusters.state:label=STATE,
                    all_messages():label=MESSAGES)"""

ROLLOUTS_DESCRIBE_ALLATONCE_FULL_MESSAGES_FORMAT = """table(info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.membership.basename():label=CLUSTER,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.current.version:label=CURRENT_VERSION,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.current.syncState:label=SYNC_STATE,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.desired.version:label=DESIRED_VERSION,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.startTime:label=START_TIME,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.endTime:label=END_TIME,
                    info.rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.state:label=STATE,
                    all_messages():label=MESSAGES)"""


def ApiVersion():
  return _DEFAULT_API_VERSION


def FormatForRolloutsDescribe(rollout, args, less=False):
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
  """Returns paths of all .yaml and .yml files in a directory and subdirectories.

  Args:
    path: The root directory to search in.

  Returns:
    A list of strings, where each string is a path to a .yaml or .yml file.
  """
  if not path.endswith('/'):
    path += '/'
  glob_path = os.path.dirname(path) + '/**/*'
  return [
      p
      for p in glob.glob(pathname=glob_path, recursive=True)
      if os.path.isfile(p) and p.endswith(('.yaml', '.yml'))
  ]


def _VariantNameFromFilePath(path):
  return pathlib.Path(path).stem


def _VariantNameFromDir(path):
  return pathlib.Path(path).name


def ExpandPathForUser(path):
  return os.path.expanduser(path)


def _ExpandPathForUserAndVars(path):
  user_expanded_path = os.path.expanduser(path)
  vars_expanded_path = user_expanded_path
  if '$' in vars_expanded_path:
    vars_expanded_path = os.path.expandvars(vars_expanded_path)
  return vars_expanded_path


def _FileNotFoundMessage(path):
  return f'Source file or dir not found: {path}.'


def _FileWrongTypeMessage(path):
  return f'Source is not of type directory or file: {path}.'


def VariantsFromGlobPattern(glob_pattern):
  """Returns a dictionary of input-format variants discovered from a glob.

  Gets all files from user-supplied glob pattern and creates variant(s). If
  glob_pattern is for YAML files (e.g. *.yaml), variants are created from each
  file matched. If glob_pattern is for directories (e.g. *), variants are
  created from each directory matched. These variant(s) can be used for more
  advanced deployment setups.

  Args:
    glob_pattern: Pattern compatible with python's glob library

  Returns:
    A dict of input-formatted variants, for example:
      {'us-a': [resources...], 'us-b': [resources...]}

  Raises:
    ValueError: if duplicate variant names are detected.
  """
  user_expanded_glob = os.path.expanduser(glob_pattern)
  expanded_glob = user_expanded_glob
  if '$' in expanded_glob:
    expanded_glob = os.path.expandvars(expanded_glob)

  resources_by_variant_name = {}
  origin_by_variant_name = (
      {}
  )  # To track origins of variant names for dup detection.
  is_file_mask = '.yaml' in glob_pattern or '.yml' in glob_pattern
  paths = glob.glob(expanded_glob)

  if not is_file_mask:
    paths = [p for p in paths if os.path.isdir(p)]

  paths.sort()
  for path in paths:
    if is_file_mask:
      if os.path.isfile(path):
        resources = _LoadResourcesFromFile(path)
        if resources:
          variant_name = _VariantNameFromFilePath(path)
          if variant_name in origin_by_variant_name:
            raise ValueError(
                f'Duplicate variant name {variant_name!r} detected: paths'
                f' {origin_by_variant_name[variant_name]!r} and {path!r}'
                ' resulted in the same variant name.'
            )
          resources_by_variant_name[variant_name] = resources
          origin_by_variant_name[variant_name] = path
    else:  # directory mask
      if os.path.isdir(path):
        files_list = _AllFilesUnderDir(path)
        resources_per_file = (
            _LoadResourcesFromFile(os.path.abspath(file))
            for file in files_list
        )
        all_resources = list(itertools.chain.from_iterable(resources_per_file))
        if all_resources:
          variant_name = _VariantNameFromDir(path)
          if variant_name in origin_by_variant_name:
            raise ValueError(
                f'Duplicate variant name {variant_name!r} detected: paths'
                f' {origin_by_variant_name[variant_name]!r} and {path!r}'
                ' resulted in the same variant name.'
            )
          resources_by_variant_name[variant_name] = all_resources
          origin_by_variant_name[variant_name] = path
  return resources_by_variant_name


def TransformTrimClusterLevelMessages(resource):
  """Shows the first cluster-level message and truncates it if it's too long.

  Args:
    resource: A RolloutInfo resource

  Returns:
    Message limited to 40 characters
  """
  truncated_message_length = 40
  messages = _GetClusterLevelMessagesFromResource(resource)
  if not messages:
    return ''
  if len(messages) >= 1 and len(messages[0]) > truncated_message_length:
    return messages[0][:truncated_message_length] + '...'
  return messages[0]


def TransformTrimRolloutLevelMessage(resource):
  """Trims rollout-level message if it's too long.

  Args:
    resource: A Rollout resource

  Returns:
    String message limited to 40 characters
  """
  rollout_info = resource.get('info', {})
  if rollout_info:
    rollout_message = rollout_info.get('message', '')
    if rollout_message:
      if len(rollout_message) > 40:
        return rollout_message[:40] + '...'
      return rollout_message
  return ''


def _GetClusterLevelMessagesFromResource(resource):
  """Gathers cluster-level messages from a Rollout resource.

  Args:
    resource: A Rollout resource, from `... rollouts describe ...`

  Returns:
    A list of messages from the Rollout resource.
  """
  messages = []
  if not resource:
    return []
  rollout_strategy_info = resource.get('info', {}).get(
      'rolloutStrategyInfo', {}
  )
  for rollout_info in rollout_strategy_info.values():
    clusters = rollout_info.get('clusters', [])
    if 'messages' in clusters:
      messages.extend(clusters.get('messages', []))
    current = clusters.get('current', {})
    if 'messages' in current:
      messages.extend(current.get('messages', []))

  info_errors = resource.get('info', {}).get('errors', [])
  if info_errors:
    for error in info_errors:
      info_message = error.get('errorMessage', '')
      if info_message:
        messages.append(info_message)

  return messages


def TransformAllClusterLevelMessages(resource):
  """Returns all cluster-level messages from a Rollout resource.

  Args:
    resource: A Rollout resource, from `... rollouts describe ...`

  Returns:
    A single string or string array of cluster-level messages.
  """
  messages = _GetClusterLevelMessagesFromResource(resource)
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


def FixFleetPackagePathForCloudBuild(fleet_package):
  """Removes leading slash from fleet package path if it uses Cloud Build.

  If we don't remove the leading slash, parsing the path will fail for cloud
  build. See b/352756986#comment13

  Args:
    fleet_package: A user-inputted FleetPackage which may need its path fixed.

  Returns:
    A FleetPackage with a fixed path if it uses Cloud Build, unchanged if it
    doesn't use Cloud Build.
  """
  if _FleetPackageUsesCloudBuild(fleet_package):
    path = fleet_package.resourceBundleSelector.cloudBuildRepository.path
    if path is not None and path.startswith('/'):
      if path == '/':
        fleet_package.resourceBundleSelector.cloudBuildRepository.path = './'
      else:
        fleet_package.resourceBundleSelector.cloudBuildRepository.path = (
            fleet_package.resourceBundleSelector.cloudBuildRepository.path[1:]
        )
  return fleet_package


def _FleetPackageUsesCloudBuild(fleet_package):
  return (
      fleet_package
      and fleet_package.resourceBundleSelector
      and fleet_package.resourceBundleSelector.cloudBuildRepository is not None
  )
