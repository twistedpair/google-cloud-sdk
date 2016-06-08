# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Utilities for subcommands that need to SSH into virtual machine guests."""
import errno
import getpass
import logging
import os
import re

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.compute import gaia_utils
from googlecloudsdk.api_lib.compute import metadata_utils
from googlecloudsdk.api_lib.compute import path_simplifier
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import time_utils
from googlecloudsdk.api_lib.compute import user_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms
from googlecloudsdk.third_party.py27 import py27_subprocess as subprocess

# The maximum amount of time to wait for a newly-added SSH key to
# propagate before giving up.
_SSH_KEY_PROPAGATION_TIMEOUT_SEC = 60


# `ssh` exits with this exit code in the event of an SSH error (as opposed to a
# successful `ssh` execution where the *command* errored).
_SSH_ERROR_EXIT_CODE = 255

# Normally, all SSH output is simply returned to the user (or sent to
# /dev/null if user output is disabled). For testing, this value can be
# overridden with a file path.
SSH_OUTPUT_FILE = None


class SetProjectMetadataError(core_exceptions.Error):
  pass


class SshLikeCmdFailed(core_exceptions.Error):
  """Raise for a failure when invoking ssh, scp, or similar."""

  def __init__(self, cmd, message=None, return_code=None):
    if not (message or return_code):
      raise ValueError('One of message and return_code is required.')

    self.cmd = cmd

    message_text = '[{0}]'.format(message) if message else None
    return_code_text = ('return code [{0}]'.format(return_code)
                        if return_code else None)
    why_failed = ' and '.join(filter(None, [message_text, return_code_text]))

    super(SshLikeCmdFailed, self).__init__(
        '[{0}] exited with {1}. See '
        'https://cloud.google.com/compute/docs/troubleshooting#ssherrors '
        'for troubleshooting hints.'.format(self.cmd, why_failed),
        exit_code=return_code)


def _IsValidSshUsername(user):
  # All characters must be ASCII, and no spaces are allowed
  # This may grant false positives, but will prevent backwards-incompatible
  # behavior.
  return all(ord(c) < 128 and c != ' ' for c in user)


def _WarnOrReadFirstKeyLine(path, kind):
  """Returns the first line from the key file path.

  A None return indicates an error and is always accompanied by a log.warn
  message.

  Args:
    path: The path of the file to read from.
    kind: The kind of key file, 'private' or 'public'.

  Returns:
    None (and prints a log.warn message) if the file does not exist, is not
    readable, or is empty. Otherwise returns the first line utf8 decoded.
  """
  try:
    with open(path) as f:
      # Decode to utf8 to handle any unicode characters. Key data is base64
      # encoded so it cannot contain any unicode. Comments may contain unicode,
      # but they are ignored in the key file analysis here, so replacing invalid
      # chars with ? is OK.
      line = f.readline().strip().decode('utf8', 'replace')
      if line:
        return line
      msg = 'is empty'
  except IOError as e:
    if e.errno == errno.ENOENT:
      msg = 'does not exist'
    else:
      msg = 'is not readable'
  log.warn('The %s SSH key file for Google Compute Engine %s.', kind, msg)
  return None


# TODO(user): This function can be dropped 1Q2017.
def _IsPublicKeyCorrupt95Through97(key):
  """Returns True if the encoded public key has the release 95.0.0 corruption.

  Windows corruption checks for release 95.0.0 through 97.0.0.
  Corrupt Windows encoded keys have these properties:
    type:       'ssh-rsa'
    exponent:   65537
    length:     256
    next byte:  bit 0x80 set
  A valid key either has exponent != 65537 or:
    type:       'ssh-rsa'
    exponent:   65537
    length:     257
    next byte:  0

  Args:
    key: The base64 encoded public key.

  Returns:
    True if the encoded public key has the release 95.0.0 corruption.
  """
  # The corruption only happened on Windows.
  if not IsRunningOnWindows():
    return False

  # All corrupt encodings have the same encoded prefix (up to the second to
  # last byte of the modulus size).
  prefix = 'AAAAB3NzaC1yc2EAAAADAQABAAAB'
  if not key.startswith(prefix):
    return False

  # The next 3 base64 chars determine the next 2 encoded bytes.
  modulus = key[len(prefix):len(prefix) + 3]
  # The last byte of the size must be 01 and the first byte of the modulus must
  # be 00, and that corresponds to one of two base64 encodings:
  if modulus in ('AQC', 'AQD'):
    return False

  # Looks bad.
  return True


