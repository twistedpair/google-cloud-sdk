# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utils for GKE Connect generate gateway RBAC policy files."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import re

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log

CLUSTER_ROLE = 'clusterrole'
NAMESPACE_ROLE = 'role'
RBAC_POLICY_CLUSTER_ROLE_FORMAT = """\
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: gateway-impersonate-{project_id}-{cluster_name}
rules:
- apiGroups:
  - ""
  resourceNames:{user_account}
  resources:
  - users
  verbs:
  - impersonate
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: gateway-impersonate-{project_id}-{cluster_name}
roleRef:
  kind: ClusterRole
  name: gateway-impersonate-{project_id}-{cluster_name}
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: connect-agent-sa
  namespace: gke-connect
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: gateway-permission-{project_id}-{cluster_name}
subjects:{users}
roleRef:
  kind: ClusterRole
  name: {permission}
  apiGroup: rbac.authorization.k8s.io
"""

RBAC_POLICY_ROLE_FORMAT = """\
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: gateway-impersonate-{project_id}-{cluster_name}
rules:
- apiGroups:
  - ""
  resourceNames:{role_user_account}
  resources:
  - users
  verbs:
  - impersonate
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: gateway-impersonate-{project_id}-{cluster_name}
roleRef:
  kind: ClusterRole
  name: gateway-impersonate-{project_id}-{cluster_name}
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: connect-agent-sa
  namespace: gke-connect
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: gateway-permission-{project_id}-{cluster_name}
  namespace: {namespace}
subjects:{role_users}
roleRef:
  kind: Role
  name: {role_permission}
  apiGroup: rbac.authorization.k8s.io
"""


def ValidateArgs(args):
  """Validation for input args in correct format."""
  cluster_pattern = re.compile('^clusterrole/')
  namespace_pattern = re.compile('^role/')
  if cluster_pattern.match(args.role.lower()):
    log.status.Print('Specified ClusterRole is:', args.role)
    if len(args.role.split('/')) != 2:
      raise InvalidArgsError(
          'Cluster role is not specified in correct format. Please specify the '
          'cluster role as: clusterrole/cluser-permission'
      )
  elif namespace_pattern.match(args.role.lower()):
    if len(args.role.split('/')) != 3:
      raise InvalidArgsError(
          'Namespace role is not specified in correct format. Please specify '
          'the namespace role as: role/namespace/namespace-permission'
      )
    log.status.Print('Specified Namespace Role is:', args.role)
  else:
    raise InvalidArgsError(
        'The required role is not a cluster role or a namespace role.')


def GenerateRBAC(args, project_id):
  """Returns the generated RBAC policy file with args provided."""
  expected_rbac = ''
  cluster_pattern = re.compile('^clusterrole/')
  namespace_pattern = re.compile('^role/')
  if cluster_pattern.match(args.role.lower()):
    # Get the role permission
    role_permission = args.role.split('/')[1]

    # Get the users to grant permission
    user_account = ''
    users = ''
    user_list = args.users.split(',')
    for user in user_list:
      user_account += os.linesep + '  - {user}'.format(user=user)
      users += os.linesep + '- kind: User'
      users += os.linesep + '  name: {user}'.format(user=user)

    # Assign value to the RBAC file templates.
    expected_rbac = RBAC_POLICY_CLUSTER_ROLE_FORMAT.format(
        project_id=project_id,
        cluster_name=args.MEMBERSHIP,
        user_account=user_account,
        users=users,
        permission=role_permission)
  elif namespace_pattern.match(args.role.lower()):
    # Get the role permission
    role_namespace = args.role.split('/')[1]
    role_permission = args.role.split('/')[2]

    # Get the users to grant permission
    users_in_cli = args.users.split(',')
    user_account = ''
    users = ''
    for user in users_in_cli:
      user_account += os.linesep + '  - {user}'.format(user=user)
      users += os.linesep + '- kind: User'
      users += os.linesep + '  name: {user}'.format(user=user)

    # Assign value to the RBAC file templates.
    expected_rbac = RBAC_POLICY_ROLE_FORMAT.format(
        project_id=project_id,
        cluster_name=args.MEMBERSHIP,
        namespace=role_namespace,
        role_user_account=user_account,
        role_users=users,
        role_permission=role_permission)
  return expected_rbac


class InvalidArgsError(exceptions.Error):

  def __init__(self, error_message):
    message = '{}'.format(error_message)
    super(InvalidArgsError, self).__init__(message)
