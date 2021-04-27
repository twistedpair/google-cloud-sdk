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
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files
import six

RESOURCE_NOT_FOUND = (
    'The following resources [{}] are snapped in the release, '
    'but no longer exist.\n')
RESOURCE_CREATED = ('The following targets [{}] are not snapped in the '
                    'release.\n')
RESOURCE_CHANGED = ('The following resources [{}] have been changed after the '
                    'release was created.\n')


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
    if target_ref.RelativeName() not in [
        obj.name for obj in release_obj.targetSnapshots
    ]:
      resource_created.append(target_ref.RelativeName())
  for obj in release_obj.targetSnapshots:
    # Check if the snapped targets still exist.
    try:
      target_obj = target.TargetsClient().Get(obj.name)
      # Checks if the snapped targets have been changed.
      if target_obj.etag != obj.etag:
        resource_changed.append(target_obj.name)
    except apitools_exceptions.HttpError as error:
      log.debug('Failed to get target {}: {}'.format(obj.name, error.content))
      log.status.Print('Unable to get target {}'.format(obj.name))
      resource_not_found.append(obj.name)

  name = release_obj.deliveryPipelineSnapshot.name
  # Checks if the pipeline exists.
  try:
    pipeline_obj = delivery_pipeline.DeliveryPipelinesClient().Get(name)
    # Checks if the pipeline has been changed.
    if pipeline_obj.etag != release_obj.deliveryPipelineSnapshot.etag:
      resource_changed.append(name)
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
    prompt = RESOURCE_CREATED.format(', '.join(resource_created))
  if resource_not_found:
    prompt += RESOURCE_NOT_FOUND.format(', '.join(resource_not_found))
  if resource_changed:
    prompt += RESOURCE_CHANGED.format(', '.join(resource_changed))

  log.status.Print(prompt)