def _KeyFilesAreValid(private=None, public=None):
  """Returns True if private and public pass minimum key file requirements.

  Args:
    private: The private key file path.
    public: The public key file path.

  Returns:
    True if private and public meet minumum key file requirements.
  """
  # The private key file must be readable and non-empty.
  if not _WarnOrReadFirstKeyLine(private, 'private'):
    return False

  # The PuTTY PPK key file must be readable and non-empty.
  if IsRunningOnWindows() and not _WarnOrReadFirstKeyLine(private + '.ppk',
                                                          'PuTTY PPK'):
    return False

  # The public key file must be readable and non-empty.
  public_line = _WarnOrReadFirstKeyLine(public, 'public')
  if not public_line:
    return False

  # The remaining checks are for the public key file.

  # Must have at least 2 space separated fields.
  fields = public_line.split(' ')
  if len(fields) < 2 or _IsPublicKeyCorrupt95Through97(fields[1]):
    log.warn('The public SSH key file for Google Compute Engine is corrupt.')
    return False

  # Looks OK.
  return True


def GetDefaultSshUsername(warn_on_account_user=False):
  """Returns the default username for ssh.

  The default username is the local username, unless that username is invalid.
  In that case, the default username is the username portion of the current
  account.

  Emits a warning if it's not using the local account username.

  Args:
    warn_on_account_user: bool, whether to warn if using the current account
      instead of the local username.

  Returns:
    str, the default SSH username.
  """
  user = getpass.getuser()
  if not _IsValidSshUsername(user):
    full_account = properties.VALUES.core.account.Get(required=True)
    account_user = gaia_utils.MapGaiaEmailToDefaultAccountName(full_account)
    if warn_on_account_user:
      log.warn('Invalid characters in local username [{0}]. '
               'Using username corresponding to active account: [{1}]'.format(
                   user, account_user))
    user = account_user
  return user


def UserHost(user, host):
  """Returns a string of the form user@host."""
  if user:
    return user + '@' + host
  else:
    return host


def GetExternalIPAddress(instance_resource, no_raise=False):
  """Returns the external IP address of the instance.

  Args:
    instance_resource: An instance resource object.
    no_raise: A boolean flag indicating whether or not to return None instead of
      raising.

  Raises:
    ToolException: If no external IP address is found for the instance_resource
      and no_raise is False.

  Returns:
    A string IP or None is no_raise is True and no ip exists.
  """
  if instance_resource.networkInterfaces:
    access_configs = instance_resource.networkInterfaces[0].accessConfigs
    if access_configs:
      ip_address = access_configs[0].natIP
      if ip_address:
        return ip_address
      elif not no_raise:
        raise exceptions.ToolException(
            'Instance [{0}] in zone [{1}] has not been allocated an external '
            'IP address yet. Try rerunning this command later.'.format(
                instance_resource.name,
                path_simplifier.Name(instance_resource.zone)))

  if no_raise:
    return None

  raise exceptions.ToolException(
      'Instance [{0}] in zone [{1}] does not have an external IP address, '
      'so you cannot SSH into it. To add an external IP address to the '
      'instance, use [gcloud compute instances add-access-config].'
      .format(instance_resource.name,
              path_simplifier.Name(instance_resource.zone)))


def _RunExecutable(cmd_args, strict_error_checking=True):
  """Run the given command, handling errors appropriately.

  Args:
    cmd_args: list of str, the arguments (including executable path) to run
    strict_error_checking: bool, whether a non-zero, non-255 exit code should be
      considered a failure.

  Returns:
    int, the return code of the command

  Raises:
    SshLikeCmdFailed: if the command failed (based on the command exit code and
      the strict_error_checking flag)
  """
  outfile = SSH_OUTPUT_FILE or os.devnull
  with open(outfile, 'w') as output_file:
    if log.IsUserOutputEnabled() and not SSH_OUTPUT_FILE:
      stdout, stderr = None, None
    else:
      stdout, stderr = output_file, output_file
    if IsRunningOnWindows() and not cmd_args[0].endswith('winkeygen.exe'):
      # TODO(user): b/25126583 will drop StrictHostKeyChecking=no and 'y'.
      # PuTTY and friends always prompt on fingerprint mismatch. A 'y' response
      # adds/updates the fingerprint registry entry and proceeds. The prompt
      # will appear once for each new/changed host. Redirecting stdin is not a
      # problem. Even interactive ssh is not a problem because a separate PuTTY
      # term is used and it ignores the calling process stdin.
      stdin = subprocess.PIPE
    else:
      stdin = None
    try:
      proc = subprocess.Popen(
          cmd_args, stdin=stdin, stdout=stdout, stderr=stderr)
      if stdin == subprocess.PIPE:
        # Max one prompt per host and there can't be more hosts than args.
        proc.communicate('y\n' * len(cmd_args))
      returncode = proc.wait()
    except OSError as e:
      raise SshLikeCmdFailed(cmd_args[0], message=e.strerror)
    if ((returncode and strict_error_checking) or
        returncode == _SSH_ERROR_EXIT_CODE):
      raise SshLikeCmdFailed(cmd_args[0], return_code=returncode)
    return returncode


