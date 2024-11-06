# -*- coding: utf-8 -*- #
# Copyright 2018 Google LLC. All Rights Reserved.
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
"""Wraps a Serverless Service message, making fields more convenient."""

from __future__ import absolute_import
from __future__ import annotations
from __future__ import division
from __future__ import unicode_literals

import json
from typing import List

from googlecloudsdk.api_lib.run import k8s_object
from googlecloudsdk.api_lib.run import revision
from googlecloudsdk.api_lib.run import traffic

DEFAULT_BASE_IMAGE = 'gcr.io/buildpacks/google-22/run'
ENDPOINT_VISIBILITY = 'networking.knative.dev/visibility'
CLUSTER_LOCAL = 'cluster-local'

IAP_ANNOTATION = 'run.googleapis.com/iap-enabled'
INGRESS_ANNOTATION = 'run.googleapis.com/ingress'
INGRESS_STATUS_ANNOTATION = 'run.googleapis.com/ingress-status'
INGRESS_ALL = 'all'
INGRESS_INTERNAL = 'internal'
INGRESS_INTERNAL_AND_CLOUD_LOAD_BALANCING = 'internal-and-cloud-load-balancing'
SERVICE_MIN_SCALE_ANNOTATION = 'run.googleapis.com/minScale'
SERVICE_MAX_SCALE_ANNOTATION = 'run.googleapis.com/maxScale'
MANUAL_INSTANCE_COUNT_ANNOTATION = 'run.googleapis.com/manualInstanceCount'
SERVICE_MAX_SURGE_ANNOTATION = 'run.googleapis.com/max-surge'
SERVICE_MAX_UNAVAILABLE_ANNOTATION = 'run.googleapis.com/max-unavailable'
SERVICE_SCALING_MODE_ANNOTATION = 'run.googleapis.com/scalingMode'
OPERATION_ID_ANNOTATION = 'run.googleapis.com/operation-id'
RUN_FUNCTIONS_BUILD_SOURCE_LOCATION_ANNOTATION = (
    'run.googleapis.com/build-source-location'
)
RUN_FUNCTIONS_BUILD_FUNCTION_TARGET_ANNOTATION = (
    'run.googleapis.com/build-function-target'
)
RUN_FUNCTIONS_BUILD_IMAGE_URI_ANNOTATION = 'run.googleapis.com/build-image-uri'
RUN_FUNCTIONS_BUILD_ID_ANNOTATION = 'run.googleapis.com/build-id'
RUN_FUNCTIONS_BUILD_ENV_VARS_ANNOTATION = (
    'run.googleapis.com/build-environment-variables'
)
RUN_FUNCTIONS_BUILD_SOURCE_LOCATION_ANNOTATION = 'run.googleapis.com/build-source-location'
RUN_FUNCTIONS_BUILD_FUNCTION_TARGET_ANNOTATION = 'run.googleapis.com/build-function-target'
RUN_FUNCTIONS_BUILD_IMAGE_URI_ANNOTATION = 'run.googleapis.com/build-image-uri'
RUN_FUNCTIONS_BUILD_WORKER_POOL_ANNOTATION = (
    'run.googleapis.com/build-worker-pool'
)
RUN_FUNCTIONS_BUILD_SERVICE_ACCOUNT_ANNOTATION = (
    'run.googleapis.com/build-service-account'
)
RUN_FUNCTIONS_BUILD_NAME_ANNOTATION = 'run.googleapis.com/build-name'
RUN_FUNCTIONS_BUILD_BASE_IMAGE = 'run.googleapis.com/build-base-image'
RUN_FUNCTIONS_BUILD_ENABLE_AUTOMATIC_UPDATES = (
    'run.googleapis.com/build-enable-automatic-updates'
)
# TODO(b/365567914): Remove these annotations once the new ones are in use.
RUN_FUNCTIONS_SOURCE_LOCATION_ANNOTATION_DEPRECATED = (
    'run.googleapis.com/source-location'
)
RUN_FUNCTIONS_FUNCTION_TARGET_ANNOTATION_DEPRECATED = (
    'run.googleapis.com/function-target'
)
RUN_FUNCTIONS_IMAGE_URI_ANNOTATION_DEPRECATED = 'run.googleapis.com/image-uri'
RUN_FUNCTIONS_ENABLE_AUTOMATIC_UPDATES_DEPRECATED = (
    'run.googleapis.com/enable-automatic-updates'
)


