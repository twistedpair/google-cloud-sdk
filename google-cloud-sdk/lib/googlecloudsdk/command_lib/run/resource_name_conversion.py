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
"""Utilities for converting resource names between OP and KRM styles."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.core import properties


kubernetes_ref = re.compile(
    r'namespaces/(?P<NAMESPACE>.*?)/services/(?P<SERVICE>.*)')


def K8sToOnePlatform(service_resource, region):
  """Convert the Kubernetes-style service resource to One Platform-style."""
  project = properties.VALUES.core.project.Get(required=True)
  parts = kubernetes_ref.match(service_resource.RelativeName())
  service = parts.group('SERVICE')
  return 'projects/{project}/locations/{location}/services/{service}'.format(
      project=project,
      location=region,
      service=service)


display_kinds_map = {
    'workerPools': 'WorkerPool',
}


def _GetKind(kind):
  if kind in display_kinds_map:
    return display_kinds_map[kind]
  return kind


one_platform_resource_ref = re.compile(
    r'projects/(?P<PROJECT>.*?)/locations/(?P<REGION>.*)/(?P<KIND>.*)/(?P<NAME>.*)'
)


def GetInfoFromFullName(full_name):
  """Extracts project, region, resource kind, and name from One Platform-style name."""
  parts = one_platform_resource_ref.match(full_name)
  return (
      parts.group('PROJECT'),
      parts.group('REGION'),
      _GetKind(parts.group('KIND')),
      parts.group('NAME'),
  )


one_platform_child_resource_ref = re.compile(
    r'projects/(?P<PROJECT>.*?)/locations/(?P<REGION>.*)/(?P<PARENT_KIND>.*)/(?P<PARENT_NAME>.*)/(?P<KIND>.*)/(?P<NAME>.*)'
)


def GetInfoFromFullChildName(full_name):
  """Extracts project, region, resource kind, and name from One Platform-style name."""
  parts = one_platform_child_resource_ref.match(full_name)
  return (
      parts.group('PROJECT'),
      parts.group('REGION'),
      parts.group('PARENT_KIND'),
      parts.group('PARENT_NAME'),
      _GetKind(parts.group('KIND')),
      parts.group('NAME'),
  )


def GetNameFromFullChildName(full_name):
  """Extracts name from One Platform-style name."""
  *_, name = GetInfoFromFullChildName(full_name)
  return name
