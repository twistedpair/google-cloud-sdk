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
"""Library for generating the files for local development environment."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os.path
import subprocess
from googlecloudsdk.core import config
from googlecloudsdk.core.util import files as file_utils
import six


def _FindMinikubeComponent():
  """Find the path to the minikube component."""
  if config.Paths().sdk_root:
    return os.path.join(config.Paths().sdk_root, 'bin', 'minikube')
  return None


def _FindMinikube():
  """Find the path to the minikube executable."""
  minikube = (
      file_utils.FindExecutableOnPath('minikube') or _FindMinikubeComponent())
  if not minikube:
    raise EnvironmentError('Unable to locate minikube.')
  return minikube


class MinikubeCluster(object):
  """A cluster on minikube.

  Attributes:
    context_name: Kubernetes context name.
  """

  def __init__(self, profile):
    """Initialize MinkubeCluster with profile name.

    Args:
      profile: Name of minikube profile.
    """
    self.context_name = profile


class Minikube(object):
  """Start and stop a minikube cluster."""

  def __init__(self, cluster_name, delete_cluster=True, vm_driver='kvm2'):
    self._cluster_name = cluster_name
    self._delete_cluster = delete_cluster
    self._vm_driver = vm_driver

  def __enter__(self):
    _StartCluster(self._cluster_name, self._vm_driver)
    return MinikubeCluster(self._cluster_name)

  def __exit__(self, exc_type, exc_value, tb):
    if self._delete_cluster:
      _DeleteMinikube(self._cluster_name)


def _StartCluster(cluster_name, vm_driver):
  """Start a minikube cluster."""
  if not _IsClusterUp(cluster_name):
    cmd = [
        _FindMinikube(), 'start', '-p', cluster_name, '--keep-context',
        '--vm-driver=' + vm_driver
    ]
    subprocess.check_call(cmd)


def _IsClusterUp(cluster_name):
  """Check if a minikube cluster is running."""
  cmd = [_FindMinikube(), 'status', '-p', cluster_name]
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
  stdout, _ = p.communicate()
  lines = six.ensure_text(stdout).strip().splitlines()
  status = dict(line.split(':', 1) for line in lines)
  return 'host' in status and status['host'].strip() == 'Running'


def _DeleteMinikube(cluster_name):
  """Delete a minikube cluster."""
  cmd = [_FindMinikube(), 'delete', '-p', cluster_name]
  subprocess.check_call(cmd)


class ExternalCluster(object):
  """A external kubernetes cluster.

  Attributes:
    context_name: Kubernetes context name.
  """

  def __init__(self, cluster_name):
    """Initialize ExternalCluster with profile name.

    Args:
      cluster_name: Name of the cluster.
    """
    self.context_name = cluster_name


class ExternalClusterContext(object):
  """Do nothing context manager for external clusters."""

  def __init__(self, kube_context):
    self._kube_context = kube_context

  def __enter__(self):
    return ExternalCluster(self._kube_context)

  def __exit__(self, exc_type, exc_value, tb):
    pass
