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
"""Utils for GKE Connect generate gateway RBAC policy files."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import re

from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.command_lib.container.fleet.memberships import errors as memberships_errors
from googlecloudsdk.command_lib.projects import util as projects_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties

CLUSTER_ROLE = 'clusterrole'
NAMESPACE_ROLE = 'role'
ANTHOS_SUPPORT_USER = 'service-{project_number}@gcp-sa-{instance_name}anthossupport.iam.gserviceaccount.com'
IMPERSONATE_POLICY_FORMAT = """\
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: gateway-impersonate-{metadata_name}
  labels:
    connect.gke.io/owner-feature: connect-gateway
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
  labels:
    connect.gke.io/owner-feature: connect-gateway
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
  labels:
    connect.gke.io/owner-feature: connect-gateway
subjects:{users}
roleRef:
  kind: ClusterRole
  name: {permission}
  apiGroup: rbac.authorization.k8s.io
---
"""
PERMISSION_POLICY_NAMESPACE_FORMAT = """\
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: gateway-permission-{metadata_name}
  labels:
    connect.gke.io/owner-feature: connect-gateway
  namespace: {namespace}
subjects:{users}
roleRef:
  kind: Role
  name: {permission}
  apiGroup: rbac.authorization.k8s.io
---
"""
PERMISSION_POLICY_ANTHOS_SUPPORT_FORMAT = """\
---
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: anthos-support-reader
  labels:
    connect.gke.io/owner-feature: connect-gateway
rules:
- apiGroups:
  - '*'
  resources: ["apiservices", "clusterrolebindings","clusterroles","clusters","clusterstates","configmaps","controlplanes","customresourcedefinitions","cronjobs","daemonsets","deployments","endpoints", "events", "jobs","machineclasses","machinedeployments","machines","machinesets","machines","mutatingwebhookconfigurations","namespaces","nodes","onpremadminclusters","onpremnodepools","onpremplatforms","onpremuserclusters","pods","pods/log","persistentvolumeclaims","persistentvolumes","replicasets","services","statefulsets","validatingwebhookconfigurations","validations"]
  verbs: ["get", "list", "watch"]
- nonResourceURLs:
  - '*'
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: gateway-anthos-support-permission-{metadata_name}
  labels:
    connect.gke.io/owner-feature: connect-gateway
subjects:{users}
roleRef:
  kind: ClusterRole
  name: anthos-support-reader
  apiGroup: rbac.authorization.k8s.io
---
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
  """Validate Args in correct format."""
  # Validate the confliction between '--anthos-support' and '--role'.
  if not args.revoke and ((args.anthos_support and args.role) or (
      not args.anthos_support and not args.role)):
    raise InvalidArgsError(
        'Please specify either --role or --anthos-support in the flags.')
  if args.role:
    ValidateRole(args.role)
  # Validate the confliction between '--anthos-support' and '--users'.
  if not args.users and not args.anthos_support:
    raise InvalidArgsError(
        'Please specify the either --users or --anthos-support the flags.')
  # Validate required flags when apply RBAC policy to cluster.
  if args.apply:
    if not args.membership:
      raise InvalidArgsError('Please specify the --membership in flags.')
    if not args.kubeconfig:
      raise InvalidArgsError('Please specify the --kubeconfig in flags.')
    if not args.context:
      raise InvalidArgsError('Please specify the --context in flags.')
  # Validate users in correct format before generate RBAC policy.
  if args.users:
    users_list = args.users.split(',')
    for user in users_list:
      if '@' not in user:
        raise InvalidArgsError(
            'Please specify the --users in correct format: foo@example.com.')
  if args.revoke and args.apply:
    # Validate confliction between --apply and --revoke.
    raise InvalidArgsError(
        'Please specify either --apply or --revoke in flags.')
  if args.revoke:
    # Validate required flags when revoke RBAC policy for specified user from
    # from cluster.
    if not args.membership:
      raise InvalidArgsError('Please specify the --membership in flags.')
    if not args.kubeconfig:
      raise InvalidArgsError('Please specify the --kubeconfig in flags.')
    if not args.context:
      raise InvalidArgsError('Please specify the --context in flags.')


def GetAnthosSupportUser(project_id):
  """Get P4SA account name for Anthos Support when user not specified."""
  project_number = projects_api.Get(
      projects_util.ParseProject(project_id)).projectNumber
  endpoint_overrides = properties.VALUES.api_endpoint_overrides.AllValues()
  hub_endpoint_override = endpoint_overrides.get('gkehub', '')
  if not hub_endpoint_override:
    return ANTHOS_SUPPORT_USER.format(
        project_number=project_number, instance_name='')
  elif 'autopush-gkehub' in hub_endpoint_override:
    return ANTHOS_SUPPORT_USER.format(
        project_number=project_number, instance_name='autopush-')
  else:
    raise memberships_errors.UnknownApiEndpointOverrideError('gkehub')


def GenerateRBAC(args, project_id):
  """Returns the generated RBAC policy file with args provided."""
  generated_rbac = {}
  cluster_pattern = re.compile('^clusterrole/')
  namespace_pattern = re.compile('^role/')
  role_permission = ''
  rbac_policy_format = ''
  namespace = ''
  metadata_name = ''
  users_list = list()

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

  if args.users:
    users_list = args.users.split(',')
  elif args.anthos_support:
    users_list.append(GetAnthosSupportUser(project_id))
  for user in users_list:
    impersonate_users = os.linesep + '  - {user}'.format(user=user)
    permission_users = os.linesep + '- kind: User'
    permission_users += os.linesep + '  name: {user}'.format(user=user)
    user_name = user.split('@')[0]
    if args.membership:
      metadata_name = project_id + '_' + user_name + '_' + args.membership
    else:
      metadata_name = project_id + '_' + user_name

    # Assign value to the RBAC file templates.
    single_generated_rbac = rbac_policy_format.format(
        metadata_name=metadata_name,
        namespace=namespace,
        user_account=impersonate_users,
        users=permission_users,
        permission=role_permission)
    generated_rbac[user] = single_generated_rbac

  return generated_rbac


class InvalidArgsError(exceptions.Error):

  def __init__(self, error_message):
    message = '{}'.format(error_message)
    super(InvalidArgsError, self).__init__(message)
