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
"""Bigtable app-profiles API helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.bigtable import util
from googlecloudsdk.calliope import exceptions


def Describe(app_profile_ref):
  """Describe an app profile.

  Args:
    app_profile_ref: A resource reference to the app profile to describe.

  Returns:
    App profile resource object.
  """
  client = util.GetAdminClient()
  msg = util.GetAdminMessages().BigtableadminProjectsInstancesAppProfilesGetRequest(
      name=app_profile_ref.RelativeName()
  )
  return client.projects_instances_appProfiles.Get(msg)


def List(instance_ref):
  """List app profiles.

  Args:
    instance_ref: A resource reference of the instance to list app profiles for.

  Returns:
    Generator of app profile resource objects.
  """
  client = util.GetAdminClient()
  msg = util.GetAdminMessages().BigtableadminProjectsInstancesAppProfilesListRequest(
      parent=instance_ref.RelativeName()
  )
  return list_pager.YieldFromList(
      client.projects_instances_appProfiles,
      msg,
      field='appProfiles',
      batch_size_attribute=None,
  )


def Delete(app_profile_ref, force=False):
  """Delete an app profile.

  Args:
    app_profile_ref: A resource reference to the app profile to delete.
    force: bool, Whether to ignore API warnings and delete forcibly.

  Returns:
    Empty response.
  """
  client = util.GetAdminClient()
  msg = util.GetAdminMessages().BigtableadminProjectsInstancesAppProfilesDeleteRequest(
      name=app_profile_ref.RelativeName(), ignoreWarnings=force
  )
  return client.projects_instances_appProfiles.Delete(msg)


def Create(
    app_profile_ref,
    cluster=None,
    description='',
    multi_cluster=False,
    restrict_to=None,
    failover_radius=None,
    transactional_writes=False,
    force=False,
    priority=None,
):
  """Create an app profile.

  Args:
    app_profile_ref: A resource reference of the new app profile.
    cluster: string, The cluster id for the new app profile to route to using
      single cluster routing.
    description: string, A description of the new app profile.
    multi_cluster: bool, Whether this app profile should route to multiple
      clusters, instead of single cluster.
    restrict_to: list[string] The list of cluster ids for the new app profile to
      route to using multi cluster routing.
    failover_radius: string, Restricts clusters that requests can fail over to
      by proximity with multi cluster routing.
    transactional_writes: bool, Whether this app profile has transactional
      writes enabled. This is only possible when using single cluster routing.
    force: bool, Whether to ignore API warnings and create forcibly.
    priority: string, The request priority of the new app profile.

  Raises:
    ConflictingArgumentsException:
        If both cluster and multi_cluster are present.
        If both multi_cluster and transactional_writes are present.
        If both cluster and restrict_to are present.
        If both cluster and failover_radius are present.
    OneOfArgumentsRequiredException: If neither cluster or multi_cluster are
        present.

  Returns:
    Created app profile resource object.
  """
  if multi_cluster and cluster:
    raise exceptions.ConflictingArgumentsException('--route-to', '--route-any')
  if multi_cluster and transactional_writes:
    raise exceptions.ConflictingArgumentsException(
        '--route-any', '--transactional-writes'
    )
  if cluster and restrict_to:
    raise exceptions.ConflictingArgumentsException(
        '--route-to', '--restrict-to'
    )
  if cluster and failover_radius:
    raise exceptions.ConflictingArgumentsException(
        '--route-to', '--failover-radius'
    )
  if not multi_cluster and not cluster:
    raise exceptions.OneOfArgumentsRequiredException(
        ['--route-to', '--route-any'],
        'Either --route-to or --route-any must be specified.',
    )

  client = util.GetAdminClient()
  msgs = util.GetAdminMessages()

  instance_ref = app_profile_ref.Parent()

  multi_cluster_routing = None
  single_cluster_routing = None
  if multi_cluster:
    # Default failover radius to ANY_REGION.
    failover_radius_enum = (
        msgs.MultiClusterRoutingUseAny.FailoverRadiusValueValuesEnum(
            failover_radius or 'ANY_REGION'
        )
    )
    multi_cluster_routing = msgs.MultiClusterRoutingUseAny(
        clusterIds=restrict_to or [], failoverRadius=failover_radius_enum
    )
  elif cluster:
    single_cluster_routing = msgs.SingleClusterRouting(
        clusterId=cluster, allowTransactionalWrites=transactional_writes
    )

  # Default priority to PRIORITY_UNSPECIFIED.
  priority_enum = msgs.AppProfile.PriorityValueValuesEnum(
      priority or 'PRIORITY_UNSPECIFIED'
  )

  msg = msgs.BigtableadminProjectsInstancesAppProfilesCreateRequest(
      appProfile=msgs.AppProfile(
          description=description,
          multiClusterRoutingUseAny=multi_cluster_routing,
          singleClusterRouting=single_cluster_routing,
          priority=priority_enum,
      ),
      appProfileId=app_profile_ref.Name(),
      parent=instance_ref.RelativeName(),
      ignoreWarnings=force,
  )
  return client.projects_instances_appProfiles.Create(msg)


def Update(
    app_profile_ref,
    cluster=None,
    description='',
    multi_cluster=False,
    restrict_to=None,
    failover_radius=None,
    transactional_writes=False,
    force=False,
    priority=None,
):
  """Update an app profile.

  Args:
    app_profile_ref: A resource reference of the app profile to update.
    cluster: string, The cluster id for the app profile to route to using single
      cluster routing.
    description: string, A description of the app profile.
    multi_cluster: bool, Whether this app profile should route to multiple
      clusters, instead of single cluster.
    restrict_to: list[string] The list of cluster IDs for the app profile to
      route to using multi cluster routing.
    failover_radius: string, Restricts clusters that requests can fail over to
      by proximity with multi cluster routing.
    transactional_writes: bool, Whether this app profile has transactional
      writes enabled. This is only possible when using single cluster routing.
    force: bool, Whether to ignore API warnings and create forcibly.
    priority: string, The request priority of the app profile.

  Raises:
    ConflictingArgumentsException:
        If both cluster and multi_cluster are present.
        If both multi_cluster and transactional_writes are present.
        If both cluster and restrict_to are present.
        If both cluster and failover_radius are present.
    OneOfArgumentsRequiredException: If neither cluster or multi_cluster are
        present.

  Returns:
    Long running operation.
  """
  if multi_cluster and cluster:
    raise exceptions.ConflictingArgumentsException('--route-to', '--route-any')
  if multi_cluster and transactional_writes:
    raise exceptions.ConflictingArgumentsException(
        '--route-any', '--transactional-writes'
    )
  if cluster and restrict_to:
    raise exceptions.ConflictingArgumentsException(
        '--route-to', '--restrict-to'
    )
  if cluster and failover_radius:
    raise exceptions.ConflictingArgumentsException(
        '--route-to', '--failover-radius'
    )
  if not multi_cluster and not cluster:
    raise exceptions.OneOfArgumentsRequiredException(
        ['--route-to', '--route-any'],
        'Either --route-to or --route-any must be specified.',
    )

  client = util.GetAdminClient()
  msgs = util.GetAdminMessages()

  changed_fields = []
  app_profile = msgs.AppProfile()

  if cluster:
    changed_fields.append('singleClusterRouting')
    app_profile.singleClusterRouting = msgs.SingleClusterRouting(
        clusterId=cluster, allowTransactionalWrites=transactional_writes
    )
  elif multi_cluster:
    changed_fields.append('multiClusterRoutingUseAny')
    if failover_radius:
      failover_radius_enum = (
          msgs.MultiClusterRoutingUseAny.FailoverRadiusValueValuesEnum(
              failover_radius
          )
      )
    else:
      failover_radius_enum = None
    app_profile.multiClusterRoutingUseAny = msgs.MultiClusterRoutingUseAny(
        clusterIds=restrict_to or [], failoverRadius=failover_radius_enum
    )

  if description:
    changed_fields.append('description')
    app_profile.description = description

  if priority:
    priority_enum = msgs.AppProfile.PriorityValueValuesEnum(priority)
    changed_fields.append('priority')
    app_profile.priority = priority_enum

  msg = msgs.BigtableadminProjectsInstancesAppProfilesPatchRequest(
      appProfile=app_profile,
      name=app_profile_ref.RelativeName(),
      updateMask=','.join(changed_fields),
      ignoreWarnings=force,
  )
  return client.projects_instances_appProfiles.Patch(msg)
