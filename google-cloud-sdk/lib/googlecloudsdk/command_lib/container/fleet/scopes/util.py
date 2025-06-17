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
"""Utils for Fleet scopes commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.api_lib.container.fleet import client
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.core import exceptions


class ScopeLogViewCondition:
  """Helper class for creating a scope log view iam condition.

  This class defines a `get` object method that can be used by the iam util
  lib to get the iam condition spec.
  """

  def __init__(self, project_id, scope_id):
    self.project_id = project_id
    self.scope_id = scope_id

  # The condition should be iterable.
  def __iter__(self):
    return self

  def __next__(self):
    # There is only one condition.
    raise StopIteration

  def IsSpecified(self):
    return True

  def get(self, condition_spec):  # pylint: disable=invalid-name
    # This method is called by the iam util lib.
    if condition_spec == 'title':
      return 'conditional log view access'
    if condition_spec == 'description':
      return 'log view access for scope {}'.format(self.scope_id)
    if condition_spec == 'expression':
      return (
          'resource.name =='
          f' "projects/{self.project_id}/locations/global/buckets/fleet-o11y-scope-{self.scope_id}/views/fleet-o11y-scope-{self.scope_id}-k8s_container"'
          ' || resource.name =='
          f' "projects/{self.project_id}/locations/global/buckets/fleet-o11y-scope-{self.scope_id}/views/fleet-o11y-scope-{self.scope_id}-k8s_pod"'
      )


class AppOperatorBinding:
  """Helper class for containing a principal with their project-level IAM role, fleet scope-level role, and fleet scope RBAC role.
  """

  def __init__(self, principal, overall_role, scope_rrb_role, scope_iam_role, project_iam_role, log_view_access):
    # The principal in the IAM format, e.g., "user:person@google.com".
    self.principal = principal
    # Overall role can be "view", "edit", or "admin" if the IAM and RBAC roles
    # are known and consistent. If inconsistent, it will be "custom". Otherwise,
    # it will be "unknown".
    self.overall_role = overall_role
    # Scope RBAC role can be "view", "edit", "admin", "not found", or
    # "permission denied".
    self.scope_rrb_role = scope_rrb_role
    # Scope-level IAM role can be "roles/gkehub.scopeViewer",
    # "roles/gkehub.scopeEditor", "roles/gkehub.scopeAdmin", "not found", or
    # "permission denied".
    self.scope_iam_role = scope_iam_role
    # Project-level IAM role can be "roles/gkehub.scopeViewerProjectLevel",
    # "roles/gkehub.scopeEditorProjectLevel", "not found", or
    # "permission denied".
    self.project_iam_role = project_iam_role
    # Log view access can be "granted", "not found", or "permission denied".
    self.log_view_access = log_view_access


def SetParentCollection(ref, args, request):
  """Set parent collection with location for created resources.

  Args:
    ref: reference to the scope object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request
  """
  del ref, args  # Unused.
  request.parent = request.parent + '/locations/-'
  return request


def CheckUpdateArguments(ref, args, request):
  del ref, args  # Unused.
  if request.updateMask is None or not request.updateMask:
    request.updateMask = 'name'
  return request


def HandleNamespaceLabelsUpdateRequest(ref, args):
  """Add namespace labels to update request.

  Args:
    ref: reference to the scope object.
    args: command line arguments.

  Returns:
    response

  """
  mask = []
  release_track = args.calliope_command.ReleaseTrack()
  fleetclient = client.FleetClient(release_track)

  labels_diff = labels_util.Diff.FromUpdateArgs(args)
  namespace_labels_diff = labels_util.Diff(
      args.update_namespace_labels,
      args.remove_namespace_labels,
      args.clear_namespace_labels,
  )

  current_scope = fleetclient.GetScope(ref.RelativeName())

  # update GCP labels for namespace resource
  new_labels = labels_diff.Apply(
      fleetclient.messages.Scope.LabelsValue, current_scope.labels
  ).GetOrNone()
  if new_labels:
    mask.append('labels')

  # add cluster namespace level labels to resource
  new_namespace_labels = namespace_labels_diff.Apply(
      fleetclient.messages.Scope.NamespaceLabelsValue,
      current_scope.namespaceLabels,
  ).GetOrNone()
  if new_namespace_labels:
    mask.append('namespace_labels')

  # if there are no fields to update, don't make update api call
  if not mask:
    response = fleetclient.messages.Scope(name=ref.RelativeName())
    return response

  return fleetclient.UpdateScope(
      ref.RelativeName(), new_labels, new_namespace_labels, ','.join(mask)
  )


def HandleNamespaceLabelsCreateRequest(ref, args, request):
  """Add namespace labels to create request.

  Args:
    ref: reference to the scope object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request

  """
  del ref
  release_track = args.calliope_command.ReleaseTrack()
  fleetclient = client.FleetClient(release_track)
  namespace_labels_diff = labels_util.Diff(additions=args.namespace_labels)
  ns_labels = namespace_labels_diff.Apply(
      fleetclient.messages.Scope.NamespaceLabelsValue, None
  ).GetOrNone()
  request.scope.namespaceLabels = ns_labels
  return request


def IamMemberFromRbac(user, group):
  """Returns Iam member for the specified RBAC user/group.

  Args:
    user: user email, principal or None
    group: group email, principal set or None

  Returns:
    an Iam member, e.g., "user:person@google.com" or "group:people@google.com"

  Raises:
    a core.Error, if both user and group are None
  """
  if user:
    if user.startswith('principal://'):
      return user
    if user.endswith('gserviceaccount.com'):
      return 'serviceAccount:' + user
    return 'user:' + user
  if group:
    if group.startswith('principalSet://'):
      return group
    return 'group:' + group
  raise exceptions.Error(
      'User or group is required in the args.'
  )


def IamScopeLevelScopeRoleFromRbac(role):
  """Returns Iam scope role (scope-level) based on the specified RBAC role.

  Args:
    role: RBAC role

  Returns:
    a scope-related Iam role, e.g., "roles/gkehub.scopeEditor"

  Raises:
    a core.Error, if the role is not admin, edit, or view
  """
  if role == 'admin':
    return 'roles/gkehub.scopeAdmin'
  elif role == 'edit':
    return 'roles/gkehub.scopeEditor'
  elif role == 'view':
    return 'roles/gkehub.scopeViewer'
  elif role:
    return 'roles/gkehub.scopeViewer'
  raise exceptions.Error(
      'Role is required to be admin, edit, view or a custom role.'
  )


def AllIamScopeLevelScopeRoles():
  """Returns all valid Iam scope roles at scope level.
  """
  return [
      'roles/gkehub.scopeAdmin',
      'roles/gkehub.scopeEditor',
      'roles/gkehub.scopeViewer',
  ]


def IamProjectLevelScopeRoleFromRbac(role):
  """Returns Iam scope role (project-level) based on the specified RBAC role.

  Args:
    role: RBAC role

  Returns:
    a scope-related Iam role, e.g., "roles/gkehub.scopeEditorProjectLevel"

  Raises:
    a core.Error, if the role is not admin, edit, or view
  """
  if role == 'admin':
    # Admin needs the same project-level permissions as Editor.
    return 'roles/gkehub.scopeEditorProjectLevel'
  elif role == 'edit':
    return 'roles/gkehub.scopeEditorProjectLevel'
  elif role == 'view':
    return 'roles/gkehub.scopeViewerProjectLevel'
  elif role:
    # Custom role gives minimal editor project-level permissions.
    return 'roles/gkehub.scopeEditorProjectLevel'
  raise exceptions.Error(
      'Role is required to be admin, edit, or view.'
  )


def AllIamProjectLevelScopeRoles():
  """Returns all valid Iam scope roles at project level.
  """
  return [
      'roles/gkehub.scopeEditorProjectLevel',
      'roles/gkehub.scopeViewerProjectLevel',
  ]


def ScopeRbacRoleString(role):
  """Returns the RBAC role string from the specifiedRBAC role message.

  Args:
    role: RBAC role

  Returns:
    RBAC role string (admin, edit, or view)

  Raises:
    a core.Error, if the role is not admin, edit, or view
  """
  if role.customRole:
    return role.customRole
  elif str(encoding.MessageToPyValue(role)['predefinedRole']) == 'ADMIN':
    return 'admin'
  elif str(encoding.MessageToPyValue(role)['predefinedRole']) == 'EDIT':
    return 'edit'
  elif str(encoding.MessageToPyValue(role)['predefinedRole']) == 'VIEW':
    return 'view'
  raise exceptions.Error(
      'Role is required to be admin, edit, view or a custom role.'
  )


def RbacAndScopeIamRolesMatch(rbac_role, scope_iam_role):
  """Returns true if the specified RBAC role and scope IAM role match.
  """
  if rbac_role == 'admin' and scope_iam_role == 'roles/gkehub.scopeAdmin':
    return True
  if rbac_role == 'edit' and scope_iam_role == 'roles/gkehub.scopeEditor':
    return True
  return rbac_role == 'view' and scope_iam_role == 'roles/gkehub.scopeViewer'
