# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Utility file that contains helpers for the Cloud TPU Execution groups."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import os
import sys

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute.operations import poller
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute import scope as compute_scope
from googlecloudsdk.command_lib.compute import ssh_utils
from googlecloudsdk.command_lib.compute.instances import flags as instance_flags
from googlecloudsdk.command_lib.projects import util as p_util
from googlecloudsdk.command_lib.util.ssh import ssh
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import retry
from googlecloudsdk.core.util import times


class TPUNode(object):
  """Helper to create and modify TPU nodes."""

  def __init__(self, release_track):
    if release_track == base.ReleaseTrack.ALPHA:
      self._api_version = 'v1alpha1'
    elif release_track == base.ReleaseTrack.BETA:
      self._api_version = 'v1beta1'
    else:
      self._api_version = 'v1'
    self.client = apis.GetClientInstance('tpu', self._api_version)
    self.messages = apis.GetMessagesModule('tpu', self._api_version)

  def _CreateDefaultNode(self, accelerator_type, tf_version):
    node = self.messages.Node()
    node.acceleratorType = accelerator_type
    node.network = ''
    node.tensorflowVersion = tf_version
    return node

  def _GetTpuOperationRef(self, operation):
    """Get a resource reference to a long running operation."""
    return resources.REGISTRY.ParseRelativeName(
        operation.name, collection='tpu.projects.locations.operations')

  def Create(self, name, accelerator_type, tf_version, zone):
    """Create builds and issues a request to create a TPU node.

    Args:
      name: Name of the TPU Node to be created.
      accelerator_type: Slice type of TPU accelerator like 'v2-8', 'v2-32'.
      tf_version: Tensorflow Version like '1.1', '1.5'.
      zone: Zone to create the TPU Node in.
    Returns:
      A TPU Create response which needs to be polled on.
    """
    project = properties.VALUES.core.project.Get(required=True)
    request = self.messages.TpuProjectsLocationsNodesCreateRequest(
        parent='projects/{}/locations/{}'.format(project, zone),
        nodeId=name,
        node=self._CreateDefaultNode(accelerator_type, tf_version))
    operation = self.client.projects_locations_nodes.Create(request)
    return self._GetTpuOperationRef(operation)

  def WaitForOperation(self, operation_ref, message):
    operation_poller = waiter.CloudOperationPoller(
        self.client.projects_locations_nodes,
        self.client.projects_locations_operations)
    return waiter.WaitFor(operation_poller, operation_ref, message)


class Instance(object):
  """Helper to create the GCE VM required to work with the TPU Node."""

  def __init__(self, release_track):
    holder = base_classes.ComputeApiHolder(release_track)
    self.client = holder.client.apitools_client
    self.messages = holder.client.messages

  def _BuildInstanceSpec(
      self, name, zone, machine_type, disk_size, preemptible):
    """Builds an instance spec to be used for Instance creation."""

    disk = self.messages.AttachedDisk(
        boot=True,
        autoDelete=True,
        initializeParams=self.messages.AttachedDiskInitializeParams(
            sourceImage='projects/ml-images/global/images/debian-10-tf-nightly-v20200403',
            diskSizeGb=disk_size
        ))
    project_number = p_util.GetProjectNumber(
        properties.VALUES.core.project.Get(required=True))
    network_interface = self.messages.NetworkInterface(
        network='projects/{}/global/networks/default'.format(project_number),
        accessConfigs=[self.messages.AccessConfig(
            name='External NAT',
            type=self.messages.AccessConfig.TypeValueValuesEnum.ONE_TO_ONE_NAT)]
        )
    metadata = [self.messages.Metadata.ItemsValueListEntry(
        key='ctpu',
        value=name)]
    service_account = self.messages.ServiceAccount(
        email='default',
        scopes=[
            'https://www.googleapis.com/auth/devstorage.read_write',
            'https://www.googleapis.com/auth/logging.write',
            'https://www.googleapis.com/auth/monitoring.write',
            'https://www.googleapis.com/auth/cloud-platform'
        ])
    labels = self.messages.Instance.LabelsValue(additionalProperties=[
        self.messages.Instance.LabelsValue.AdditionalProperty(
            key='ctpu', value=name)
    ])

    return self.messages.Instance(
        name=name,
        metadata=self.messages.Metadata(items=metadata),
        machineType='zones/{}/machineTypes/{}'.format(zone, machine_type),
        disks=[disk],
        scheduling=self.messages.Scheduling(preemptible=preemptible),
        networkInterfaces=[network_interface],
        labels=labels,
        serviceAccounts=[service_account])

  def _GetComputeZoneOperationRef(self, operation):
    """Get a resource reference to a long running operation."""
    return resources.REGISTRY.Parse(
        operation.selfLink, collection='compute.zoneOperations')

  def Create(self, name, zone, machine_type, disk_size, preemptible):
    """Issue request to create an Instance."""
    request = self.messages.ComputeInstancesInsertRequest(
        project=properties.VALUES.core.project.Get(required=True),
        zone=zone,
        instance=self._BuildInstanceSpec(
            name, zone, machine_type, disk_size, preemptible))
    operation = self.client.instances.Insert(request)
    return self._GetComputeZoneOperationRef(operation)

  def WaitForOperation(self, operation_ref, message):
    """Wait for Instance operation to complete."""
    operation_poller = poller.Poller(self.client.instances)
    return waiter.WaitFor(operation_poller, operation_ref, message)