def _GetMetadataKey(iam_ssh_keys):
  """Get the metadata key name for the desired SSH key metadata.

  There are four SSH key related metadata pairs:
  * Per-project 'sshKeys': this grants SSH access to VMs project-wide.
  * Per-instance 'sshKeys': this is used to grant access to an individual
    instance. For historical reasons, it acts as an override to the
    project-global value.
  * Per-instance 'block-project-ssh-keys': this determines whether 'ssh-keys'
    overrides or adds to the per-project 'sshKeys'
  * Per-instance 'ssh-keys': this also grants access to an individual
     instance, but acts in addition or as an override to the per-project
     'sshKeys' depending on 'block-project-ssh-keys'

  Args:
    iam_ssh_keys: bool. If False, give the name of the original SSH metadata key
        (that overrides the project-global SSH metadata key). If True, give the
        name of the IAM SSH metadata key (that works in conjunction with the
        project-global SSH key metadata).

  Returns:
    str, the corresponding metadata key name.
  """
  if iam_ssh_keys:
    metadata_key = constants.SSH_KEYS_INSTANCE_RESTRICTED_METADATA_KEY
  else:
    metadata_key = constants.SSH_KEYS_METADATA_KEY
  return metadata_key


def _GetSSHKeysFromMetadata(metadata, iam_keys=False):
  """Returns the value of the "sshKeys" metadata as a list."""
  if not metadata:
    return []
  for item in metadata.items:
    if item.key == _GetMetadataKey(iam_keys):
      return [key.strip() for key in item.value.split('\n') if key]
  return []


def _PrepareSSHKeysValue(ssh_keys):
  """Returns a string appropriate for the metadata.

  Values from are taken from the tail until either all values are
  taken or _MAX_METADATA_VALUE_SIZE_IN_BYTES is reached, whichever
  comes first. The selected values are then reversed. Only values at
  the head of the list will be subject to removal.

  Args:
    ssh_keys: A list of keys. Each entry should be one key.

  Returns:
    A new-line-joined string of SSH keys.
  """
  keys = []
  bytes_consumed = 0

  for key in reversed(ssh_keys):
    num_bytes = len(key + '\n')
    if bytes_consumed + num_bytes > constants.MAX_METADATA_VALUE_SIZE_IN_BYTES:
      log.warn('The following SSH key will be removed from your project '
               'because your sshKeys metadata value has reached its '
               'maximum allowed size of {0} bytes: {1}'
               .format(constants.MAX_METADATA_VALUE_SIZE_IN_BYTES, key))
    else:
      keys.append(key)
      bytes_consumed += num_bytes

  keys.reverse()
  return '\n'.join(keys)


def _AddSSHKeyToMetadataMessage(message_classes, user, public_key, metadata,
                                iam_keys=False):
  """Adds the public key material to the metadata if it's not already there."""
  entry = u'{user}:{public_key}'.format(
      user=user, public_key=public_key)

  ssh_keys = _GetSSHKeysFromMetadata(metadata, iam_keys=iam_keys)
  log.debug('Current SSH keys in project: {0}'.format(ssh_keys))

  if entry in ssh_keys:
    return metadata
  else:
    ssh_keys.append(entry)
    return metadata_utils.ConstructMetadataMessage(
        message_classes=message_classes,
        metadata={
            _GetMetadataKey(iam_keys): _PrepareSSHKeysValue(ssh_keys)},
        existing_metadata=metadata)


