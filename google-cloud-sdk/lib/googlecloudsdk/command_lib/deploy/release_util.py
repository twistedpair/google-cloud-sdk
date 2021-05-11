# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utilities for the cloud deploy release commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.clouddeploy import delivery_pipeline
from googlecloudsdk.api_lib.clouddeploy import target
from googlecloudsdk.command_lib.projects import util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files

import six

RESOURCE_NOT_FOUND = ('The following resources are snapped in the release, '
                      'but no longer exist:\n{}\n\nThese resources were cached '
                      'when the release was created, but their source '
                      'may have been deleted.\n\n')
RESOURCE_CREATED = (
    'The following target is not snapped in the release:\n{}\n\n'
    'You may have specified a target that wasn\'t '
    'cached when the release was created.\n\n')
RESOURCE_CHANGED = ('The following snapped releases resources differ from '
                    'their current definition:\n{}\n\nThe pipeline or targets '
                    'were cached when the release was created, but the source '
                    'has changed since then. You should review the differences '
                    'before proceeding.\n')


class ParserError(exceptions.Error):
  """Error parsing JSON into a dictionary."""

  def __init__(self, path, msg):
    """Initialize a release_util.ParserError.

    Args:
      path: build artifacts file path.
      msg: error message.
    """
    msg = 'parsing {path}: {msg}'.format(
        path=path,
        msg=msg,
    )
    super(ParserError, self).__init__(msg)


def SetBuildArtifacts(images, messages, release_config):
  """Set build_artifacts field of the release message.

  Args:
    images: docker image name and tag dictionary.
    messages: Module containing the Cloud Deploy messages.
    release_config: Cloud Deploy release message.

  Returns:
    Cloud Deploy release message.
  """
  if not images:
    return release_config
  build_artifacts = []
  for key, value in sorted(six.iteritems(images)):  # Sort for tests
    build_artifacts.append(messages.BuildArtifact(imageName=key, tag=value))
  release_config.buildArtifacts = build_artifacts

  return release_config


def LoadBuildArtifactFile(path):
  """Load images from a file containing JSON build data.

  Args:
    path: build artifacts file path.

  Returns:
    Docker image name and tag dictionary.
  """
  with files.FileReader(path) as f:  # Returns user-friendly error messages
    try:
      structured_data = yaml.load(f, file_hint=path)
    except yaml.Error as e:
      raise ParserError(path, e.inner_error)
    images = {}
    for build in structured_data['builds']:
      images[build['imageName']] = build['tag']

    return images


def DiffSnappedPipeline(release_ref, release_obj, to_target=None):
  """Detects the differences between current delivery pipeline and target definitions, from those associated with the release being promoted.

  Changes are determined through etag value differences.

  This runs the following checks:
    - if the to_target is one of the snapped targets in the release.
    - if the snapped targets still exist.
    - if the snapped targets have been changed.
    - if the snapped pipeline still exists.
    - if the snapped pipeline has been changed.

  Args:
    release_ref: release resource object.
    release_obj: release message.
    to_target: the target to promote the release to. If specified, this verifies
      if the target has been snapped in the release.

  Returns:
    the list of the resources that no longer exist.
    the list of the resources that have been changed.
    the list of the resources that aren't snapped in the release.
  """
  resource_not_found = []
  resource_changed = []
  resource_created = []
  # check if the to_target is one of the snapped targets in the release.
  if to_target:
    ref_dict = release_ref.AsDict()
    target_ref = resources.REGISTRY.Parse(
        to_target,
        collection='clouddeploy.projects.locations.deliveryPipelines.targets',
        params={
            'projectsId': ref_dict['projectsId'],
            'locationsId': ref_dict['locationsId'],
            'deliveryPipelinesId': ref_dict['deliveryPipelinesId'],
            'targetsId': to_target,
        })
    if target_ref.Name() not in [
        GetResourceName(obj.name) for obj in release_obj.targetSnapshots
    ]:
      resource_created.append(target_ref.RelativeName())

  for obj in release_obj.targetSnapshots:
    target_name = ResourceNameProjectNumberToId(obj.name)
    # Check if the snapped targets still exist.
    try:
      target_obj = target.TargetsClient().Get(target_name)
      # Checks if the snapped targets have been changed.
      if target_obj.etag != obj.etag:
        resource_changed.append(target_name)
    except apitools_exceptions.HttpError as error:
      log.debug('Failed to get target {}: {}'.format(target_name,
                                                     error.content))
      log.status.Print('Unable to get target {}\n'.format(target_name))
      resource_not_found.append(ResourceNameProjectNumberToId(target_name))

  name = release_obj.deliveryPipelineSnapshot.name
  # Checks if the pipeline exists.
  try:
    pipeline_obj = delivery_pipeline.DeliveryPipelinesClient().Get(name)
    # Checks if the pipeline has been changed.
    if pipeline_obj.etag != release_obj.deliveryPipelineSnapshot.etag:
      resource_changed.append(release_ref.Parent().RelativeName())
  except apitools_exceptions.HttpError as error:
    log.debug('Failed to get pipeline {}: {}'.format(name, error.content))
    log.status.Print('Unable to get delivery pipeline {}'.format(name))
    resource_not_found.append(name)

  return resource_created, resource_changed, resource_not_found


