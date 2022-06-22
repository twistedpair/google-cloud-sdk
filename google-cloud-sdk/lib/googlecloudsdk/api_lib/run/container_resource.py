# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Wraps a resource message with a container with convenience methods."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
from googlecloudsdk.api_lib.run import k8s_object

# Annotation for the user-specified image.
USER_IMAGE_ANNOTATION = k8s_object.CLIENT_GROUP + '/user-image'
CLOUDSQL_ANNOTATION = k8s_object.RUN_GROUP + '/cloudsql-instances'
VPC_ACCESS_ANNOTATION = 'run.googleapis.com/vpc-access-connector'
SANDBOX_ANNOTATION = 'run.googleapis.com/execution-environment'
CMEK_KEY_ANNOTATION = 'run.googleapis.com/encryption-key'
POST_CMEK_KEY_REVOCATION_ACTION_TYPE_ANNOTATION = 'run.googleapis.com/post-key-revocation-action-type'
ENCRYPTION_KEY_SHUTDOWN_HOURS_ANNOTATION = 'run.googleapis.com/encryption-key-shutdown-hours'
SECRETS_ANNOTATION = 'run.googleapis.com/secrets'
CPU_THROTTLE_ANNOTATION = 'run.googleapis.com/cpu-throttling'
COLD_START_BOOST_ANNOTATION = 'run.googleapis.com/startup-cpu-boost'

EGRESS_SETTINGS_ANNOTATION = 'run.googleapis.com/vpc-access-egress'
EGRESS_SETTINGS_ALL = 'all'
EGRESS_SETTINGS_ALL_TRAFFIC = 'all-traffic'
EGRESS_SETTINGS_PRIVATE_RANGES_ONLY = 'private-ranges-only'


class ContainerResource(k8s_object.KubernetesObject):
  """Wraps a resource message with a container, making fields more convenient.

  Provides convience fields for Cloud Run resources that contain a container.
  These resources also typically have other overlapping fields such as volumes
  which are also handled by this wrapper.
  """

  @property
  def env_vars(self):
    """Returns a mutable, dict-like object to manage env vars.

    The returned object can be used like a dictionary, and any modifications to
    the returned object (i.e. setting and deleting keys) modify the underlying
    nested env vars fields.
    """
    if self.container:
      return EnvVarsAsDictionaryWrapper(self.container.env,
                                        self._messages.EnvVar)

  @property
  def image(self):
    """URL to container."""
    return self.container.image

  @image.setter
  def image(self, value):
    self.container.image = value

  def UserImage(self, service_user_image=None):
    """Human-readable "what's deployed".

    Sometimes references a client.knative.dev/user-image annotation on the
    revision or service to determine what the user intended to deploy. In that
    case, we can display that, and show the user the hash prefix as a note that
    it's at that specific hash.

    Arguments:
      service_user_image: Optional[str], the contents of the user image annot on
        the service.

    Returns:
      a string representing the user deployment intent.
    """
    if not self.image:
      return None
    if '@' not in self.image:
      return self.image
    user_image = (
        self.annotations.get(USER_IMAGE_ANNOTATION) or service_user_image)
    if not user_image:
      return self.image
    # The image should  be in the format base@sha256:hashhashhash
    base, h = self.image.split('@')
    if ':' in h:
      _, h = h.split(':')
    if not user_image.startswith(base):
      # The user-image is out of date.
      return self.image
    if len(h) > 8:
      h = h[:8] + '...'
    return user_image + ' at ' + h

  def _EnsureResources(self):
    limits_cls = self._messages.ResourceRequirements.LimitsValue
    if self.container.resources is not None:
      if self.container.resources.limits is None:
        self.container.resources.limits = k8s_object.InitializedInstance(
            limits_cls)
    else:
      self.container.resources = k8s_object.InitializedInstance(
          self._messages.ResourceRequirements)
    # These fields are in the schema due to an error in interperetation of the
    # Knative spec. We're removing them, so never send any contents for them.
    try:
      self.container.resources.limitsInMap = None
      self.container.resources.requestsInMap = None
    except AttributeError:
      # The fields only exist in the v1alpha1 spec, if we're working with a
      # different version, this is safe to ignore
      pass

  @property
  def container(self):
    """The container in the revisionTemplate."""
    if hasattr(self.spec, 'container'):
      if self.spec.container and (hasattr(self.spec, 'containers') and
                                  self.spec.containers):
        raise ValueError(
            'Revision can have only one of `container` or `containers` set')
      elif self.spec.container:
        return self.spec.container
    if hasattr(self.spec, 'containers') and self.spec.containers:
      if self.spec.containers[0] is None or len(self.spec.containers) != 1:
        raise ValueError('List of containers must contain exactly one element')
      return self.spec.containers[0]
    else:
      raise ValueError('Either `container` or `containers` must be set')

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
  def volumes(self):
    """Returns a dict-like object to manage volumes.

    There are additional properties on the object (e.g. `.secrets`) that can
    be used to access a mutable, dict-like object for managing volumes of a
    given type. Any modifications to the returned object for these properties
    (i.e. setting and deleting keys) modify the underlying nested volumes.
    """
    return VolumesAsDictionaryWrapper(self.spec.volumes, self._messages.Volume)

  @property
  def volume_mounts(self):
    """Returns a mutable, dict-like object to manage volume mounts.

    The returned object can be used like a dictionary, and any modifications to
    the returned object (i.e. setting and deleting keys) modify the underlying
    nested volume mounts. There are additional properties on the object
    (e.g. `.secrets` that can be used to access a mutable dict-like object for
    a volume mounts that mount volumes of a given type.
    """
    if self.container:
      return VolumeMountsAsDictionaryWrapper(self.volumes,
                                             self.container.volumeMounts,
                                             self._messages.VolumeMount)

  def MountedVolumeJoin(self, subgroup=None):
    vols = self.volumes
    mounts = self.volume_mounts
    if subgroup:
      vols = getattr(vols, subgroup)
      mounts = getattr(mounts, subgroup)
    return {path: vols.get(vol) for path, vol in mounts.items()}