class SSH(object):
  """Helper class to SSH to the VM associated with the TPU node."""

  def __init__(self, release_track):
    holder = base_classes.ComputeApiHolder(release_track)
    self.client = holder.client
    self.resources = holder.resources

  def _DefaultArgsForSSH(self, args):
    # These arguments are not exposed to the user but are required in
    # order to use the SSH Utils.
    args.plain = None
    args.strict_host_key_checking = 'no'
    args.force_key_file_overwrite = None
    args.ssh_key_file = None
    return args

  def _GetHostKeyFromInstance(self, zone, ssh_helper, instance):
    """Wrapper around SSH Utils to get the host keys for SSH."""
    instance_ref = instance_flags.SSH_INSTANCE_RESOLVER.ResolveResources(
        [instance.name], compute_scope.ScopeEnum.ZONE, zone,
        self.resources,
        scope_lister=instance_flags.GetInstanceZoneScopeLister(self.client))[0]
    project = ssh_helper.GetProject(self.client, instance_ref.project)
    host_keys = ssh_helper.GetHostKeysFromGuestAttributes(
        self.client, instance_ref, instance, project)

    if host_keys is not None and not host_keys:
      # Only display this message if there was an attempt to retrieve
      # host keys but it was unsuccessful(yielded empty dict). If Guest
      # Attributes is disabled, there is no attempt to retrieve host keys.
      log.status.Print('Unable to retrieve host keys from instance metadata. '
                       'Continuing.')
    return host_keys

  def _GetSSHOptions(self, name, ssh_helper, instance, host_keys):
    options = ssh_helper.GetConfig(ssh_utils.HostKeyAlias(instance),
                                   strict_host_key_checking='no',
                                   host_keys_to_add=host_keys)
    os.environ['TPU_NAME'] = name
    options['SendEnv'] = 'TPU_NAME'
    return options

  def _WaitForSSHKeysToPropagate(
      self, ssh_helper, remote, identity_file, user, instance, options):
    """Waits for SSH keys to propagate in order to SSH to the instance."""
    ssh_helper.EnsureSSHKeyExists(
        self.client, user, instance,
        ssh_helper.GetProject(
            self.client, properties.VALUES.core.project.Get(required=True)),
        times.Now() + datetime.timedelta(seconds=300))
    ssh_poller = ssh.SSHPoller(
        remote=remote,
        identity_file=identity_file, options=options, max_wait_ms=120*1000)
    try:
      ssh_poller.Poll(ssh_helper.env, force_connect=True)
    except retry.WaitException:
      raise ssh_utils.NetworkError()

  def SSHToInstance(self, args, instance):
    """Helper to manage authentication followed by SSH to the instance."""
    args = self._DefaultArgsForSSH(args)

    external_nat = ssh_utils.GetExternalIPAddress(instance)
    log.status.Print(
        'Trying to SSH to GCE Green VM with NAT IP:{}'.format(external_nat))
    remote = ssh.Remote(external_nat, ssh.GetDefaultSshUsername())
    args.ssh_key_file = ssh.Keys.DEFAULT_KEY_FILE

    ssh_helper = ssh_utils.BaseSSHCLIHelper()
    ssh_helper.Run(args)
    identity_file = ssh_helper.keys.key_file

    user, _ = ssh_utils.GetUserAndInstance(args.name)
    host_keys = self._GetHostKeyFromInstance(
        args.zone, ssh_helper, instance)
    options = self._GetSSHOptions(args.name, ssh_helper, instance, host_keys)
    self._WaitForSSHKeysToPropagate(
        ssh_helper, remote, identity_file, user, instance, options)

    extra_flags = []
    # Ctpu seems to be forwarding some other ports on what
    # seems like the TPU node. Need to understand better before enabling.
    if args.forward_ports:
      extra_flags.extend(
          ['-A', '-L', '6006:localhost:6006', '-L', '8888:localhost:8888'])
    ssh_cmd_args = {
        'remote': remote,
        'identity_file': identity_file,
        'options': options,
        'extra_flags': extra_flags
    }
    cmd = ssh.SSHCommand(**ssh_cmd_args)
    # Errors from SSH itself result in an ssh.CommandError being raised
    return_code = cmd.Run(ssh_helper.env, force_connect=True)
    if return_code:
      # This is the return code of the remote command.  Problems with SSH itself
      # will result in ssh.CommandError being raised above.
      sys.exit(return_code)
