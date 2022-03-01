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
"""Utils for running gcloud command and kubectl command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json

from googlecloudsdk.command_lib.anthos.config.sync.common import exceptions
from googlecloudsdk.command_lib.anthos.config.sync.common import utils
from googlecloudsdk.core import log


def ListResources(project, name, namespace, repo_cluster, membership):
  """List managed resources.

  Args:
    project: The project id the repo is from.
    name: The name of the corresponding ResourceGroup CR.
    namespace: The namespace of the corresponding ResourceGroup CR.
    repo_cluster: The cluster that the repo is synced to.
    membership: membership name that the repo should be from.

  Returns:
    List of raw ResourceGroup dicts

  """
  if membership and repo_cluster:
    raise exceptions.ConfigSyncError(
        'only one of --membership and --cluster may be specified.')

  resource_groups = []
  # Get ResourceGroups from the Config Controller cluster
  if not membership:  # exclude CC clusters if membership option is provided
    cc_rg = _GetResourceGroupsFromConfigController(
        project, name, namespace, repo_cluster)
    resource_groups.extend(cc_rg)

  # Get ResourceGroups from memberships
  member_rg = _GetResourceGroupsFromMemberships(
      project, name, namespace, repo_cluster, membership)
  resource_groups.extend(member_rg)
  # TODO(b/216846414): Implement parsing of ResourceGroup to proper output type
  return resource_groups


def _GetResourceGroupsFromConfigController(
    project, name, namespace, repo_cluster):
  """List all ResourceGroup CRs from Config Controller clusters.

  Args:
    project: The project id the repo is from.
    name: The name of the corresponding ResourceGroup CR.
    namespace: The namespace of the corresponding ResourceGroup CR.
    repo_cluster: The cluster that the repo is synced to.

  Returns:
    List of raw ResourceGroup dicts

  """
  clusters = []
  resource_groups = []
  try:
    # TODO(b/218518163): support resources applied by kpt live apply
    clusters = utils.ListConfigControllerClusters(project)
  except exceptions.ConfigSyncError as err:
    log.error(err)
  if clusters:
    for cluster in clusters:
      if repo_cluster and repo_cluster != cluster[0]:
        continue
      try:
        utils.KubeconfigForCluster(project, cluster[1], cluster[0])
        cc_rg = _GetResourceGroups(cluster[0], 'Config Controller', name,
                                   namespace)
        if cc_rg:
          resource_groups.extend(cc_rg)
      except exceptions.ConfigSyncError as err:
        log.error(err)
  return resource_groups


def _GetResourceGroupsFromMemberships(
    project, name, namespace, repo_cluster, membership):
  """List all ResourceGroup CRs from the provided membership cluster.

  Args:
    project: The project id the repo is from.
    name: The name of the corresponding ResourceGroup CR.
    namespace: The namespace of the corresponding ResourceGroup CR.
    repo_cluster: The cluster that the repo is synced to.
    membership: membership name that the repo should be from.

  Returns:
    List of raw ResourceGroup dicts

  """
  resource_groups = []
  try:
    memberships = utils.ListMemberships(project)
  except exceptions.ConfigSyncError as err:
    raise err
  for member in memberships:
    if membership and not utils.MembershipMatched(member, membership):
      continue
    if repo_cluster and repo_cluster != member:
      continue
    try:
      utils.KubeconfigForMembership(project, member)
      member_rg = _GetResourceGroups(member, 'Membership', name, namespace)
      if member_rg:
        resource_groups.extend(member_rg)
    except exceptions.ConfigSyncError as err:
      log.error(err)
  return resource_groups


def _GetResourceGroups(cluster_name, cluster_type, name, namespace):
  """List all the ResourceGroup CRs from the given cluster.

  Args:
    cluster_name: The membership name or cluster name of the current cluster.
    cluster_type: The type of the current cluster. It is either a Fleet-cluster
      or a Config-controller cluster.
    name: The name of the desired ResourceGroup.
    namespace: The namespace of the desired ResourceGroup.

  Returns:
    List of raw ResourceGroup dicts

  Raises:
    Error: errors that happen when listing the CRs from the cluster.
  """
  utils.GetConfigManagement(cluster_name, cluster_type)
  if not namespace:
    params = ['--all-namespaces']
  else:
    params = ['-n', namespace]
  repos, err = utils.RunKubectl(
      ['get', 'resourcegroup.kpt.dev', '-o', 'json'] + params)
  if err:
    raise exceptions.ConfigSyncError(
        'Error getting ResourceGroup custom resources for cluster {}: {}'
        .format(cluster_name, err))

  if not repos:
    return []
  obj = json.loads(repos)
  if 'items' not in obj or not obj['items']:
    return []

  resource_groups = []
  for item in obj['items']:
    _, nm = utils.GetObjectKey(item)
    if name and nm != name:
      continue
    resource_groups.append(item)

  return resource_groups
