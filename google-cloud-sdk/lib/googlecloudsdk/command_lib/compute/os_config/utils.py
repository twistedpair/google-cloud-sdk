# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Utility functions for GCE OS Config commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from enum import Enum
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.util.args import common_args
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
import six


class InstanceDetailsStates(Enum):
  """Indicate instance progress during a patch job execution."""
  NOTIFIED = 1
  PATCHING = 2
  FINISHED = 3


INSTANCE_DETAILS_KEY_MAP = {
    'instancesAcked': InstanceDetailsStates.NOTIFIED,
    'instancesApplyingPatches': InstanceDetailsStates.PATCHING,
    'instancesDownloadingPatches': InstanceDetailsStates.PATCHING,
    'instancesFailed': InstanceDetailsStates.FINISHED,
    'instancesInactive': InstanceDetailsStates.FINISHED,
    'instancesNotified': InstanceDetailsStates.NOTIFIED,
    'instancesPending': InstanceDetailsStates.NOTIFIED,
    'instancesRebooting': InstanceDetailsStates.PATCHING,
    'instancesStarted': InstanceDetailsStates.PATCHING,
    'instancesSucceeded': InstanceDetailsStates.FINISHED,
    'instancesSucceededRebootRequired': InstanceDetailsStates.FINISHED,
    'instancesTimedOut': InstanceDetailsStates.FINISHED,
    'instancesRunningPrePatchStep': InstanceDetailsStates.PATCHING,
    'instancesRunningPostPatchStep': InstanceDetailsStates.PATCHING,
}

_GCS_PREFIXES = ('gs://', 'https://www.googleapis.com/storage/v1/',
                 'https://storage.googleapis.com/')


def GetParentUriPath(parent_name, parent_id):
  """Return the URI path of a GCP parent resource."""
  return '/'.join([parent_name, parent_id])


def GetProjectUriPath(project):
  """Return the URI path of a GCP project."""
  return GetParentUriPath('projects', project)


def GetFolderUriPath(folder):
  """Return the URI path of a GCP folder."""
  return GetParentUriPath('folders', folder)


def GetOrganizationUriPath(organization):
  """Return the URI path of a GCP organization."""
  return GetParentUriPath('organizations', organization)


def GetPatchJobUriPath(project, patch_job):
  """Return the URI path of an osconfig patch job."""
  return '/'.join(['projects', project, 'patchJobs', patch_job])


def GetPatchJobName(patch_job_uri):
  """Return the name of a patch job from its URI."""
  return patch_job_uri.split('/')[3]


def GetGuestPolicyRelativePath(parent, guest_policy):
  """Return the relative path of an osconfig guest policy."""
  return '/'.join([parent, 'guestPolicies', guest_policy])


def AddResourceParentArgs(parser, noun, verb):
  """Add project, folder, and organization flags to the parser."""
  parent_resource_group = parser.add_group(
      help='The scope of the {} which defaults to project if unspecified.'
      .format(noun),
      mutex=True,
  )
  common_args.ProjectArgument(
      help_text_to_prepend='The project of the {} {}.'.format(
          noun, verb)).AddToParser(parent_resource_group)
  parent_resource_group.add_argument(
      '--folder',
      metavar='FOLDER_ID',
      type=str,
      help='The folder of the {} {}.'.format(noun, verb),
  )
  parent_resource_group.add_argument(
      '--organization',
      metavar='ORGANIZATION_ID',
      type=str,
      help='The organization of the {} {}.'.format(noun, verb),
  )


def GetGuestPolicyUriPath(parent_type, parent_name, policy_id):
  """Return the URI path of an osconfig guest policy."""
  return '/'.join([parent_type, parent_name, 'guestPolicies', policy_id])


def GetResourceAndUpdateFieldsFromFile(file_path, resource_message_type):
  """Return the resource message and update fields in file."""
  try:
    resource_to_parse = yaml.load_path(file_path)
  except yaml.YAMLParseError as e:
    raise exceptions.BadFileException(
        'Policy config file [{0}] cannot be parsed. {1}'
        .format(file_path, six.text_type(e)))
  except yaml.FileLoadError as e:
    raise exceptions.BadFileException(
        'Policy config file [{0}] cannot be opened or read. {1}'
        .format(file_path, six.text_type(e)))

  if not isinstance(resource_to_parse, dict):
    raise exceptions.BadFileException(
        'Policy config file [{0}] is not a properly formatted YAML or JSON '
        'file.'.format(file_path))

  update_fields = list(resource_to_parse.keys())

  try:
    resource = encoding.PyValueToMessage(resource_message_type,
                                         resource_to_parse)
  except (AttributeError) as e:
    raise exceptions.BadFileException(
        'Policy config file [{0}] is not a properly formatted YAML or JSON '
        'file. {1}'.format(file_path, six.text_type(e)))

  return (resource, update_fields)


def GetGcsParams(arg_name, path):
  """Returns information for a Google Cloud Storage object.

  Args:
      arg_name: The name of the argument whose value may be a GCS object path.
      path: A string whose value may be a GCS object path.
  """
  obj_ref = None
  for prefix in _GCS_PREFIXES:
    if path.startswith(prefix):
      obj_ref = resources.REGISTRY.Parse(path)
      break

  if not obj_ref:
    return None

  if not hasattr(obj_ref, 'bucket') or not hasattr(obj_ref, 'object'):
    raise exceptions.InvalidArgumentException(
        arg_name,
        'The provided Google Cloud Storage path [{}] is invalid.'.format(path))

  obj_str = obj_ref.object.split('#')
  if len(obj_str) != 2 or not obj_str[1].isdigit():
    raise exceptions.InvalidArgumentException(
        arg_name,
        'The provided Google Cloud Storage path [{}] does not contain a valid '
        'generation number.'.format(path))

  return {
      'bucket': obj_ref.bucket,
      'object': obj_str[0],
      'generationNumber': int(obj_str[1]),
  }
