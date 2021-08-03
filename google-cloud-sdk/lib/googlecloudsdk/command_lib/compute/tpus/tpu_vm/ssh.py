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
"""SSH/SCP utilities for Cloud TPU VM commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import sys
import time

from apitools.base.py import encoding_helper
from apitools.base.py.exceptions import HttpConflictError
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute.tpus.tpu_vm import exceptions as tpu_exceptions
from googlecloudsdk.command_lib.util.ssh import ssh
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log

import six

SSH_KEYS_METADATA_KEY = 'ssh-keys'


def AddTPUSSHArgs(parser):
  """Arguments that are common and specific to both TPU VM SSH and SCP."""
  parser.add_argument(
      '--worker',
      default='0',
      help="""\
          TPU worker to connect to. The supported value is a single 0-based
          index of the worker in the case of a TPU Pod. When also using the
          `--command` flag, it additionally supports a comma-separated list
          (e.g. '1,4,6'), range (e.g. '1-3'), or special keyword ``all" to
          run the command concurrently on each of the specified workers.

          Note that when targeting multiple workers, you should run 'ssh-add'
          with your private key prior to executing the gcloud command. Default:
          'ssh-add ~/.ssh/google_compute_engine'.
          """)
  parser.add_argument(
      '--internal-ip',
      action='store_true',
      help="""\
          Connect to TPU VMs using their internal IP addresses rather than their
          external IP addresses. Use this to connect from a Google Compute
          Engine VM to a TPU VM on the same VPC network, or between two peered
          VPC networks.
          """)


class IPAddresses():
  """Worker is a holder for the worker IP addresses."""

  def __init__(self, ip_address, internal_address):
    self.ip_address = ip_address
    self.internal_address = internal_address


def ParseWorkerFlag(worker_flag, network_endpoints, use_internal_ips):
  """Parses the --worker flag into a dict of worker indexes to IP addresses."""
  n_vms = len(network_endpoints)
  if six.text_type(worker_flag).upper() == 'ALL':
    indexes = list(range(n_vms))
  else:
    indexes = set()
    ranges = worker_flag.split(',')
    for r in ranges:
      if not r:
        continue
      if '-' in r:
        bounds = r.split('-')
        if len(bounds) != 2 or not bounds[0] or not bounds[1]:
          raise exceptions.InvalidArgumentException(
              '--worker', 'found malformed range "{}".'.format(r))
        start, end = int(bounds[0]), int(bounds[1])
        if start >= end:
          raise exceptions.InvalidArgumentException(
              '--worker', 'found malformed range "{}".'.format(r))
        indexes.update(range(start, end + 1))
      else:
        try:
          indexes.add(int(r))
        except ValueError:
          raise exceptions.InvalidArgumentException(
              '--worker', 'unable to parse worker ID {}. Please only use'
              'numbers.'.format(r))

  if not indexes:
    raise exceptions.InvalidArgumentException(
        '--worker', 'no worker specified, or none were parsed from the '
        'argument value.')

  mx = max(indexes)
  if mx >= n_vms:
    raise exceptions.InvalidArgumentException(
        '--worker', 'worker index {} is larger than the valid worker indexes '
        'on this TPU VM. Please only use indexes in the range [0, {}], '
        'inclusive.'.format(mx, n_vms - 1))

  # Get the VMs' IP addresses.
  worker_ips = {}
  for worker in indexes:
    internal_address = network_endpoints[worker].ipAddress
    if (not use_internal_ips and network_endpoints[worker].accessConfig and
        network_endpoints[worker].accessConfig.externalIp):
      ip_address = network_endpoints[worker].accessConfig.externalIp
    else:
      ip_address = internal_address
    worker_ips[worker] = IPAddresses(ip_address, internal_address)
  return worker_ips


def _ParseHostKeySuffixes(guest_attributes_response):
  """Returns the host key suffixes."""
  host_key_suffixes = []
  for guest_attributes in guest_attributes_response.guestAttributes:
    for item in guest_attributes.queryValue.items:
      if item.key == 'ssh-ed25519':
        host_key_suffixes.append(item.value[-6:])
        break
  return host_key_suffixes


def _ParseSingleHostKeySuffix(guest_attributes_response, worker_count, worker):
  """Returns a list with only a single worker's host key suffix populated."""
  suffixes = [''] * worker_count
  for item in guest_attributes_response.guestAttributes[0].queryValue.items:
    if item.key == 'ssh-ed25519':
      suffixes[worker] = item.value[-6:]
      break
  return suffixes


def GetHostKeySuffixes(tpu_helper, tpu_name, worker_ips, worker_count, zone):
  """Retrieves the host key suffixes for the TPU workers."""
  single_pod_worker = worker_count > 1 and len(worker_ips) == 1
  if single_pod_worker:
    # Retrieve only that worker's GuestAttributes.
    worker_id = list(worker_ips)[0]
    guest_attributes_response = tpu_helper.GetGuestAttributes(
        tpu_name, zone, str(worker_id))
    host_key_suffixes = _ParseSingleHostKeySuffix(
        guest_attributes_response, worker_count, worker_id)
  else:
    guest_attributes_response = tpu_helper.GetGuestAttributes(tpu_name, zone)
    host_key_suffixes = _ParseHostKeySuffixes(guest_attributes_response)
  return host_key_suffixes


