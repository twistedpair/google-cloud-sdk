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

import subprocess

import six


class Minikube(object):
  """Start and stop a minikube cluster."""

  def __init__(self, cluster_name):
    self._cluster_name = cluster_name

  def __enter__(self):
    _StartCluster(self._cluster_name)

  def __exit__(self, exc_type, exc_value, tb):
    _DeleteMinikube(self._cluster_name)


def _StartCluster(cluster_name):
  """Start a minikube cluster."""
  if not _IsClusterUp(cluster_name):
    cmd = ['minikube', 'start', '-p', cluster_name, '--keep-context']
    subprocess.check_call(cmd)


def _IsClusterUp(cluster_name):
  """Check if a minikube cluster is running."""
  cmd = ['minikube', 'status', '-p', cluster_name]
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
  stdout, _ = p.communicate()
  lines = six.text_type(stdout).strip().splitlines()
  status = dict(line.split(':', 1) for line in lines)
  return 'host' in status and status['host'].strip() == 'Running'


def _DeleteMinikube(cluster_name):
  """Delete a minikube cluster."""
  cmd = ['minikube', 'delete', '-p', cluster_name]
  subprocess.check_call(cmd)
