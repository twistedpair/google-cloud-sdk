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
IMPERSONATE_POLICY_FORMAT = """\
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: gateway-impersonate-{metadata_name}
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
  name: gateway-impersonate-{metadata_name}
roleRef:
  kind: ClusterRole
  name: gateway-impersonate-{metadata_name}
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: connect-agent-sa
  namespace: gke-connect
"""
PERMISSION_POLICY_CLUSTER_FORMAT = """\
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: gateway-permission-{metadata_name}
subjects:{users}
roleRef:
  kind: ClusterRole
  name: {permission}
  apiGroup: rbac.authorization.k8s.io
"""
PERMISSION_POLICY_NAMESPACE_FORMAT = """\
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: gateway-permission-{metadata_name}
  namespace: {namespace}
subjects:{users}
roleRef:
  kind: Role
  name: {permission}
  apiGroup: rbac.authorization.k8s.io
"""
PERMISSION_POLICY_ANTHOS_SUPPORT_FORMAT = """\
---
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: anthos-support-reader
rules:
- apiGroups:
  - '*'
  resources:
  - '*'
  verbs: ["get", "list", "watch"]
- nonResourceURLs:
  - '*'
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: gateway-anthos-support-permission-{metadata_name}
subjects:{users}
roleRef:
  kind: ClusterRole
  name: anthos-support-reader
  apiGroup: rbac.authorization.k8s.io
"""


def ValidateRole(role):
  """Validation for the role in correct format."""
  cluster_pattern = re.compile('^clusterrole/')
  namespace_pattern = re.compile('^role/')
  if cluster_pattern.match(role.lower()):
    log.status.Print('Specified Cluster Role is:', role)
    if len(role.split('/')) != 2:
      raise InvalidArgsError(
          'Cluster role is not specified in correct format. Please specify the '
          'cluster role as: clusterrole/cluser-permission')
  elif namespace_pattern.match(role.lower()):
    log.status.Print('Specified Namespace Role is:', role)
    if len(role.split('/')) != 3:
      raise InvalidArgsError(
          'Namespace role is not specified in correct format. Please specify '
          'the namespace role as: role/namespace/namespace-permission')
  else:
    raise InvalidArgsError(
        'The required role is not a cluster role or a namespace role.')


def ValidateArgs(args):
  """Validate the confliction between '--anthos-support' and '--role'."""
  if (args.anthos_support and args.role) or (not args.anthos_support and
                                             not args.role):
    raise InvalidArgsError(
        'Please specify either --role or --anthos-support in the flags.')
  if args.role:
    ValidateRole(args.role)


def GenerateRBAC(args, project_id):
  """Returns the generated RBAC policy file with args provided."""
  generated_rbac = ''
  cluster_pattern = re.compile('^clusterrole/')
  namespace_pattern = re.compile('^role/')
  impersonate_users = ''
  permission_users = ''
  users_list = args.users.split(',')
  role_permission = ''
  rbac_policy_format = ''
  namespace = ''
  metadata_name = ''

  if args.anthos_support:
    rbac_policy_format = IMPERSONATE_POLICY_FORMAT + PERMISSION_POLICY_ANTHOS_SUPPORT_FORMAT
  elif cluster_pattern.match(args.role.lower()):
    rbac_policy_format = IMPERSONATE_POLICY_FORMAT + PERMISSION_POLICY_CLUSTER_FORMAT
    role_permission = args.role.split('/')[1]
  elif namespace_pattern.match(args.role.lower()):
    rbac_policy_format = IMPERSONATE_POLICY_FORMAT + PERMISSION_POLICY_NAMESPACE_FORMAT
    namespace = args.role.split('/')[1]
    role_permission = args.role.split('/')[2]
  else:
    raise InvalidArgsError(
        'Invalid flags, please specify either the --role or --anthos-support in'
        'your flags.')

  if args.membership:
    metadata_name = project_id + '-' + args.membership
  else:
    metadata_name = project_id

  for user in users_list:
    impersonate_users += os.linesep + '  - {user}'.format(user=user)
    permission_users += os.linesep + '- kind: User'
    permission_users += os.linesep + '  name: {user}'.format(user=user)

  # Assign value to the RBAC file templates.
  generated_rbac = rbac_policy_format.format(
      metadata_name=metadata_name,
      namespace=namespace,
      user_account=impersonate_users,
      users=permission_users,
      permission=role_permission)

  return generated_rbac


class InvalidArgsError(exceptions.Error):

  def __init__(self, error_message):
    message = '{}'.format(error_message)
    super(InvalidArgsError, self).__init__(message)