def TpuHasOsLoginEnabled(node):
  """Returns true if the node has OSLogin enabled."""
  node_dict = encoding_helper.MessageToDict(node)
  if 'metadata' in node_dict and 'enable-oslogin' in node_dict['metadata']:
    return node_dict['metadata']['enable-oslogin'].upper() == 'TRUE'
  return False


def _MetadataHasSSHKey(metadata, public_key):
  """Returns true if the metadata has the SSH key.

  Args:
    metadata: Project metadata.
    public_key: The SSH key.

  Returns:
    True if present, False if not present.
  """
  if not (metadata and metadata.items):
    return False
  matching_values = [
      item.value for item in metadata.items if item.key == SSH_KEYS_METADATA_KEY
  ]
  if not matching_values:
    return False
  return public_key in matching_values[0]


def AddSSHKeyIfNeeded(project, tpu_helper, node, tpu_name, zone, public_key):
  """Verifies that instance has SSH key, and adds it in case it doesn't."""
  # Args: node, project, SSH key?
  # 1. Check the project metadata for the key.
  if _MetadataHasSSHKey(project.commonInstanceMetadata, public_key):
    log.status.Print(
        'SSH key found in project metadata; not updating instance.')
    return
  # 2. Check the instance metadata for the key.
  node_dict = encoding_helper.MessageToDict(node)
  ssh_keys = ''
  if 'metadata' in node_dict and SSH_KEYS_METADATA_KEY in node_dict['metadata']:
    ssh_keys = node_dict['metadata'][SSH_KEYS_METADATA_KEY]
  if public_key in ssh_keys:
    log.debug('SSH key found in instance metadata; not updating instance.')
    return
  # 3. Call update node if not present.
  ssh_keys += '\n' + public_key
  node_for_update = tpu_helper.messages.Node(
      metadata=tpu_helper.UpdateMetadataKey(
          metadata=node.metadata, key=SSH_KEYS_METADATA_KEY, value=ssh_keys))
  try:
    tpu_helper.UpdateNode(tpu_name, zone, node_for_update, 'metadata')
  except HttpConflictError:
    # Do not fail the SSH if there is already an UpdateNode call in flight.
    pass


def GetInstanceID(node_id, worker, host_key_suffixes):
  instance_id = 'tpu.{}-{}'.format(node_id, worker)
  if len(host_key_suffixes) > worker:
    instance_id += '-{}'.format(host_key_suffixes[worker])
  return instance_id


def VerifyKeyInAgent(identity_file):
  """Verifies that the ssh-agent holds the SSH key."""
  # Generate key fingerprint.
  cmd = ['ssh-keygen', '-lf', identity_file]
  keygen_out = io.StringIO()
  err = io.StringIO()
  retcode = execution_utils.Exec(
      cmd, no_exit=True, out_func=keygen_out.write, err_func=err.write)
  if retcode != 0:
    log.debug('ssh-keygen exited with error {}', err.getvalue())
    log.warning('Cannot generate fingerprint of SSH key. Command may stall.')
    return
  fingerprint = keygen_out.getvalue()

  # Get keys in agent.
  cmd = ['ssh-add', '-l']
  out = io.StringIO()
  retcode = execution_utils.Exec(
      cmd, no_exit=True, out_func=out.write, err_func=err.write)
  if retcode != 0:
    log.debug('ssh-add exited with error {}', err.getvalue())
    log.warning('Cannot retrieve keys in ssh-agent. Command may stall.')
    return

  if fingerprint not in out.getvalue():
    raise tpu_exceptions.SSHKeyNotInAgent(identity_file)


def AttemptRunWithRetries(command_name, worker, cmd, env, output_file,
                          multiple_workers, run_cmd):
  """Attempts to connect to a worker using SSH."""
  max_attempts = 10
  sleep_interval = 5
  # Since SSH keys may have recently been set in the instance's metadata by
  # the UpateNode call, it can take some time before those are propagated
  # correctly and the SSH command's authorization is successful. Therefore,
  # we wrap this in a retry loop. No exponential back-off is needed here, as
  # we're not looking to throttle.
  for i in range(max_attempts):
    try:
      log.status.Print('{}: Attempting to connect to worker {}...'.format(
          command_name, worker))
      return_code = run_cmd(env, cmd, output_file)
      if return_code:
        # This is the return code of the remote command.  Problems with SSH
        # itself will result in ssh.CommandError being raised above.
        if multiple_workers:
          log.status.Print('##### Command execution on worker {} failed '
                           'with return code {}. Continuing.'
                           ''.format(worker, return_code))
        sys.exit(return_code)
    except ssh.CommandError as e:
      if i == max_attempts - 1:
        raise e
      if multiple_workers:
        log.status.Print('Failed to execute command on multiple workers. '
                         'This may have happened if you have not added '
                         'your SSH key to your ssh-agent using "ssh-add '
                         '~/.ssh/google_compute_engine".')
      log.status.Print('Retrying: {} command error: {}'.format(
          command_name, six.text_type(e)))
      time.sleep(sleep_interval)
      continue
    break
