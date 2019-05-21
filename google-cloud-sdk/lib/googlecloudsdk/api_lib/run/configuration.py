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
"""Wraps a Cloud Run Configuration message, making fields more convenient."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.run import k8s_object


# Annotation for the user-specified image.
USER_IMAGE_ANNOTATION = 'client.knative.dev/user-image'


class Configuration(k8s_object.KubernetesObject):
  """Wraps a Cloud Run Configuration message, making fields more convenient.

  Setting properties on a Configuration (where possible) writes through to the
  nested Kubernetes-style fields.
  """
  API_CATEGORY = 'serving.knative.dev'
  KIND = 'Configuration'

  @property
  def image(self):
    """URL to container."""
    return self._m.spec.revisionTemplate.spec.container.image

  @image.setter
  def image(self, value):
    self._m.spec.revisionTemplate.spec.container.image = value

  def _EnsureResources(self):
    limits_cls = self._messages.ResourceRequirements.LimitsValue
    if self.container.resources is not None:
      if self.container.resources.limits is None:
        self.container.resources.limits = k8s_object.InitializedInstance(
            limits_cls)
        # If we still have the old field set, move it over to the new.
        # But if we had both fields, don't bother changing the limits field.
        if self.container.resources.limitsInMap is not None:
          for item in self.container.resources.limitsInMap.additionalProperties:
            self.container.resources.limits.additionalProperties.append(
                limits_cls.AdditionalProperty(
                    key=item.key,
                    value=item.value.string))
    else:
      self.container.resources = k8s_object.InitializedInstance(
          self._messages.ResourceRequirements)
    # These fields are in the schema due to an error in interperetation of the
    # Knative spec. We're removing them, so never send any contents for them.
    self.container.resources.limitsInMap = None
    self.container.resources.requestsInMap = None

  def _EnsureRevisionMeta(self):
    revision_meta = self.spec.revisionTemplate.metadata
    if revision_meta is None:
      revision_meta = self._messages.ObjectMeta()
      self.spec.revisionTemplate.metadata = revision_meta
    return revision_meta

  @property
  def revision_labels(self):
    revision_meta = self._EnsureRevisionMeta()
    if revision_meta.labels is None:
      revision_meta.labels = self._messages.ObjectMeta.LabelsValue()
    return k8s_object.ListAsDictionaryWrapper(
        revision_meta.labels.additionalProperties,
        self._messages.ObjectMeta.LabelsValue.AdditionalProperty,
        key_field='key',
        value_field='value',
        )

  @property
  def revision_annotations(self):
    revision_meta = revision_meta = self._EnsureRevisionMeta()
    return k8s_object.AnnotationsFromMetadata(self._messages, revision_meta)

  @property
  def container(self):
    """The container in the revisionTemplate."""
    return self.spec.revisionTemplate.spec.container

  @property
  def env_vars(self):
    """Returns a mutable, dict-like object to manage env vars.

    The returned object can be used like a dictionary, and any modifications to
    the returned object (i.e. setting and deleting keys) modify the underlying
    nested env vars fields.
    """
    return k8s_object.ListAsDictionaryWrapper(
        self.container.env, self._messages.EnvVar)

  @property
  def resource_limits(self):
    """The resource limits as a dictionary { resource name: limit}."""
    self._EnsureResources()
    return k8s_object.ListAsDictionaryWrapper(
        self.container.resources.limits.additionalProperties,
        self._messages.ResourceRequirements.LimitsValue.AdditionalProperty,
        key_field='key',
        value_field='value',
    )

  @property
  def deprecated_string_concurrency(self):
    """The string-enum concurrency model in the revisionTemplate.

    This is deprecated in favor of the numeric field containerConcurrency
    """
    return self.spec.revisionTemplate.spec.concurrencyModel

  @deprecated_string_concurrency.setter
  def deprecated_string_concurrency(self, value):
    self.spec.revisionTemplate.spec.concurrencyModel = value

  @property
  def concurrency(self):
    """The concurrency number in the revisionTemplate.

    0: Multiple concurrency, max unspecified.
    1: Single concurrency
    n>1: Allow n simultaneous requests per instance.
    """
    return self.spec.revisionTemplate.spec.containerConcurrency

  @concurrency.setter
  def concurrency(self, value):
    self.spec.revisionTemplate.spec.containerConcurrency = value

  @property
  def timeout(self):
    """The timeout number in the revisionTemplate.

    The lib can accept either a duration format like '1m20s' or integer like
    '80' to set the timeout. The returned object is an integer value, which
    assumes second the unit, e.g., 80.
    """
    return self.spec.revisionTemplate.spec.timeoutSeconds

  @timeout.setter
  def timeout(self, value):
    self.spec.revisionTemplate.spec.timeoutSeconds = value

  @property
  def service_account(self):
    """The service account in the revisionTemplate."""
    return self.spec.revisionTemplate.spec.serviceAccountName

  @service_account.setter
  def service_account(self, value):
    self.spec.revisionTemplate.spec.serviceAccountName = value

