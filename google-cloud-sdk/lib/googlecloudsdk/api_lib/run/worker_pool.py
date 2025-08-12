# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Wraps a Serverless WorkerPool message, making fields more convenient."""

from __future__ import absolute_import
from __future__ import annotations
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.run import instance_split
from googlecloudsdk.api_lib.run import k8s_object
from googlecloudsdk.api_lib.run import revision


WORKER_POOL_MIN_SCALE_ANNOTATION = 'run.googleapis.com/minScale'
WORKER_POOL_MAX_SCALE_ANNOTATION = 'run.googleapis.com/maxScale'
MANUAL_INSTANCE_COUNT_ANNOTATION = 'run.googleapis.com/manualInstanceCount'
WORKER_POOL_SCALING_MODE_ANNOTATION = 'run.googleapis.com/scalingMode'
OPERATION_ID_ANNOTATION = 'run.googleapis.com/operation-id'


class WorkerPool(k8s_object.KubernetesObject):
  """Wraps a Serverless WorkerPool message, making fields more convenient.

  Setting properties on a WorkerPool (where possible) writes through to the
  nested Kubernetes-style fields.
  """

  API_CATEGORY = 'run.googleapis.com'
  KIND = 'WorkerPool'

  @property
  def template(self):
    if not self.spec.template.metadata:
      self.spec.template.metadata = k8s_object.MakeMeta(self.MessagesModule())
    ret = revision.Revision.Template(self.spec.template, self.MessagesModule())
    return ret

  @property
  def template_annotations(self):
    self.AssertFullObject()
    return k8s_object.AnnotationsFromMetadata(
        self._messages, self.template.metadata
    )

  @property
  def revision_labels(self):
    return self.template.labels

  @property
  def revision_name(self):
    return self.template.name

  @revision_name.setter
  def revision_name(self, value):
    self.template.name = value

  @property
  def latest_created_revision(self):
    return self.status.latestCreatedRevisionName

  @property
  def latest_ready_revision(self):
    return self.status.latestReadyRevisionName

  @property
  def serving_revisions(self):
    return [i.revisionName for i in self.status.instanceSplits if i.percent]

  def _ShouldIncludeInLatestPercent(self, split):
    """Returns True if the split's percent is part of the latest percent."""
    is_latest_by_name = (
        self.status.latestReadyRevisionName
        and split.revisionName == self.status.latestReadyRevisionName
    )
    return split.latestRevision or is_latest_by_name

  @property
  def latest_percent_instance_split(self):
    """The percent of instance split assigned tothe latest ready revision."""
    return sum(
        split.percent or 0
        for split in self.status.instanceSplits
        if self._ShouldIncludeInLatestPercent(split)
    )

  def ReadySymbolAndColor(self):
    if (
        self.ready is False  # pylint: disable=g-bool-id-comparison
        and self.latest_ready_revision
        and self.latest_created_revision != self.latest_ready_revision
    ):
      return '!', 'yellow'
    return super(WorkerPool, self).ReadySymbolAndColor()

  @property
  def last_modifier(self):
    return self.annotations.get('serving.knative.dev/lastModifier')

  @property
  def spec_split(self):
    self.AssertFullObject()
    return instance_split.InstanceSplits(
        self._messages, self.spec.instanceSplits
    )

  @property
  def status_split(self):
    self.AssertFullObject()
    return instance_split.InstanceSplits(
        self._messages,
        [] if self.status is None else self.status.instanceSplits,
    )

  @property
  def image(self):
    return self.template.image

  @image.setter
  def image(self, value):
    self.template.image = value

  @property
  def operation_id(self):
    return self.annotations.get(OPERATION_ID_ANNOTATION)

  @operation_id.setter
  def operation_id(self, value):
    self.annotations[OPERATION_ID_ANNOTATION] = value

  @property
  def description(self):
    return self.annotations.get(k8s_object.DESCRIPTION_ANNOTATION)

  @description.setter
  def description(self, value):
    self.annotations['run.googleapis.com/description'] = value
