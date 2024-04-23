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
  resource_bundle_name = fleet_package.resourceBundleSelector.resourceBundle
  return resource_bundle_name.split('/')


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
