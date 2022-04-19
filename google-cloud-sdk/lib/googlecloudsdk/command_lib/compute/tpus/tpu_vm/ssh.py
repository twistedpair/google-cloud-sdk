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
from googlecloudsdk.command_lib.compute import iap_tunnel
from googlecloudsdk.command_lib.compute.tpus.tpu_vm import exceptions as tpu_exceptions
from googlecloudsdk.command_lib.util.ssh import ssh
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log

import six

SSH_KEYS_METADATA_KEY = 'ssh-keys'

IAP_TROUBLESHOOTING_HELP = """
Please ensure that this TPU was created after March 24, 2022. If it is, check
that you have allowed IAP to connect to instances in your
firewall (https://cloud.google.com/iap/docs/using-tcp-forwarding#create-firewall-rule),
and that the TPU is in READY state with HEALTHY health.
"""


def AddTPUSSHArgs(parser, enable_iap):
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
  if enable_iap:
    routing_group = parser.add_mutually_exclusive_group()
    routing_group.add_argument(
        '--internal-ip',
        action='store_true',
        help="""\
            Connect to TPU VMs using their internal IP addresses rather than their
            external IP addresses. Use this to connect from a Google Compute
            Engine VM to a TPU VM on the same VPC network, or between two peered
            VPC networks.
            """)
    routing_group.add_argument(
        '--tunnel-through-iap',
        action='store_true',
        help="""\
        Tunnel the SSH connection through Cloud Identity-Aware Proxy for TCP
        forwarding.

        This flag must be specified to attempt to connect via IAP tunneling. If it
        is not set, and connection to a Cloud TPU VM without external IP address
        is attempted from outside the network, then the command will fail.

        To use IAP tunneling, there must be firewall access to the SSH port for
        the IAP TCP IP address range for the network the TPU is created in. See
        the [user guide](https://cloud.google.com/iap/docs/using-tcp-forwarding)
        for more details.

        To learn more, see the
        [IAP for TCP forwarding documentation](https://cloud.google.com/iap/docs/tcp-forwarding-overview).
        """)
  else:
    parser.add_argument(
        '--internal-ip',
        action='store_true',
        help="""\
            Connect to TPU VMs using their internal IP addresses rather than their
            external IP addresses. Use this to connect from a Google Compute
            Engine VM to a TPU VM on the same VPC network, or between two peered
            VPC networks.
            """)


def ValidateTPUState(state, state_enum):
  """Validates the TPU's state.

  Prints warnings or throws exceptions when appropriate.

  Args:
    state: the state of the TPU.
    state_enum: the enum for all TPU states.
  """
  if state is state_enum.READY:
    # This is the base case.
    pass
  elif state is state_enum.STATE_UNSPECIFIED:
    log.warning(
        'The TPU VM is in state "{}", therefore the TPU may not be available '
        'or reachable.'.format(state))
  elif state in [
      state_enum.CREATING, state_enum.STARTING, state_enum.REPAIRING,
      state_enum.HIDING, state_enum.UNHIDING
  ]:
    log.warning(
        'The TPU VM is in state "{}", therefore the TPU may not be available '
        'or reachable. If the connection fails, please try again later.'.format(
            state))
  elif state in [
      state_enum.STOPPED, state_enum.STOPPING, state_enum.DELETING,
      state_enum.HIDDEN
  ]:
    raise tpu_exceptions.TPUInUnusableState(state)
  elif state in [state_enum.PREEMPTED, state_enum.TERMINATED]:
    raise tpu_exceptions.TPUInUnusableTerminalState(state)


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


def _ParseHostKeySuffixes(guest_attributes):
  """Returns the host key suffixes."""
  host_key_suffixes = []
  for worker_guest_attributes in guest_attributes:
    for item in worker_guest_attributes.queryValue.items:
      if item.key == 'ssh-ed25519':
        host_key_suffixes.append(item.value[-6:])
        break
  return host_key_suffixes


def _ParseSingleHostKeySuffix(guest_attributes, worker_count, worker):
  """Returns a list with only a single worker's host key suffix populated."""
  suffixes = [''] * worker_count
  for item in guest_attributes[0].queryValue.items:
    if item.key == 'ssh-ed25519':
      suffixes[worker] = item.value[-6:]
      break
  return suffixes


def GetFromGuestAttributes(guest_attributes, worker, key):
  for item in guest_attributes[worker].queryValue.items:
    if item.key == key:
      return item.value
  return None


def GetHostKeySuffixes(
    guest_attributes, worker_count=None, worker_id=None):
  """Retrieves the host key suffixes for the TPU workers."""
  if worker_count and worker_id:
    return _ParseSingleHostKeySuffix(guest_attributes, worker_count, worker_id)
  else:
    return _ParseHostKeySuffixes(guest_attributes)


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
    log.debug('ssh-keygen exited with error {}'.format(err.getvalue()))
    log.warning('Cannot generate fingerprint of SSH key. Command may stall.')
    return
  fingerprint_entry = keygen_out.getvalue()
  if len(fingerprint_entry.split()) <= 1:
    log.debug('ssh-keygen returned fingerprint entry in invalid format: "{}"'
              ''.format(fingerprint_entry))
    return
  # Only use the actual fingerprint part of the fingerprint entry.
  fingerprint = fingerprint_entry.split()[1]

  # Get keys in agent.
  cmd = ['ssh-add', '-l']
  out = io.StringIO()
  retcode = execution_utils.Exec(
      cmd, no_exit=True, out_func=out.write, err_func=err.write)
  if retcode != 0:
    log.debug('ssh-add exited with error {}'.format(err.getvalue()))
    log.warning('Cannot retrieve keys in ssh-agent. Command may stall.')
    return

  if fingerprint not in out.getvalue():
    raise tpu_exceptions.SSHKeyNotInAgent(identity_file)


def CreateSshTunnelArgs(args, track, project, zone, instance):
  """Construct an SshTunnelArgs object from command line args and values."""
  # If tunneling through IAP is not available or specified, then abort.
  if not args.IsKnownAndSpecified('tunnel_through_iap'):
    return None

  res = iap_tunnel.SshTunnelArgs()

  res.track = track.prefix
  res.project = project.name
  res.zone = zone
  res.instance = instance

  return res


def AttemptRunWithRetries(command_name, worker, exit_statuses, cmd, env,
                          output_file, multiple_workers, run_cmd):
  """Attempts to connect to a worker using SSH or SCP."""
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
      exit_status = run_cmd(env, cmd, output_file)
      if exit_status:
        # This is the exit status of the remote command.  Problems with SSH
        # itself will result in ssh.CommandError being raised above.
        if multiple_workers:
          log.status.Print('##### Command execution on worker {} failed '
                           'with exit status {}. Continuing.'
                           ''.format(worker, exit_status))
          # Store the exit status in list so that we can check it in the main
          # thread.
          exit_statuses[worker] = exit_status
        sys.exit(exit_status)
    except ssh.CommandError as e:
      if i == max_attempts - 1:
        if multiple_workers:
          # We need to store the exit status, since the exception will not be
          # caught by the calling thread.
          exit_statuses[worker] = 255
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
