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
"""Utilities for the cloud deploy target resource."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.clouddeploy import release
from googlecloudsdk.api_lib.clouddeploy import rollout
from googlecloudsdk.api_lib.clouddeploy import target
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.projects import util as p_util
from googlecloudsdk.core import log
from googlecloudsdk.core import resources

import six

_LESS_SHARED_TARGET_COLLECTION = 'clouddeploy.projects.locations.deliveryPipelines.targets'
_SHARED_TARGET_COLLECTION = 'clouddeploy.projects.locations.targets'


def GetReleasesAndCurrentRollout(target_ref, pipeline_id, index=0):
  """Gets the releases in the specified target and the last deployment associated with the target.

  Args:
    target_ref: protorpc.messages.Message, target resource object.
    pipeline_id: str, delivery pipeline ID.
    index: int, the nth rollout that is deployed to the target.

  Returns:
    release messages associated with the target.
    last deployed rollout message.
  Raises:
   Exceptions raised by RolloutClient.GetCurrentRollout()
  """
  releases = []
  current_rollout = None
  try:
    # get all of the releases associated with the target.
    target_dict = target_ref.AsDict()
    project_number = p_util.GetProjectNumber(target_dict['projectsId'])
    target_ref_project_number = TargetReference(
        target_dict['targetsId'], project_number, target_dict['locationsId'],
        target_dict.get('deliveryPipelinesId'))
    releases = release.ReleaseClient().ListReleasesByTarget(
        target_ref_project_number, target_dict['projectsId'], pipeline_id)
    # find the last deployed rollout.
    current_rollout = rollout.RolloutClient().GetCurrentRollout(
        releases, target_ref, index)
  except apitools_exceptions.HttpError as error:
    log.debug('failed to get the releases and current rollout of target {}: {}'
              .format(target_ref.RelativeName(), error.content))

  return releases, current_rollout


def GetTargetReferenceInUnknownCollection(target_id, project, location_id,
                                          pipeline_id):
  """Gets the target or less shared target.

  When target collection is unknown, this will try to get the shared
  target(default target type) first, then less shared target(legacy type).

  Args:
    target_id: str, target ID
    project: str, project ID.
    location_id: str, region ID.
    pipeline_id: str, delivery pipeline ID.

  Returns:
    apitools.base.protorpclite.messages.Message, target message.
  """
  # Get the shared target first.
  target_ref = resources.REGISTRY.Parse(
      None,
      collection=_SHARED_TARGET_COLLECTION,
      params={
          'projectsId': project,
          'locationsId': location_id,
          'targetsId': target_id,
      })
  try:
    target_obj = target.TargetsClient().Get(target_ref.RelativeName())
  except apitools_exceptions.HttpError as error:
    if error.status_code != six.moves.http_client.NOT_FOUND:
      raise calliope_exceptions.HttpException(error)

    # Get the less-shared target
    try:
      target_ref = resources.REGISTRY.Parse(
          None,
          collection=_LESS_SHARED_TARGET_COLLECTION,
          params={
              'projectsId': project,
              'locationsId': location_id,
              'deliveryPipelinesId': pipeline_id,
              'targetsId': target_id,
          })

      target_obj = target.TargetsClient().GetLessShared(
          target_ref.RelativeName())
    except apitools_exceptions.HttpError:

      raise calliope_exceptions.HttpException(error)

  return target_ref, target_obj


def TargetReferenceFromName(target_name):
  """Creates a target reference from full name.

  Args:
    target_name: str, target resource name.

  Returns:
    Target reference.
  """

  col = _SHARED_TARGET_COLLECTION
  if 'deliveryPipelines/' in target_name:
    col = _LESS_SHARED_TARGET_COLLECTION

  return resources.REGISTRY.ParseRelativeName(target_name, collection=col)


def TargetId(target_name_or_id):
  """Returns target ID.

  Args:
    target_name_or_id: str, target full name or ID.

  Returns:
    Target ID.
  """

  if 'projects/' in target_name_or_id:
    return TargetReferenceFromName(target_name_or_id).Name()

  return target_name_or_id


def TargetReference(target_name_or_id, project, location_id, pipeline_id=None):
  """Creates the target reference base on the parameters.

  Returns the less shared target reference if pipeline_id is specified,
  otherwise the default shared target reference.

  Args:
    target_name_or_id: str, target full name or ID.
    project: str,project number or ID.
    location_id: str, region ID.
    pipeline_id: str, pipeline ID.

  Returns:
    Target reference.
  """
  target_id = TargetId(target_name_or_id)
  if pipeline_id:
    return resources.REGISTRY.Parse(
        None,
        collection=_LESS_SHARED_TARGET_COLLECTION,
        params={
            'projectsId': project,
            'locationsId': location_id,
            'deliveryPipelinesId': pipeline_id,
            'targetsId': target_id,
        })

  return resources.REGISTRY.Parse(
      None,
      collection=_SHARED_TARGET_COLLECTION,
      params={
          'projectsId': project,
          'locationsId': location_id,
          'targetsId': target_id,
      })


def GetTarget(target_ref):
  """Gets the target message base on the type of target reference.

  Args:
    target_ref: protorpc.messages.Message, protorpc.messages.Message, target
      reference.

  Returns:
    Target message.
  Raises:
    Exceptions raised by TargetsClient's get functions
  """
  func = target.TargetsClient().Get
  if target_ref.AsDict().get('deliveryPipelinesId'):
    func = target.TargetsClient().GetLessShared

  try:
    target_obj = func(target_ref.RelativeName())
  except apitools_exceptions.HttpError as error:
    raise calliope_exceptions.HttpException(error)

  return target_obj


def PatchTarget(target_obj):
  """Patches a target resource.

  The target could be either shared target or less shared target.

  Args:
      target_obj: apitools.base.protorpclite.messages.Message, target message.

  Returns:
      The operation message.
  """
  func = target.TargetsClient().Patch
  if 'deliveryPipelines/' in target_obj.name:
    func = target.TargetsClient().PatchLessShared

  return func(target_obj)


def DeleteTarget(name):
  """Deletes a target resource.

  Args:
    name: str, target name.

  Returns:
    The operation message.
  """
  func = target.TargetsClient().Delete
  if 'deliveryPipelines/' in name:
    func = target.TargetsClient().DeleteLessShared

  return func(name)


def ListTarget(parent_name):
  """List target resources.

  Args:
    parent_name: str, the name of the collection that owns the targets.

  Returns:
    List of targets returns from target list API call.
  """
  func = target.TargetsClient().List
  if 'deliveryPipelines/' in parent_name:
    func = target.TargetsClient().ListLessShared

  return func(parent_name)