def IsRunningOnWindows():
  """Returns True if the current os is Windows."""
  current_os = platforms.OperatingSystem.Current()
  return current_os is platforms.OperatingSystem.WINDOWS


def ReadFile(file_path):
  """Returns the contents of the file or ''."""
  try:
    with open(file_path) as f:
      return f.read()
  except IOError as e:
    if e.errno == errno.ENOENT:
      return ''
    else:
      raise exceptions.ToolException('There was a problem reading [{0}]: {1}'
                                     .format(file_path, e.message))


def UpdateKnownHostsFile(known_hosts_file, hostname, host_key,
                         overwrite_keys=False):
  """Update the known_hosts file entry for the given hostname.

  If there is no entry for the give hostname, it will be added. If there is
  an entry already and overwrite_keys is False, nothing will be changed. If
  there is an entry and overwrite_keys is True, the key will be updated if it
  has changed.

  Args:
    known_hosts_file: str, The full path of the known_hosts file to update.
    hostname: str, The hostname for the known_hosts entry.
    host_key: str, The host key for the given hostname.
    overwrite_keys: bool, If true, will overwrite the entry corresponding to
      hostname with the new host_key if it already exists. If false and an
      entry already exists for hostname, will ignore the new host_key value.
  """
  known_hosts_contents = ReadFile(known_hosts_file)
  key_list = known_hosts_contents.splitlines()
  found_key_entry = None
  new_key_entry = '{0} {1}'.format(hostname, host_key)

  for key in key_list:
    if key.startswith(hostname):
      found_key_entry = key
      break

  if overwrite_keys and found_key_entry:
    if found_key_entry != new_key_entry:
      key_list.remove(found_key_entry)
      found_key_entry = None

  if not found_key_entry:
    key_list.append(new_key_entry)

  new_contents = '\n'.join(key_list) + '\n'
  with files.OpenForWritingPrivate(known_hosts_file) as f:
    f.write(new_contents)


def _SdkHelperBin():
  """Returns the SDK helper executable bin directory."""
  return os.path.join(config.Paths().sdk_root, 'bin', 'sdk')


def _MetadataHasBlockProjectSshKeys(metadata):
  """Return true if the metadata has 'block-project-ssh-keys' set and 'true'."""
  if not (metadata and metadata.items):
    return False
  matching_values = [item.value for item in metadata.items
                     if item.key == constants.SSH_KEYS_BLOCK_METADATA_KEY]
  if not matching_values:
    return False
  return matching_values[0].lower() == 'true'


