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
"""Wraps a Cloud Run Execution message with convenience methods."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum
from googlecloudsdk.api_lib.run import container_resource
from googlecloudsdk.api_lib.run import k8s_object

AUTHOR_ANNOTATION = k8s_object.RUN_GROUP + '/creator'

STARTED_CONDITION = 'Started'
COMPLETED_CONDITION = 'Completed'

JOB_LABEL = 'run.googleapis.com/job'


class RestartPolicy(enum.Enum):
  NEVER = 'Never'
  ON_FAILURE = 'OnFailure'


class Execution(k8s_object.KubernetesObject):
  """Wraps a Cloud Run Execution message, making fields more convenient."""

  API_CATEGORY = 'run.googleapis.com'
  KIND = 'Execution'
  READY_CONDITION = COMPLETED_CONDITION
  TERMINAL_CONDITIONS = frozenset({STARTED_CONDITION, READY_CONDITION})

  class TaskTemplateSpec(container_resource.ContainerResource):
    """Wrapper class for Execution subfield TaskTemplateSpec."""

    KIND = 'TaskTemplateSpec'

    @classmethod
    def SpecAndParitialMetadataOnly(cls, execution):
      """Special wrapper for spec only that also covers partial metadata.

      For a message type without its own metadata, like TaskTemplateSpec,
      metadata fields should either raise AttributeErrors or refer to the
      metadata of a different message depending on use case. This method handles
      the annotations and labels of metadata by referencing the parent
      execution's annotations and labels.
      All other metadata fields will fall through to k8s_object which will
      lead to AttributeErrors.

      Args:
        execution: The parent execution for this TaskTemplateSpec

      Returns:
        A new k8s_object to wrap the TaskTemplateSpec with only the spec
        fields and the metadata annotations and labels.
      """
      spec_wrapper = super(Execution.TaskTemplateSpec,
                           cls).SpecOnly(execution.spec.template.spec,
                                         execution.MessagesModule())
      # pylint: disable=protected-access
      spec_wrapper._annotations = execution.annotations
      spec_wrapper._labels = execution.labels
      return spec_wrapper

    @property
    def annotations(self):
      """Override to return the parent execution's annotations."""
      try:
        return self._annotations
      except AttributeError:
        raise ValueError(
            'Execution templates do not have their own annotations. Initialize '
            'the wrapper with SpecAndAnnotationsOnly to be able to use '
            'annotations.')

    @property
    def labels(self):
      """Override to return the parent execution's labels."""
      try:
        return self._labels
      except AttributeError:
        raise ValueError(
            'Execution templates do not have their own labels. Initialize '
            'the wrapper with SpecAndAnnotationsOnly to be able to use '
            'labels.'
        )

    @property
    def service_account(self):
      """The service account to use as the container identity."""
      return self.spec.serviceAccountName

    @service_account.setter
    def service_account(self, value):
      self.spec.serviceAccountName = value

    def _EnsureNodeSelector(self):
      if self.spec.nodeSelector is None:
        self.spec.nodeSelector = k8s_object.InitializedInstance(
            self._messages.TaskSpec.NodeSelectorValue
        )

    @property
    def node_selector(self):
      """The node selector as a dictionary { accelerator_type: value}."""
      self._EnsureNodeSelector()
      return k8s_object.KeyValueListAsDictionaryWrapper(
          self.spec.nodeSelector.additionalProperties,
          self._messages.TaskSpec.NodeSelectorValue.AdditionalProperty,
          key_field='key',
          value_field='value',
      )

  @property
  def template(self):
    return Execution.TaskTemplateSpec.SpecAndParitialMetadataOnly(self)

  @property
  def author(self):
    return self.annotations.get(AUTHOR_ANNOTATION)

  @property
  def image(self):
    return self.template.image

  @image.setter
  def image(self, value):
    self.template.image = value

  @property
  def parallelism(self):
    return self.spec.parallelism

  @parallelism.setter
  def parallelism(self, value):
    self.spec.parallelism = value

  @property
  def task_count(self):
    return self.spec.taskCount

  @task_count.setter
  def task_count(self, value):
    self.spec.taskCount = value

  @property
  def started_condition(self):
    if self.conditions and STARTED_CONDITION in self.conditions:
      return self.conditions[STARTED_CONDITION]

  @property
  def job_name(self):
    return self.labels[JOB_LABEL]
