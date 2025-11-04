# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Library to SSH into a Cloud Run Deployment."""

import argparse
import enum
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.compute import iap_tunnel


def ProjectIdToProjectNumber(project_id):
  """Returns the Cloud project number associated with the `project_id`."""
  crm_message_module = apis.GetMessagesModule("cloudresourcemanager", "v1")
  resource_manager = apis.GetClientInstance("cloudresourcemanager", "v1")
  req = crm_message_module.CloudresourcemanagerProjectsGetRequest(
      projectId=project_id
  )
  project = resource_manager.projects.Get(req)
  return project.projectNumber


def CreateSshTunnelArgs(
    track,
    project_number,
    deployment_name,
    workload_type,
    instance_id=None,
    container_id=None,
):
  """Construct an SshTunnelArgs from command line args and values.

  Args:
    track: ReleaseTrack, The currently running release track.
    project_number: str, the project number (string with digits).
    deployment_name: str, the name of the deployment.
    workload_type: Ssh.WorkloadType, the type of the workload.
    instance_id: str, the instance id (optional).
    container_id: str, the container id (optional).

  Returns:
    SshTunnelArgs.
  """

  cloud_run_args = {}
  cloud_run_args["deployment_name"] = deployment_name
  cloud_run_args["workload_type"] = workload_type
  cloud_run_args["project_number"] = project_number
  if instance_id:
    cloud_run_args["instance_id"] = instance_id
  if container_id:
    cloud_run_args["container_id"] = container_id

  res = iap_tunnel.SshTunnelArgs()
  res.track = track.prefix
  res.cloud_run_args = cloud_run_args

  return res


class Ssh:
  """SSH into a Cloud Run Deployment."""

  class WorkloadType(enum.Enum):
    """The type of the deployment."""

    WORKER_POOL = "worker_pool"
    JOB = "job"
    SERVICE = "service"

  def __init__(self, args: argparse.Namespace, workload_type: WorkloadType):
    """Initialize the SSH library."""
    self.deployment_name = args.deployment_name
    self.workload_type = workload_type
    self.project = args.project
    self.project_number = ProjectIdToProjectNumber(args.project)
    self.instance = getattr(args, "instance", None)
    self.container = getattr(args, "container", None)
    self.region = args.region
    self.release_track = args.release_track

  def Run(self):
    """Run the SSH command."""

    CreateSshTunnelArgs(
        self.release_track,
        self.project_number,
        self.deployment_name,
        self.workload_type,
        self.instance,
        self.container,
    )
