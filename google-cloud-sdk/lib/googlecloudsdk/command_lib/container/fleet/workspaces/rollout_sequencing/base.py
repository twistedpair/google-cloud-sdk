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
"""Base class for Cluster Upgrade Feature CRUD operations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.container.fleet.features import base as feature_base
from googlecloudsdk.command_lib.projects import util as project_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core.resource import resource_projector
import six

CLUSTER_UPGRADE_FEATURE = 'clusterupgrade'


class ClusterUpgradeCommand(object):
  """Base class for Cluster Upgrade Feature commands."""

  def __init__(self, args):
    self.feature_name = CLUSTER_UPGRADE_FEATURE
    self.args = args

  @staticmethod
  def GetScopeNameWithProjectNumber(name):
    """Rebuilds scope name with project number instead of ID."""
    delimiter = '/'
    tokens = name.split(delimiter)
    if len(tokens) != 6 or tokens[0] != 'projects':
      raise exceptions.Error(
          '{} is not a valid Scope resource name'.format(name))
    project_id = tokens[1]
    project_number = project_util.GetProjectNumber(project_id)
    tokens[1] = six.text_type(project_number)
    return delimiter.join(tokens)

  @staticmethod
  def GetProjectFromScopeName(name):
    """Extracts the project name from the full Scope resource name."""
    return name.split('/')[1]

  def ReleaseTrack(self):
    """Required to initialize HubClient. See calliope base class."""
    return self.args.calliope_command.ReleaseTrack()

  def IsClusterUpgradeRequest(self):
    """Checks if any Cluster Upgrade Feature related arguments are present."""
    cluster_upgrade_flags = {
        'show_cluster_upgrade',
        'show_linked_cluster_upgrade',
    }
    return any(has_value and flag in cluster_upgrade_flags
               for flag, has_value in self.args.__dict__.items())


class DescribeCommand(feature_base.FeatureCommand, ClusterUpgradeCommand):
  """Command for describing a Scope's Cluster Upgrade Feature."""

  def GetScopeWithClusterUpgradeInfo(self, scope, feature):
    """Adds Cluster Upgrade Feature information to describe Scope response."""
    scope_name = ClusterUpgradeCommand.GetScopeNameWithProjectNumber(scope.name)
    if self.args.show_cluster_upgrade:
      serialized_scope = resource_projector.MakeSerializable(scope)
      serialized_scope[
          'clusterUpgrade'] = self.GetClusterUpgradeInfoForScope(
              scope_name, feature)
      return serialized_scope
    elif self.args.show_linked_cluster_upgrade:
      serialized_scope = resource_projector.MakeSerializable(scope)
      serialized_scope['clusterUpgrades'] = self.GetLinkedClusterUpgradeScopes(
          scope_name, feature)
      return serialized_scope
    return scope

  def GetClusterUpgradeInfoForScope(self, scope_name, feature):
    """Gets Cluster Upgrade Feature information for the provided Scope."""
    return ({
        'scope': scope_name,
        'state':
            self.hubclient.ToPyDefaultDict(
                self.messages.ScopeFeatureState,
                feature.scopeStates)[scope_name].clusterupgrade
            or self.messages.ClusterUpgradeScopeState(),
        'spec':
            self.hubclient.ToPyDefaultDict(
                self.messages.ScopeFeatureSpec,
                feature.scopeSpecs)[scope_name].clusterupgrade
            or self.messages.ClusterUpgradeScopeSpec(),
    })

  def GetLinkedClusterUpgradeScopes(self, scope_name, feature):
    """Gets Cluster Upgrade Feature information for the entire sequence."""

    current_project = ClusterUpgradeCommand.GetProjectFromScopeName(
        scope_name)
    visited = set([scope_name])

    def UpTheStream(cluster_upgrade):
      """Recursively gets information for the upstream Scopes."""
      upstream_spec = cluster_upgrade.get('spec', None)
      upstream_scopes = upstream_spec.upstreamScopes if upstream_spec else None
      if not upstream_scopes:
        return [cluster_upgrade]

      # Currently, we only process the first upstream Scope in the
      # Cluster Upgrade Feature, forming a linked-list of Scopes. If the API
      # ever supports multiple upstream Scopes (i.e., graph of Scopes), this
      # will need to be modified to recurse on every Scope.
      upstream_scope_name = upstream_scopes[0]
      if upstream_scope_name in visited:
        return [cluster_upgrade]  # Detected a cycle.
      visited.add(upstream_scope_name)

      upstream_scope_project = ClusterUpgradeCommand.GetProjectFromScopeName(
          upstream_scope_name)
      upstream_feature = (
          feature if upstream_scope_project == current_project else
          self.GetFeature(project=upstream_scope_project))
      upstream_cluster_upgrade = self.GetClusterUpgradeInfoForScope(
          upstream_scope_name, upstream_feature)
      return UpTheStream(upstream_cluster_upgrade) + [cluster_upgrade]

    def DownTheStream(cluster_upgrade):
      """Recursively gets information for the downstream Scopes."""
      downstream_state = cluster_upgrade.get('state', None)
      downstream_scopes = (
          downstream_state.downstreamScopes if downstream_state else None)
      if not downstream_scopes:
        return [cluster_upgrade]

      # Currently, we only process the first downstream Scope in the
      # Cluster Upgrade Feature, forming a linked-list of Scopes. If the API
      # ever supports multiple downstream Scopes (i.e., graph of Scopes), this
      # will need to be modified to recurse on every Scope.
      downstream_scope_name = downstream_scopes[0]
      if downstream_scope_name in visited:
        return [cluster_upgrade]  # Detected a cycle.
      visited.add(downstream_scope_name)

      downstream_scope_project = ClusterUpgradeCommand.GetProjectFromScopeName(
          downstream_scope_name)
      downstream_feature = (
          feature if downstream_scope_project == current_project else
          self.GetFeature(project=downstream_scope_project))
      downstream_cluster_upgrade = self.GetClusterUpgradeInfoForScope(
          downstream_scope_name, downstream_feature)
      return [cluster_upgrade] + DownTheStream(downstream_cluster_upgrade)

    current_cluster_upgrade = self.GetClusterUpgradeInfoForScope(
        scope_name, feature)
    upstream_cluster_upgrades = UpTheStream(current_cluster_upgrade)[:-1]
    downstream_cluster_upgrades = DownTheStream(current_cluster_upgrade)[1:]
    return (upstream_cluster_upgrades + [current_cluster_upgrade] +
            downstream_cluster_upgrades)
