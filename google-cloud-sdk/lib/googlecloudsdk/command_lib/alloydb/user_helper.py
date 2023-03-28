# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Helper functions for constructing and validating AlloyDB user requests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import properties


def ConstructCreateRequestFromArgs(client, alloydb_messages, project_ref, args):
  """Validates command line input arguments and passes parent's resources.

  Args:
    client: Client for api_utils.py class.
    alloydb_messages: Messages module for the API client.
    project_ref: parent resource path of the resource being created
    args: Command line input arguments.

  Returns:
    Fully-constructed request to create an AlloyDB user.
  """
  user_resource = alloydb_messages.User()
  user_ref = client.resource_parser.Create(
      'alloydb.projects.locations.clusters.users',
      projectsId=properties.VALUES.core.project.GetOrFail,
      locationsId=args.region,
      clustersId=args.cluster,
      usersId=args.username,
  )
  user_resource.name = user_ref.RelativeName()

  # set password if provided
  if args.password:
    user_resource.password = args.password
  # set authentication method if provided
  user_resource.authMethod = _ParseAuthenticationMethod(
      alloydb_messages, args.type
  )
  # set user type if provided
  user_resource.userType = _ParseUserType(alloydb_messages, args.type)
  # set database roles if provided
  user_resource.databaseRoles = _ParseDatabaseRoles(args)

  return alloydb_messages.AlloydbProjectsLocationsClustersUsersCreateRequest(
      user=user_resource,
      userId=args.username,
      parent=project_ref.RelativeName(),
  )


def _ParseAuthenticationMethod(alloydb_messages, authentication_method):
  if authentication_method:
    return alloydb_messages.User.AuthMethodValueValuesEnum.lookup_by_name(
        authentication_method.upper()
    )
  return None


def _ParseUserType(alloydb_messages, authentication_method):
  if authentication_method == 'BUILT_IN':
    return alloydb_messages.User.UserTypeValueValuesEnum.ALLOYDB_BUILT_IN
  elif authentication_method == 'IAM_BASED':
    return alloydb_messages.User.UserTypeValueValuesEnum.ALLOYDB_IAM_USER
  return None


def _ParseDatabaseRoles(args):
  if args.db_roles:
    if args.superuser:
      return args.db_roles + ['alloydbsuperuser']
    else:
      return args.db_roles
  else:
    if args.superuser:
      return ['alloydbsuperuser']
  return []