def PrintDiff(release_ref, release_obj, target_id=None, prompt=''):
  """Prints differences between current and snapped delivery pipeline and target definitions.

  Args:
    release_ref: release resource object.
    release_obj: release message.
    target_id: target id, e.g. test/stage/prod.
    prompt: prompt text.
  """
  resource_created, resource_changed, resource_not_found = DiffSnappedPipeline(
      release_ref, release_obj, target_id)

  if resource_created:
    prompt += RESOURCE_CREATED.format('\n'.join(
        BulletedList(resource_created, ResourceNameProjectNumberToId)))
  if resource_not_found:
    prompt += RESOURCE_NOT_FOUND.format('\n'.join(
        BulletedList(resource_not_found, ResourceNameProjectNumberToId)))
  if resource_changed:
    prompt += RESOURCE_CHANGED.format('\n'.join(
        BulletedList(resource_changed, ResourceNameProjectNumberToId)))

  log.status.Print(prompt)


def ResourceNameProjectNumberToId(name):
  """Replaces the project number in resource name with project ID.

  e.g. projects/my-project/locations/ will become projects/12321/locations/

  Args:
    name: resource name.

  Returns:
    transformed resource name.
  """
  template = 'projects/{}/locations/'
  project_id = properties.VALUES.core.project.GetOrFail()
  project_num = util.GetProjectNumber(project_id)
  project_id_str = template.format(project_id)
  project_num_str = template.format(project_num)
  return name.replace(project_num_str, project_id_str)


def GetResourceName(name, resource_type='targets'):
  """Gets resource ID from a resource name.

  This will return "pipeline" for a given name
  "projects/my-project/locations/us-central1/deliveryPipelines/pipeline".

  Args:
    name: resource name.
    resource_type: one of [pipelines,targets,releases,rollouts]

  Returns:
    resource ID.
  """
  return resources.REGISTRY.ParseRelativeName(
      name,
      collection='clouddeploy.projects.locations.deliveryPipelines.' +
      resource_type,
  ).Name()


def BulletedList(str_list, trans_func=None):
  """Converts a list of string to a bulleted list.

  The returned list looks like ['- string1','- string2'].

  Args:
    str_list: list to be converted.
    trans_func: string transformation function.

  Returns:
    list of the transformed strings.
  """
  for i in range(len(str_list)):
    if trans_func:
      str_list[i] = trans_func(str_list[i])
    str_list[i] = '- ' + str_list[i]

  return str_list


def GetSnappedTarget(release_obj, target_id):
  """Get the snapped target in a release by target ID.

  Args:
    release_obj: release message object.
    target_id: target ID.

  Returns:
    target message object.
  """
  target_obj = None

  for snapshot in release_obj.targetSnapshots:
    if GetResourceName(snapshot.name) == target_id:
      target_obj = snapshot
      break

  return target_obj
