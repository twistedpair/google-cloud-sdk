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

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import yaml

_DEFAULT_API_VERSION = 'v1alpha'
_RESOURCE_BUNDLE_PROJECT_SEGMENT = 1
_RESOURCE_BUNDLE_LOCATION_SEGMENT = 3


def ApiVersion():
  return _DEFAULT_API_VERSION


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


def _SplitResourceBundleNameFromFleetPackage(fleet_package):
  resource_bundle_name = (
      fleet_package.resourceBundleSelector.resourceBundle.name
  )
  return resource_bundle_name.split('/')


def _ExpandPathForUserAndVars(path):
  user_expanded_path = os.path.expanduser(path)
  vars_expanded_path = os.path.expandvars(user_expanded_path)
  return vars_expanded_path


def _GetClientInstance(no_http=False):
  return apis.GetClientInstance('configdelivery', ApiVersion(), no_http=no_http)


def _GetMessagesModule():
  return _GetClientInstance().MESSAGES_MODULE


def UpsertDefaultVariants(fleet_package):
  if (
      fleet_package.resourceBundleSelector
      and fleet_package.resourceBundleSelector.cloudBuildRepository
  ):
    if not fleet_package.resourceBundleSelector.cloudBuildRepository.variants:
      messages = _GetMessagesModule()
      fleet_package.resourceBundleSelector.cloudBuildRepository.variants = (
          messages.Variants(directories=messages.Directories(pattern='.'))
      )
  return fleet_package


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


def ProjectFromFleetPackage(fleet_package):
  """Project segment parsed from Fleet Package file input."""
  split_bundle = _SplitResourceBundleNameFromFleetPackage(fleet_package)
  return split_bundle[_RESOURCE_BUNDLE_PROJECT_SEGMENT]


def LocationFromFleetPackage(fleet_package):
  """Location segment parsed from Fleet Package file input."""
  split_bundle = _SplitResourceBundleNameFromFleetPackage(fleet_package)
  return split_bundle[_RESOURCE_BUNDLE_LOCATION_SEGMENT]


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
  if not resource.get('info') or not resource.get('info').get('message'):
    return ''
  message = resource.get('info').get('message')
  if len(message) > truncated_message_length:
    return message[:truncated_message_length] + '...'
  return message


def TransformAllMessages(resource):
  """Gathers messages from all levels from a Rollout resource.

  Args:
    resource: A RolloutInfo resource, from `... rollouts describe ...`

  Returns:
    All messages on a Rollout, including sync-level, cluster-level, and
    rollout-level messages.
  """
  messages = []
  if 'message' in resource.get('info'):
    messages.append(resource.get('info').get('message'))
  if (
      'rolloutStrategyInfo.rollingStrategyInfo.clusters.messages'
      in resource.get('info')
  ):
    messages.extend(
        resource.get('info')
        .get('rolloutStrategyInfo')
        .get('rollingStrategyInfo')
        .get('clusters')
        .get('messages')
    )
  if (
      'rolloutStrategyInfo.rollingStrategyInfo.clusters.current.messages'
      in resource.get('info')
  ):
    messages.extend(
        resource.get('info')
        .get('rolloutStrategyInfo')
        .get('rollingStrategyInfo')
        .get('clusters')
        .get('current')
        .get('messages')
    )
  if (
      'rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.messages'
      in resource.get('info')
  ):
    messages.extend(
        resource.get('info')
        .get('rolloutStrategyInfo')
        .get('allAtOnceStrategyInfo')
        .get('clusters')
        .get('messages')
    )
  if (
      'rolloutStrategyInfo.allAtOnceStrategyInfo.clusters.current.messages'
      in resource.get('info')
  ):
    messages.extend(
        resource.get('info')
        .get('rolloutStrategyInfo')
        .get('allAtOnceStrategyInfo')
        .get('clusters')
        .get('current')
        .get('messages')
    )

  return messages