class EnvVarsAsDictionaryWrapper(k8s_object.ListAsReadOnlyDictionaryWrapper):
  """Wraps a list of env vars in a dict-like object.

  Additionally provides properties to access env vars of specific type in a
  mutable dict-like object.
  """

  def __init__(self, env_vars_to_wrap, env_var_class):
    """Wraps a list of env vars in a dict-like object.

    Args:
      env_vars_to_wrap: list[EnvVar], list of env vars to treat as a dict.
      env_var_class: type of the underlying EnvVar objects.
    """
    super(EnvVarsAsDictionaryWrapper, self).__init__(env_vars_to_wrap)
    self._env_vars = env_vars_to_wrap
    self._env_var_class = env_var_class

  @property
  def literals(self):
    """Mutable dict-like object for env vars with a string literal.

    Note that if neither value nor valueFrom is specified, the list entry will
    be treated as a literal empty string.

    Returns:
      A mutable, dict-like object for managing string literal env vars.
    """
    return k8s_object.ListAsDictionaryWrapper(
        self._env_vars,
        self._env_var_class,
        filter_func=lambda env_var: env_var.valueFrom is None)

  @property
  def secrets(self):
    """Mutable dict-like object for vars with a secret source type."""

    def _FilterSecretEnvVars(env_var):
      return (env_var.valueFrom is not None and
              env_var.valueFrom.secretKeyRef is not None)

    return k8s_object.ListAsDictionaryWrapper(
        self._env_vars,
        self._env_var_class,
        value_field='valueFrom',
        filter_func=_FilterSecretEnvVars)

  @property
  def config_maps(self):
    """Mutable dict-like object for vars with a config map source type."""

    def _FilterConfigMapEnvVars(env_var):
      return (env_var.valueFrom is not None and
              env_var.valueFrom.configMapKeyRef is not None)

    return k8s_object.ListAsDictionaryWrapper(
        self._env_vars,
        self._env_var_class,
        value_field='valueFrom',
        filter_func=_FilterConfigMapEnvVars)


class VolumesAsDictionaryWrapper(k8s_object.ListAsReadOnlyDictionaryWrapper):
  """Wraps a list of volumes in a dict-like object.

  Additionally provides properties to access volumes of specific type in a
  mutable dict-like object.
  """

  def __init__(self, volumes_to_wrap, volume_class):
    """Wraps a list of volumes in a dict-like object.

    Args:
      volumes_to_wrap: list[Volume], list of volumes to treat as a dict.
      volume_class: type of the underlying Volume objects.
    """
    super(VolumesAsDictionaryWrapper, self).__init__(volumes_to_wrap)
    self._volumes = volumes_to_wrap
    self._volume_class = volume_class

  @property
  def secrets(self):
    """Mutable dict-like object for volumes with a secret source type."""
    return k8s_object.ListAsDictionaryWrapper(
        self._volumes,
        self._volume_class,
        value_field='secret',
        filter_func=lambda volume: volume.secret is not None)

  @property
  def config_maps(self):
    """Mutable dict-like object for volumes with a config map source type."""
    return k8s_object.ListAsDictionaryWrapper(
        self._volumes,
        self._volume_class,
        value_field='configMap',
        filter_func=lambda volume: volume.configMap is not None)


class VolumeMountsAsDictionaryWrapper(k8s_object.ListAsDictionaryWrapper):
  """Wraps a list of volume mounts in a mutable dict-like object.

  Additionally provides properties to access mounts that are mounting volumes
  of specific type in a mutable dict-like object.
  """

  def __init__(self, volumes, mounts_to_wrap, mount_class):
    """Wraps a list of volume mounts in a mutable dict-like object.

    Forces readOnly=True on creation of new volume mounts.

    Args:
      volumes: associated VolumesAsDictionaryWrapper obj
      mounts_to_wrap: list[VolumeMount], list of mounts to treat as a dict.
      mount_class: type of the underlying VolumeMount objects.
    """
    super(VolumeMountsAsDictionaryWrapper, self).__init__(
        mounts_to_wrap,
        functools.partial(mount_class, readOnly=True),
        key_field='mountPath',
        value_field='name')
    self._volumes = volumes

  @property
  def secrets(self):
    """Mutable dict-like object for mounts whose volumes have a secret source type."""
    return k8s_object.ListAsDictionaryWrapper(
        self._m,
        self._item_class,
        key_field=self._key_field,
        value_field=self._value_field,
        filter_func=lambda mount: mount.name in self._volumes.secrets)

  @property
  def config_maps(self):
    """Mutable dict-like object for mounts whose volumes have a config map source type."""
    return k8s_object.ListAsDictionaryWrapper(
        self._m,
        self._item_class,
        key_field=self._key_field,
        value_field=self._value_field,
        filter_func=lambda mount: mount.name in self._volumes.config_maps)
