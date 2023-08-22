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
"""Functions to transform input args to request field params."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import properties


def GetProject():
  """Returns the value of the core/project config property.

  Config properties can be overridden with command line flags. If the --project
  flag was provided, this will return the value provided with the flag.
  """
  return properties.VALUES.core.project.Get(required=True)


def FabricID(fabric_id, location):
  """Convert a fabric_id to fabric canonical resource name.

  Args:
    fabric_id: An id of the existing fabric resource.
    location: location where resource will be created.

  Returns:
    A fabric resource canonical name.
  """
  if not fabric_id:
    return ""

  resources = fabric_id.split("/")
  if len(resources) == 1:
    return (
        "projects/"
        + GetProject()
        + "/locations/"
        + location
        + "/fabrics/"
        + fabric_id
    )

  return fabric_id


def DeploymentProjectID(deployment_project_id):
  """Convert a deployment project id  to projects canonical resource name.

  Args:
    deployment_project_id: An id of the existing fabric resource.

  Returns:
    A project resource canonical name.
  """
  if not deployment_project_id:
    return ""

  resources = deployment_project_id.split("/")
  if len(resources) == 1:
    return "projects/" + deployment_project_id

  return deployment_project_id


def GenerateCreateDeployment(_, args, create_req):
  """Construct the fabric id and deployment project canonical resource names.

  Args:
    _: A resource ref to the parsed Federation resource.
    args: The parsed args namespace from CLI.
    create_req: Create tdf deployment request for the API call.

  Returns:
    Modified request for the API call.
  """
  create_req.deployment.fabricId = FabricID(args.fabric_id, args.location)
  create_req.deployment.projectId = DeploymentProjectID(args.deployment_project)
  return create_req
