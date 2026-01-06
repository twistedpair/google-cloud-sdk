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
import json
import subprocess
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.compute import iap_tunnel
from googlecloudsdk.command_lib.compute import ssh_utils
from googlecloudsdk.command_lib.util.ssh import ssh


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
    project,
    deployment_name,
    workload_type,
    region,
    instance_id=None,
    container_id=None,
    iap_tunnel_url_override=None,
):
  """Construct an SshTunnelArgs from command line args and values.

  Args:
    track: ReleaseTrack, The currently running release track.
    project_number: str, the project number (string with digits).
    project: str, the project id.
    deployment_name: str, the name of the deployment.
    workload_type: Ssh.WorkloadType, the type of the workload.
    region: str, the region of the deployment.
    instance_id: str, the instance id (optional).
    container_id: str, the container id (optional).
    iap_tunnel_url_override: str, the IAP tunnel URL override (optional).

  Returns:
    SshTunnelArgs.
  """

  cloud_run_args = {}
  cloud_run_args["deployment_name"] = deployment_name
  cloud_run_args["workload_type"] = workload_type
  cloud_run_args["project_number"] = project_number
  cloud_run_args["instance_id"] = instance_id
  cloud_run_args["container_id"] = container_id

  res = iap_tunnel.SshTunnelArgs()
  res.track = track.prefix
  res.cloud_run_args = cloud_run_args
  res.region = region
  res.project = project

  if iap_tunnel_url_override:
    res.pass_through_args.append(
        "--iap-tunnel-url-override=" + iap_tunnel_url_override)

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
    self.iap_tunnel_url_override = getattr(
        args, "iap_tunnel_url_override", None
    )
    self.service_account = self._GetServiceAccountFromWorkload()

  def _GetServiceAccountFromWorkload(self):
    """Retrieves the service account from the Cloud Run workload."""
    command = ["gcloud"]

    if self.workload_type == self.WorkloadType.SERVICE:
      command.extend(["run", "services", "describe"])
    elif self.workload_type == self.WorkloadType.WORKER_POOL:
      command.extend(["beta", "run", "worker-pools", "describe"])
    elif self.workload_type == self.WorkloadType.JOB:
      command.extend(["run", "jobs", "describe"])
    else:
      raise ValueError(f"Unsupported workload type: {self.workload_type}")

    command.extend([
        self.deployment_name,
        "--region",
        self.region,
        "--project",
        self.project,
        "--format",
        "json",
    ])
    try:
      output = subprocess.check_output(command, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
      raise ValueError(
          f"Error describing deployment: {e.stderr.decode('utf-8')}"
      ) from e
    else:
      service_data = json.loads(output)
      template = service_data.get("spec", {}).get("template", {})
      execution_environment = (
          template.get("metadata", {})
          .get("annotations", {})
          .get("run.googleapis.com/execution-environment")
      )
      if execution_environment == "gen1":
        raise ValueError("SSH is not supported for Cloud Run gen1 deployments.")
      service_account = template.get("spec", {}).get("serviceAccountName")
      if not service_account:
        raise ValueError("Service account not found for workload.")
      return service_account

  def HostKeyAlias(self):
    """Returns the host key alias for the SSH connection."""
    if self.instance and self.container:
      return "cloud-run-{}-{}".format(self.instance, self.container)
    else:
      return "cloud-run-default"

  def Run(self):
    """Run the SSH command."""
    env = ssh.Environment.Current()
    env.RequireSSH()
    keys = ssh.Keys.FromFilename()
    keys.EnsureKeysExist(overwrite=False)
    user = "root"

    # Note: this actually creates the certificate.
    ssh.GetOsloginState(
        None,
        None,
        user,
        keys.GetPublicKey().ToEntry(),
        None,
        self.release_track,
        cloud_run_params={
            "deployment_name": self.deployment_name,
            "project_id": self.project,
            "region": self.region,
            "service_account": self.service_account,
        },
    )
    cert_file = ssh.CertFileFromCloudRunDeployment(
        project=self.project,
        region=self.region,
        deployment=self.deployment_name,
    )
    dest_addr = self.HostKeyAlias()
    remote = ssh.Remote(dest_addr, user)

    iap_tunnel_args = CreateSshTunnelArgs(
        self.release_track,
        self.project_number,
        self.project,
        self.deployment_name,
        self.workload_type,
        self.region,
        self.instance,
        self.container,
        self.iap_tunnel_url_override,
    )

    ssh_helper = ssh_utils.BaseSSHCLIHelper()
    ssh_options = ssh_helper.GetConfig(
        host_key_alias=dest_addr,
        strict_host_key_checking="no",
    )

    return ssh.SSHCommand(
        remote=remote,
        cert_file=cert_file,
        iap_tunnel_args=iap_tunnel_args,
        options=ssh_options,
        identity_file=keys.key_file,
    ).Run(env)