class Service(k8s_object.KubernetesObject):
  """Wraps a Serverless Service message, making fields more convenient.

  Setting properties on a Service (where possible) writes through to the
  nested Kubernetes-style fields.
  """

  API_CATEGORY = 'serving.knative.dev'
  KIND = 'Service'

  @property
  def run_functions_annotations(self):
    return (
        self.annotations.get(RUN_FUNCTIONS_BUILD_SERVICE_ACCOUNT_ANNOTATION),
        self.annotations.get(RUN_FUNCTIONS_BUILD_WORKER_POOL_ANNOTATION),
        self.annotations.get(RUN_FUNCTIONS_BUILD_ENV_VARS_ANNOTATION),
    )

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
    return [t.revisionName for t in self.status.traffic if t.percent]

  def _ShouldIncludeInLatestPercent(self, target):
    """Returns True if the target's percent is part of the latest percent."""
    is_latest_by_name = (
        self.status.latestReadyRevisionName
        and target.revisionName == self.status.latestReadyRevisionName
    )
    return target.latestRevision or is_latest_by_name

  @property
  def latest_percent_traffic(self):
    """The percent of traffic the latest ready revision is serving."""
    return sum(
        target.percent or 0
        for target in self.status.traffic
        if self._ShouldIncludeInLatestPercent(target)
    )

  @property
  def latest_url(self):
    """A url at which we can reach the latest ready revision."""
    for target in self.status.traffic:
      if self._ShouldIncludeInLatestPercent(target) and target.url:
        return target.url
    return None

  @property
  def urls(self) -> List[str]:
    """List of the Service's URLs.

    Returns:
      A list of the URLs present in the Service's run.googleapis.com/urls
      annotation. If this annotation is missing an empty list is returned
      instead.
    """
    ann = self.annotations.get('run.googleapis.com/urls')
    if not ann:
      return []
    return json.loads(ann)

  @property
  def domain(self):
    urls = self.urls
    if urls:
      return urls[0]
    if self._m.status.url:
      return self._m.status.url
    try:
      return self._m.status.domain
    except AttributeError:
      # `domain` field only exists in v1alpha1 so this could be thrown if using
      # another api version
      return None

  @domain.setter
  def domain(self, domain):
    self._m.status.url = domain
    try:
      self._m.status.domain = domain
    except AttributeError:
      # `domain` field only exists in v1alpha1 so this could be thrown if using
      # another api version
      return None

  def ReadySymbolAndColor(self):
    if (
        self.ready is False  # pylint: disable=g-bool-id-comparison
        and self.latest_ready_revision
        and self.latest_created_revision != self.latest_ready_revision
    ):
      return '!', 'yellow'
    return super(Service, self).ReadySymbolAndColor()

  @property
  def last_modifier(self):
    return self.annotations.get('serving.knative.dev/lastModifier')

  @property
  def spec_traffic(self):
    self.AssertFullObject()
    return traffic.TrafficTargets(self._messages, self.spec.traffic)

  @property
  def status_traffic(self):
    self.AssertFullObject()
    return traffic.TrafficTargets(
        self._messages, [] if self.status is None else self.status.traffic
    )

  @property
  def vpc_connector(self):
    return self.annotations.get('run.googleapis.com/vpc-access-connector')

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

  @property
  def source_location(self):
    return self.annotations.get(
        RUN_FUNCTIONS_BUILD_SOURCE_LOCATION_ANNOTATION,
        self.annotations.get(
            RUN_FUNCTIONS_SOURCE_LOCATION_ANNOTATION_DEPRECATED
        ),
    )
