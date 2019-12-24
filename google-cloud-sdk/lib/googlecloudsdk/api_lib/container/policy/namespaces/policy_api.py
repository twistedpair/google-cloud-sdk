# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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

"""Useful commands for interacting with the Kubernetes Policy API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager

from googlecloudsdk.api_lib.container.policy.namespaces import policy_util


def Create(project_id, kubernetes_name):
  client = policy_util.GetClient()
  messages = policy_util.GetMessages()
  return client.projects_namespaces.Create(
      messages.Namespace(
          parent=project_id,
          kubernetesName=kubernetes_name,
      ))


def Delete(namespace_name):
  client = policy_util.GetClient()
  messages = policy_util.GetMessages()
  return client.projects_namespaces.Delete(
      messages.KubernetespolicyProjectsNamespacesDeleteRequest(
          name=namespace_name,
      ))


def Get(namespace_name):
  client = policy_util.GetClient()
  messages = policy_util.GetMessages()
  return client.projects_namespaces.Get(
      messages.KubernetespolicyProjectsNamespacesGetRequest(
          name=namespace_name))


def List(project_id):  # pylint: disable=redefined-builtin
  client = policy_util.GetClient()
  messages = policy_util.GetMessages()

  return list_pager.YieldFromList(
      client.projects_namespaces,
      messages.KubernetespolicyProjectsNamespacesListRequest(
          parent=project_id),
      batch_size=1,  # There is at most one result.
      field='resources',
      batch_size_attribute='pageSize')