class BaseSSHCommand(base_classes.BaseCommand,
                     user_utils.UserResourceFetcher):
  """Base class for subcommands that need to connect to instances using SSH.

  Subclasses can call EnsureSSHKeyIsInProject() to make sure that the
  user's public SSH key is placed in the project metadata before
  proceeding.
  """

  @staticmethod
  def Args(parser):
    ssh_key_file = parser.add_argument(
        '--ssh-key-file',
        help='The path to the SSH key file.')
    ssh_key_file.detailed_help = """\
        The path to the SSH key file. By default, this is ``{0}''.
        """.format(constants.DEFAULT_SSH_KEY_FILE)

  def GetProject(self):
    """Returns the project object."""
    errors = []
    objects = list(request_helper.MakeRequests(
        requests=[(self.compute.projects,
                   'Get',
                   self.messages.ComputeProjectsGetRequest(
                       project=properties.VALUES.core.project.Get(
                           required=True),
                   ))],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None))
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not fetch project resource:')
    return objects[0]

  def SetProjectMetadata(self, new_metadata):
    """Sets the project metadata to the new metadata."""
    compute = self.compute

    errors = []
    list(request_helper.MakeRequests(
        requests=[
            (compute.projects,
             'SetCommonInstanceMetadata',
             self.messages.ComputeProjectsSetCommonInstanceMetadataRequest(
                 metadata=new_metadata,
                 project=properties.VALUES.core.project.Get(
                     required=True),
             ))],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None))
    if errors:
      utils.RaiseException(
          errors,
          SetProjectMetadataError,
          error_message='Could not add SSH key to project metadata:')

  def SetInstanceMetadata(self, instance, new_metadata):
    """Sets the project metadata to the new metadata."""
    compute = self.compute

    errors = []
    # API wants just the zone name, not the full URL
    zone = instance.zone.split('/')[-1]
    list(request_helper.MakeRequests(
        requests=[
            (compute.instances,
             'SetMetadata',
             self.messages.ComputeInstancesSetMetadataRequest(
                 instance=instance.name,
                 metadata=new_metadata,
                 project=properties.VALUES.core.project.Get(
                     required=True),
                 zone=zone
             ))],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None))
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not add SSH key to instance metadata:')

  def EnsureSSHKeyIsInInstance(self, user, instance, iam_keys=False):
    """Ensures that the user's public SSH key is in the instance metadata.

    Args:
      user: str, the name of the user associated with the SSH key in the
          metadata
      instance: Instance, ensure the SSH key is in the metadata of this instance
      iam_keys: bool. If False, write to the original SSH metadata key (that
          overrides the project-global SSH metadata key). If true, write to the
          new SSH metadata key (that works in union with the project-global SSH
          key metadata).

    Returns:
      bool, True if the key was newly added, False if it was in the metadata
          already
    """
    # First, grab the public key from the user's computer. If the public key
    # doesn't already exist, GetPublicKey() should create it.
    public_key = self.GetPublicKey()

    new_metadata = _AddSSHKeyToMetadataMessage(self.messages, user, public_key,
                                               instance.metadata,
                                               iam_keys=iam_keys)
    if new_metadata != instance.metadata:
      self.SetInstanceMetadata(instance, new_metadata)
      return True
    else:
      return False

  def EnsureSSHKeyIsInProject(self, user):
    """Ensures that the user's public SSH key is in the project metadata.

    Args:
      user: str, the name of the user associated with the SSH key in the
          metadata

    Returns:
      bool, True if the key was newly added, False if it was in the metadata
          already
    """
    # First, grab the public key from the user's computer. If the public key
    # doesn't already exist, GetPublicKey() should create it.
    public_key = self.GetPublicKey()

    # Second, let's make sure the public key is in the project metadata.
    project = self.GetProject()
    existing_metadata = project.commonInstanceMetadata
    new_metadata = _AddSSHKeyToMetadataMessage(
        self.messages, user, public_key, existing_metadata)
    if new_metadata != existing_metadata:
      self.SetProjectMetadata(new_metadata)
      return True
    else:
      return False

  def EnsureSSHKeyExistsForUser(self, user):
    """Ensure the user's public SSH key is known by the Account Service."""
    public_key = self.GetPublicKey()
    should_upload = True
    try:
      user_info = self.LookupUser(user)
    except user_utils.UserException:
      owner_email = gaia_utils.GetAuthenticatedGaiaEmail(self.http)
      self.CreateUser(user, owner_email)
      user_info = self.LookupUser(user)
    for remote_public_key in user_info.publicKeys:
      if remote_public_key.key.rstrip() == public_key:
        expiration_time = remote_public_key.expirationTimestamp

        if expiration_time and time_utils.IsExpired(expiration_time):
          # If a key is expired we remove and reupload
          self.RemovePublicKey(
              user_info.name, remote_public_key.fingerprint)
        else:
          should_upload = False
        break

    if should_upload:
      self.UploadPublicKey(user, public_key)
    return True

  def GetPublicKey(self):
    """Generates an SSH key using ssh-keygen (if necessary) and returns it."""
    public_ssh_key_file = self.ssh_key_file + '.pub'
    if not _KeyFilesAreValid(private=self.ssh_key_file,
                             public=public_ssh_key_file):
      log.warn('You do not have an SSH key for Google Compute Engine.')
      log.warn('[%s] will be executed to generate a key.',
               self.ssh_keygen_executable)

      ssh_directory = os.path.dirname(public_ssh_key_file)
      if not os.path.exists(ssh_directory):
        if console_io.PromptContinue(
            'This tool needs to create the directory [{0}] before being able '
            'to generate SSH keys.'.format(ssh_directory)):
          files.MakeDir(ssh_directory, 0700)
        else:
          raise exceptions.ToolException('SSH key generation aborted by user.')

      # Remove the private key file to avoid interactive prompts.
      try:
        os.remove(self.ssh_key_file)
      except OSError:
        pass

      keygen_args = [self.ssh_keygen_executable]
      if IsRunningOnWindows():
        # No passphrase in the current implementation.
        keygen_args.append(self.ssh_key_file)
      else:
        if properties.VALUES.core.disable_prompts.GetBool():
          # Specify empty passphrase on command line
          keygen_args.extend(['-P', ''])
        keygen_args.extend([
            '-t', 'rsa',
            '-f', self.ssh_key_file,
        ])
      _RunExecutable(keygen_args)

    with open(public_ssh_key_file) as f:
      # We get back a unicode list of keys for the remaining metadata, so
      # convert to unicode. Assume UTF 8, but if we miss a character we can just
      # replace it with a '?'. The only source of issues would be the hostnames,
      # which are relatively inconsequential.
      return f.readline().strip().decode('utf8', 'replace')

  @property
  def resource_type(self):
    return 'instances'

  def Run(self, args):
    """Subclasses must call this in their Run() before continuing."""
    if IsRunningOnWindows():
      scp_command = 'pscp'
      ssh_command = 'plink'
      ssh_keygen_command = 'winkeygen'
      ssh_term_command = 'putty'
      # The ssh helper executables are installed in this dir only.
      path = _SdkHelperBin()
      self.ssh_term_executable = files.FindExecutableOnPath(
          ssh_term_command, path=path)
    else:
      scp_command = 'scp'
      ssh_command = 'ssh'
      ssh_keygen_command = 'ssh-keygen'
      ssh_term_command = None
      path = None
      self.ssh_term_executable = None
    self.scp_executable = files.FindExecutableOnPath(scp_command, path=path)
    self.ssh_executable = files.FindExecutableOnPath(ssh_command, path=path)
    self.ssh_keygen_executable = files.FindExecutableOnPath(
        ssh_keygen_command, path=path)
    if (not self.scp_executable or
        not self.ssh_executable or
        not self.ssh_keygen_executable or
        ssh_term_command and not self.ssh_term_executable):
      raise exceptions.ToolException('Your platform does not support OpenSSH.')

    self.ssh_key_file = os.path.realpath(os.path.expanduser(
        args.ssh_key_file or constants.DEFAULT_SSH_KEY_FILE))
    self.known_hosts_file = os.path.realpath(os.path.expanduser(
        constants.GOOGLE_SSH_KNOWN_HOSTS_FILE))


