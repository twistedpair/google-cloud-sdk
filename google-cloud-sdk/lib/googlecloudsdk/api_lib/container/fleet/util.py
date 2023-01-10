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
"""Fleet API utils."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import resources

VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v1alpha',
    base.ReleaseTrack.BETA: 'v1beta',
    base.ReleaseTrack.GA: 'v1'
}


def GetMessagesModule(release_track=base.ReleaseTrack.GA):
  return apis.GetMessagesModule('gkehub', VERSION_MAP[release_track])


def GetClientInstance(release_track=base.ReleaseTrack.GA):
  return apis.GetClientInstance('gkehub', VERSION_MAP[release_track])


def GetClientClass(release_track=base.ReleaseTrack.GA):
  return apis.GetClientClass('gkehub', VERSION_MAP[release_track])


def LocationResourceName(project, location='global'):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Create(
      'gkehub.projects.locations',
      projectsId=project,
      locationsId=location,
  ).RelativeName()


def MembershipLocation(full_name):
  matches = re.search('projects/.*/locations/(.*)/memberships/(.*)', full_name)
  if matches:
    return matches.group(1)
  raise exceptions.Error(
      'Invalid membership resource name: {}'.format(full_name))


def MembershipResourceName(project, membership, location='global'):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Create(
      'gkehub.projects.locations.memberships',
      projectsId=project,
      locationsId=location,
      membershipsId=membership,
  ).RelativeName()


def MembershipPartialName(full_name):
  matches = re.search('projects/.*/locations/(.*)/memberships/(.*)', full_name)
  if matches:
    return matches.group(1) + '/' + matches.group(2)
  raise exceptions.Error(
      'Invalid membership resource name: {}'.format(full_name))


def MembershipShortname(full_name):
  return resources.REGISTRY.ParseRelativeName(
      full_name, collection='gkehub.projects.locations.memberships').Name()


def FeatureResourceName(project, feature, location='global'):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Create(
      'gkehub.projects.locations.features',
      projectsId=project,
      locationsId=location,
      featuresId=feature,
  ).RelativeName()


def OperationResourceName(project, operation, location='global'):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Create(
      'gkehub.projects.locations.operations',
      projectsId=project,
      locationsId=location,
      operationsId=operation,
  ).RelativeName()


def FleetResourceName(project,
                      fleet='default',
                      location='global',
                      release_track=base.ReleaseTrack.ALPHA):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Parse(
      line=None,
      params={
          'projectsId': project,
          'locationsId': location,
          'fleetsId': fleet,
      },
      collection='gkehub.projects.locations.fleets',
      api_version=VERSION_MAP[release_track]).RelativeName()


def FleetParentName(project,
                    location='global',
                    release_track=base.ReleaseTrack.ALPHA):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Parse(
      line=None,
      params={
          'projectsId': project,
          'locationsId': location,
      },
      collection='gkehub.projects.locations',
      api_version=VERSION_MAP[release_track]).RelativeName()


def FleetOrgParentName(organization, location='global'):
  return 'organizations/{0}/locations/{1}'.format(organization, location)


def NamespaceParentName(project,
                        release_track=base.ReleaseTrack.ALPHA):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Parse(
      line=None,
      params={
          'projectsId': project,
          'locationsId': 'global',
      },
      collection='gkehub.projects.locations',
      api_version=VERSION_MAP[release_track]).RelativeName()


def NamespaceResourceName(project,
                          name,
                          release_track=base.ReleaseTrack.ALPHA):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Parse(
      line=None,
      params={
          'projectsId': project,
          'locationsId': 'global',
          'namespacesId': name,
      },
      collection='gkehub.projects.locations.namespaces',
      api_version=VERSION_MAP[release_track]).RelativeName()


def RBACRoleBindingParentName(project,
                              namespace,
                              release_track=base.ReleaseTrack.ALPHA):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Parse(
      line=None,
      params={
          'projectsId': project,
          'locationsId': 'global',
          'namespacesId': namespace,
      },
      collection='gkehub.projects.locations.namespaces',
      api_version=VERSION_MAP[release_track]).RelativeName()


def RBACRoleBindingResourceName(project,
                                namespace,
                                name,
                                release_track=base.ReleaseTrack.ALPHA):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Parse(
      line=None,
      params={
          'projectsId': project,
          'locationsId': 'global',
          'namespacesId': namespace,
          'rbacrolebindingsId': name,
      },
      collection='gkehub.projects.locations.namespaces.rbacrolebindings',
      api_version=VERSION_MAP[release_track]).RelativeName()


def MembershipBindingResourceName(project,
                                  name,
                                  membership,
                                  location='global',
                                  release_track=base.ReleaseTrack.GA):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Parse(
      line=None,
      params={
          'projectsId': project,
          'locationsId': location,
          'membershipsId': membership,
          'bindingsId': name,
      },
      collection='gkehub.projects.locations.memberships.bindings',
      api_version=VERSION_MAP[release_track]).RelativeName()


def MembershipBindingParentName(project,
                                membership,
                                location='global',
                                release_track=base.ReleaseTrack.GA):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Parse(
      line=None,
      params={
          'projectsId': project,
          'locationsId': location,
          'membershipsId': membership,
      },
      collection='gkehub.projects.locations.memberships',
      api_version=VERSION_MAP[release_track]).RelativeName()


def ScopeResourceName(project, scope, location='global'):
  # See command_lib/container/fleet/resources.yaml
  return resources.REGISTRY.Create(
      'gkehub.projects.locations.scopes',
      projectsId=project,
      locationsId=location,
      scopesId=scope,
  ).RelativeName()
