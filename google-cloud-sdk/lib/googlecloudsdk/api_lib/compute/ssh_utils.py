# Copyright 2014 Google Inc. All Rights Reserved.

"""Utilities for subcommands that need to SSH into virtual machine guests."""
import logging
import os

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
  with open(os.devnull, 'w') as devnull:
    if log.IsUserOutputEnabled():
      stdout, stderr = None, None
    else:
      stdout, stderr = devnull, devnull
    try:
      subprocess.check_call(cmd_args, stdout=stdout, stderr=stderr)
    except OSError as e:
      raise SshLikeCmdFailed(cmd_args[0], message=e.strerror)
    except subprocess.CalledProcessError as e:
      if strict_error_checking or e.returncode == _SSH_ERROR_EXIT_CODE:
        raise SshLikeCmdFailed(cmd_args[0], return_code=e.returncode)
      return e.returncode
    return 0


def _GetSSHKeysFromMetadata(metadata):
  """Returns the value of the "sshKeys" metadata as a list."""
  if not metadata:
    return []
  for item in metadata.items:
    if item.key == constants.SSH_KEYS_METADATA_KEY:
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


def _AddSSHKeyToMetadataMessage(message_classes, user, public_key, metadata):
  """Adds the public key material to the metadata if it's not already there."""
  entry = '{user}:{public_key}'.format(
      user=user, public_key=public_key)

  ssh_keys = _GetSSHKeysFromMetadata(metadata)
  log.debug('Current SSH keys in project: {0}'.format(ssh_keys))

  if entry in ssh_keys:
    return metadata
  else:
    ssh_keys.append(entry)
    return metadata_utils.ConstructMetadataMessage(
        message_classes=message_classes,
        metadata={
            constants.SSH_KEYS_METADATA_KEY: _PrepareSSHKeysValue(ssh_keys)},
        existing_metadata=metadata)


def _GenerateKeyNoPassphraseOnWindows(keygen_args):
  """Generate a passphrase-less key on Windows.

  Windows ssh-keygen does not support arguments for the '-P' flag, so we
  communicate with it to have no passphrase.

  Args:
    keygen_args: list of str, the arguments (including path to ssh-keygen
      executable) for the ssh-keygen command.

  Raises:
    SshLikeCmdFailed: if the ssh-keygen process fails.
  """
  err_msg = ('SSH Key Generation failed. Please run this command again in '
             'interactive mode.')

  keygen_process = subprocess.Popen(keygen_args, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE)
  keygen_output = ''
  for prompt_keywords in [('enter', 'passphrase'),
                          ('enter', 'passphrase', 'again')]:
    chunk = ''
    while not chunk.endswith(': '):
      char = keygen_process.stdout.read(1)
      chunk += char
      if not char:  # Process terminated
        break
    keygen_output += chunk
    if not all([keyword in chunk.lower() for keyword in prompt_keywords]):
      # If we don't get the output we're expecting, we don't know how to
      # generate keys.
      log.error(err_msg)
      raise SshLikeCmdFailed(keygen_args[0], message=keygen_output)
    keygen_process.stdin.write('\n')  # empty passphrase
  chunk, _ = keygen_process.communicate()  # stderr is not piped
  keygen_output += chunk
  if keygen_process.returncode != 0:
    log.error(err_msg)
    raise SshLikeCmdFailed(keygen_args[0],
                           message=keygen_output,
                           return_code=keygen_process.returncode)


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
      utils.RaiseToolException(
          errors,
          error_message='Could not add SSH key to project metadata:')

  def EnsureSSHKeyIsInProject(self, user):
    """Ensures that the user's public SSH key is in the project metadata."""
    # First, grab the public key from the user's computer. If the
    # public key doesn't already exist, GetPublicKey() should create
    # it.
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
    """Generates an SSH key using ssh-key (if necessary) and returns it."""
    public_ssh_key_file = self.ssh_key_file + '.pub'
    if (not os.path.exists(self.ssh_key_file) or
        not os.path.exists(public_ssh_key_file)):
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

      keygen_args = [
          self.ssh_keygen_executable,
          '-t', 'rsa',
          '-f', self.ssh_key_file,
      ]
      if properties.VALUES.core.disable_prompts.GetBool():
        # If prompts are disabled, use the default of no passphrase
        current_os = platforms.OperatingSystem.Current()
        if current_os is platforms.OperatingSystem.WINDOWS:
          _GenerateKeyNoPassphraseOnWindows(keygen_args)
        else:
          # Specify empty passphrase on command line
          keygen_args.extend(['-P', ''])
          _RunExecutable(keygen_args)
      else:
        # Prompts are enabled. Run normally.
        _RunExecutable(keygen_args)

    with open(public_ssh_key_file) as f:
      return f.readline().strip()

  @property
  def resource_type(self):
    return 'instances'

  def Run(self, args):
    """Subclasses must call this in their Run() before continuing."""
    self.scp_executable = files.FindExecutableOnPath('scp')
    self.ssh_executable = files.FindExecutableOnPath('ssh')
    self.ssh_keygen_executable = files.FindExecutableOnPath('ssh-keygen')
    if (not self.scp_executable or
        not self.ssh_executable or
        not self.ssh_keygen_executable):
      raise exceptions.ToolException('Your platform does not support OpenSSH.')

    self.ssh_key_file = os.path.realpath(os.path.expanduser(
        args.ssh_key_file or constants.DEFAULT_SSH_KEY_FILE))


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
        re-enable strict host checking.
        """

  def GetDefaultFlags(self):
    """Returns a list of default commandline flags."""
    return [
        '-i', self.ssh_key_file,
        '-o', 'UserKnownHostsFile=/dev/null',
        '-o', 'IdentitiesOnly=yes',  # ensure our SSH key trumps any ssh_agent
        '-o', 'CheckHostIP=no',
        '-o', 'StrictHostKeyChecking=no',
    ]

  def GetInstanceExternalIpAddress(self, instance_ref):
    """Returns the external ip address for the given instance."""
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
    return GetExternalIPAddress(objects[0])

  def WaitUntilSSHable(self, user, external_ip_address):
    """Blocks until SSHing to the given host succeeds."""
    ssh_args_for_polling = [self.ssh_executable]
    ssh_args_for_polling.extend(self.GetDefaultFlags())
    ssh_args_for_polling.append(UserHost(user, external_ip_address))
    ssh_args_for_polling.append('true')

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

  def ActuallyRun(self, args, cmd_args, user, external_ip_address,
                  strict_error_checking=True, use_account_service=False):
    """Runs the scp/ssh command specified in cmd_args.

    If the scp/ssh command exits non-zero, this command will exit with the same
    exit code.

    Args:
      args: argparse.Namespace, The calling command invocation args.
      cmd_args: [str], The argv for the command to execute.
      user: str, The user name.
      external_ip_address: str, The external IP address.
      strict_error_checking: bool, whether to fail on a non-zero, non-255 exit
        code (alternative behavior is to return the exit code
      use_account_service: bool, when false upload ssh keys to project metadata.

    Returns:
      int, the exit code of the command that was run
    """
    if args.dry_run:
      log.out.Print(' '.join(cmd_args))
      return

    if use_account_service:
      has_keys = self.EnsureSSHKeyExistsForUser(user)
    else:
      has_keys = self.EnsureSSHKeyIsInProject(user)

    if has_keys:
      self.WaitUntilSSHable(user, external_ip_address)

    logging.debug('%s command: %s', cmd_args[0], ' '.join(cmd_args))

    return _RunExecutable(cmd_args, strict_error_checking=strict_error_checking)