class BaseSSHCLICommand(BaseSSHCommand):
  """Base class for subcommands that use ssh or scp."""

  @staticmethod
  def Args(parser):
    BaseSSHCommand.Args(parser)

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help=('If provided, prints the command that would be run to standard '
              'out instead of executing it.'))

    plain = parser.add_argument(
        '--plain',
        action='store_true',
        help='Suppresses the automatic addition of ssh/scp flags.')
    plain.detailed_help = """\
        Suppresses the automatic addition of *ssh(1)*/*scp(1)* flags. This flag
        is useful if you want to take care of authentication yourself or
        use specific ssh/scp features.
        """

    strict_host_key = parser.add_argument(
        '--strict-host-key-checking',
        choices=['yes', 'no', 'ask'],
        help='Override the default behavior for ssh/scp StrictHostKeyChecking')
    strict_host_key.detailed_help = """\
        Override the default behavior of StrictHostKeyChecking. By default,
        StrictHostKeyChecking is set to 'no' the first time you connect to an
        instance and will be set to 'yes' for all subsequent connections. Use
        this flag to specify a value for the connection.
        """

  def GetDefaultFlags(self):
    """Returns a list of default commandline flags."""
    return [
        '-i', self.ssh_key_file,
        '-o', 'UserKnownHostsFile={0}'.format(self.known_hosts_file),
        '-o', 'IdentitiesOnly=yes',  # ensure our SSH key trumps any ssh_agent
        '-o', 'CheckHostIP=no'
    ]

  def GetInstance(self, instance_ref):
    """Fetch an instance based on the given instance_ref."""
    request = (self.compute.instances,
               'Get',
               self.messages.ComputeInstancesGetRequest(
                   instance=instance_ref.Name(),
                   project=self.project,
                   zone=instance_ref.zone))

    errors = []
    objects = list(request_helper.MakeRequests(
        requests=[request],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None))
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not fetch instance:')
    return objects[0]

  def WaitUntilSSHable(self, user, args, instance):
    """Blocks until SSHing to the given host succeeds."""
    external_ip_address = GetExternalIPAddress(instance)
    ssh_args_for_polling = [self.ssh_executable]
    ssh_args_for_polling.extend(self.GetDefaultFlags())
    ssh_args_for_polling.extend(self.GetHostKeyArgs(args, instance))

    ssh_args_for_polling.append(UserHost(user, external_ip_address))
    ssh_args_for_polling.append('true')
    ssh_args_for_polling = self.LocalizeCommand(ssh_args_for_polling)

    start_sec = time_utils.CurrentTimeSec()
    while True:
      logging.debug('polling instance for SSHability')
      retval = subprocess.call(ssh_args_for_polling)
      if retval == 0:
        break
      if (time_utils.CurrentTimeSec() - start_sec >
          _SSH_KEY_PROPAGATION_TIMEOUT_SEC):
        raise exceptions.ToolException(
            'Could not SSH to the instance.  It is possible that '
            'your SSH key has not propagated to the instance yet. '
            'Try running this command again.  If you still cannot connect, '
            'verify that the firewall and instance are set to accept '
            'ssh traffic.')
      time_utils.Sleep(5)

  def LocalizeCommand(self, cmd_args):
    """Modifies an ssh/scp command line to match the local implementation.

    Args:
      cmd_args: [str], The command line that will be executed.

    Returns:
      Returns new_cmd_args, the localized command line.
    """
    if not IsRunningOnWindows():
      return cmd_args
    args = [cmd_args[0]]
    i = 1
    n = len(cmd_args)
    positionals = 0
    while i < n:
      arg = cmd_args[i]
      i += 1
      if arg == '-i' and i < n:
        # -i private_key_file -- use private_key_file.ppk -- if it doesn't exist
        # then winkeygen will be called to generate it before attempting to
        # connect.
        args.append(arg)
        arg = cmd_args[i]
        i += 1
        arg += '.ppk'
      elif arg == '-o' and i < n:
        arg = cmd_args[i]
        i += 1
        if arg.startswith('CheckHostIP'):
          # Ignore -o CheckHostIP=yes/no.
          continue
        elif arg.startswith('IdentitiesOnly'):
          # Ignore -o IdentitiesOnly=yes/no.
          continue
        elif arg.startswith('StrictHostKeyChecking'):
          # Ignore -o StrictHostKeyChecking=yes/no.
          continue
        elif arg.startswith('UserKnownHostsFile'):
          # Ignore UserKnownHostsFile=path.
          continue
      elif arg == '-p':
        # -p port => -P port.
        arg = '-P'
      elif not arg.startswith('-'):
        positionals += 1
      args.append(arg)
    # Check if a putty term should be opened here.
    if positionals == 1 and cmd_args[0] == self.ssh_executable:
      args[0] = self.ssh_term_executable
    return args

  def IsHostKeyAliasInKnownHosts(self, host_key_alias):
    known_hosts = ReadFile(self.known_hosts_file)
    if known_hosts:
      return host_key_alias in known_hosts
    else:
      return False

  def GetHostKeyArgs(self, args, instance):
    """Returns default values for HostKeyAlias and StrictHostKeyChecking.

    Args:
      args: argparse.Namespace, The calling command invocation args.
      instance: Instance resource that ssh/scp is connecting to.

    Returns:
      list, list of arguments to add to the ssh command line.
    """
    if args.plain or IsRunningOnWindows():
      return []
    host_key_alias = 'compute.{0}'.format(instance.id)

    if args.strict_host_key_checking:
      strict_host_key_value = args.strict_host_key_checking
    elif self.IsHostKeyAliasInKnownHosts(host_key_alias):
      strict_host_key_value = 'yes'
    else:
      strict_host_key_value = 'no'

    cmd_args = ['-o', 'HostKeyAlias={0}'.format(host_key_alias), '-o',
                'StrictHostKeyChecking={0}'.format(strict_host_key_value)]
    return cmd_args

  def ActuallyRun(self, args, cmd_args, user, instance,
                  strict_error_checking=True, use_account_service=False,
                  wait_for_sshable=True):
    """Runs the scp/ssh command specified in cmd_args.

    If the scp/ssh command exits non-zero, this command will exit with the same
    exit code.

    Args:
      args: argparse.Namespace, The calling command invocation args.
      cmd_args: [str], The argv for the command to execute.
      user: str, The user name.
      instance: Instance, the instance to connect to
      strict_error_checking: bool, whether to fail on a non-zero, non-255 exit
        code (alternative behavior is to return the exit code
      use_account_service: bool, when false upload ssh keys to project metadata.
      wait_for_sshable: bool, when false skip the sshability check.

    Returns:
      int, the exit code of the command that was run
    """
    cmd_args = self.LocalizeCommand(cmd_args)
    if args.dry_run:
      log.out.Print(' '.join(cmd_args))
      return

    if args.plain:
      keys_newly_added = []
    elif use_account_service:
      keys_newly_added = self.EnsureSSHKeyExistsForUser(user)
    else:
      # There are two kinds of metadata: project-wide metadata and per-instance
      # metadata. There are four SSH-key related metadata keys:
      #
      # * project['sshKeys']: shared project-wide
      # * instance['sshKeys']: legacy. Acts as an override to project['sshKeys']
      # * instance['block-project-ssh-keys']: If true, instance['ssh-keys']
      #     overrides project['sshKeys']. Otherwise, keys from both metadata
      #     pairs are valid.
      # * instance['ssh-keys']: Acts either in conjunction with or as an
      #     override to project['sshKeys'], depending on
      #     instance['block-project-ssh-keys']
      #
      # SSH-like commands work by copying a relevant SSH key to
      # the appropriate metadata value. The VM grabs keys from the metadata as
      # follows (pseudo-Python):
      #
      #   def GetAllSshKeys(project, instance):
      #       if 'sshKeys' in instance.metadata:
      #           return (instance.metadata['sshKeys'] +
      #                   instance.metadata['ssh-keys'])
      #       elif instance.metadata['block-project-ssh-keys'] == 'true':
      #           return instance.metadata['ssh-keys']
      #       else:
      #           return (instance.metadata['ssh-keys'] +
      #                   project.metadata['sshKeys'])
      #
      if _GetSSHKeysFromMetadata(instance.metadata):
        # If we add a key to project-wide metadata but the per-instance
        # 'sshKeys' metadata exists, we won't be able to ssh in because the VM
        # won't check the project-wide metadata. To avoid this, if the instance
        # has per-instance SSH key metadata, we add the key there instead.
        keys_newly_added = self.EnsureSSHKeyIsInInstance(user, instance)
      elif _MetadataHasBlockProjectSshKeys(instance.metadata):
        # If the instance 'ssh-keys' metadata overrides the project-wide
        # 'sshKeys' metadata, we should put our key there.
        keys_newly_added = self.EnsureSSHKeyIsInInstance(user, instance,
                                                         iam_keys=True)
      else:
        # Otherwise, try to add to the project-wide metadata. If we don't have
        # permissions to do that, add to the instance 'ssh-keys' metadata.
        try:
          keys_newly_added = self.EnsureSSHKeyIsInProject(user)
        except SetProjectMetadataError:
          log.info('Could not set project metadata:', exc_info=True)
          # If we can't write to the project metadata, it may be because of a
          # permissions problem (we could inspect this exception object further
          # to make sure, but because we only get a string back this would be
          # fragile). If that's the case, we want to try the writing to the
          # iam_keys metadata (we may have permissions to write to instance
          # metadata). We prefer this to the per-instance override of the
          # project metadata.
          log.info('Attempting to set instance metadata.')
          keys_newly_added = self.EnsureSSHKeyIsInInstance(user, instance,
                                                           iam_keys=True)

    if keys_newly_added and wait_for_sshable:
      self.WaitUntilSSHable(user, args, instance)

    logging.debug('%s command: %s', cmd_args[0], ' '.join(cmd_args))

    return _RunExecutable(cmd_args, strict_error_checking=strict_error_checking)


# A remote path has three parts host[@user]:[path], where @user and path are
# optional.
#   A host:
#   - cannot start with '.'
#   - cannot contain ':', '/', '\\', '@'
#   A user:
#   - cannot contain ':'.
#   A path:
#   - can be anything

_SSH_REMOTE_PATH_REGEX = r'[^.:/\\@][^:/\\@]*(@[^:]*)?:'


def IsScpLocalPath(path):
  """Checks if path is an scp local file path.

  Args:
    path: The path name to check.

  Returns:
    True if path is an scp local path, false if it is a remote path.
  """
  # Paths that start with a drive are local. _SSH_REMOTE_PATH_REGEX could match
  # path for some os implementations, so the drive test must be done before the
  # pattern match.
  if os.path.splitdrive(path)[0]:
    return True
  # Paths that match _SSH_REMOTE_PATH_REGEX are not local.
  if re.match(_SSH_REMOTE_PATH_REGEX, path):
    return False
  # Otherwise the path is local.
  return True
