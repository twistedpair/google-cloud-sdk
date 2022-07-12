# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Utilities for the cloud deploy delivery pipeline resource."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.clouddeploy import delivery_pipeline
from googlecloudsdk.command_lib.deploy import exceptions as cd_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources

_PIPELINES_WITH_GIVEN_TARGET_FILTER_TEMPLATE = (
    'serialPipeline.stages.targetId:"{}"')


def ListDeliveryPipelinesWithTarget(target_ref, location_ref):
  """Lists the delivery pipelines associated with the specified target.

  The returned list is sorted by the delivery pipeline's create time.
  Args:
    target_ref: protorpc.messages.Message, target object.
    location_ref: protorpc.messages.Message, location object.

  Returns:
    a sorted list of delivery pipelines.
  """
  filter_str = _PIPELINES_WITH_GIVEN_TARGET_FILTER_TEMPLATE.format(
      target_ref.Name())

  pipelines = delivery_pipeline.DeliveryPipelinesClient().List(
      location=location_ref.RelativeName(),
      filter_str=filter_str,
      page_size=0,
  )

  # ListDeliveryPipelines does not support orderBy=createTime field
  # so sort result to get the same result you would get by using
  # orderBy = 'createTime desc'
  return sorted(
      pipelines, key=lambda pipeline: pipeline.createTime, reverse=True)


def PipelineToPipelineRef(pipeline):
  pipeline_ref = resources.REGISTRY.ParseRelativeName(
      pipeline.name,
      collection='clouddeploy.projects.locations.deliveryPipelines')
  return pipeline_ref


def GetPipeline(pipeline_name):
  """Gets the delivery pipeline and returns the value of its suspended field.

  Args:
    pipeline_name: str, the canonical resource name of the delivery pipeline

  Returns:
    The pipeline object
  Raises:
    apitools.base.py.HttpError
  """
  try:
    pipeline_obj = delivery_pipeline.DeliveryPipelinesClient().Get(
        pipeline_name)
    return pipeline_obj
  except apitools_exceptions.HttpError as error:
    log.debug('Failed to get pipeline {}: {}'.format(pipeline_name,
                                                     error.content))
    log.status.Print('Unable to get delivery pipeline {}'.format(pipeline_name))
    raise error


def ThrowIfPipelineSuspended(pipeline_obj, suspended_pipeline_msg):
  """Checks if the delivery pipeline associated with the release is suspended.

  Args:
    pipeline_obj: protorpc.messages.Message, delivery pipeline object.
    suspended_pipeline_msg: str, error msg to show the user if the pipeline is
      suspended.

  Raises:
    googlecloudsdk.command_lib.deploy.PipelineSuspendedError if the pipeline is
    suspended
  """
  if pipeline_obj.suspended:
    raise cd_exceptions.PipelineSuspendedError(
        pipeline_name=pipeline_obj.name,
        failed_activity_msg=suspended_pipeline_msg)
