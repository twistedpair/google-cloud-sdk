# Copyright 2016 Google Inc. All Rights Reserved.
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

from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.compute import metadata_utils
from googlecloudsdk.api_lib.compute import path_simplifier
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.api_lib.compute.users import client as user_client
from googlecloudsdk.api_lib.oslogin import client as oslogin_client
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.util import gaia
from googlecloudsdk.command_lib.util import time_util
from googlecloudsdk.command_lib.util.ssh import ssh
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.console import progress_tracker

# The maximum amount of time to wait for a newly-added SSH key to
# propagate before giving up.
SSH_KEY_PROPAGATION_TIMEOUT_SEC = 60

_TROUBLESHOOTING_URL = (
    'https://cloud.google.com/compute/docs/troubleshooting#ssherrors')


class CommandError(core_exceptions.Error):
  """Wraps ssh.CommandError, primarly for adding troubleshooting info."""

  def __init__(self, original_error, message=None):
    if message is None:
      message = 'See {url} for troubleshooting hints.'.format(
          url=_TROUBLESHOOTING_URL)

    super(CommandError, self).__init__(
        '{0}\n{1}'.format(original_error, message),
        exit_code=original_error.exit_code)


class ArgumentError(core_exceptions.Error):
  """Invalid combinations of, or malformed, arguments."""
  pass


class SetProjectMetadataError(core_exceptions.Error):
  pass


class NetworkError(core_exceptions.Error):
  """Indicates that an SSH connection couldn't be established right now."""

  def __init__(self):
    super(NetworkError, self).__init__(
        'Could not SSH into the instance.  It is possible that your SSH key '
        'has not propagated to the instance yet. Try running this command '
        'again.  If you still cannot connect, verify that the firewall and '
        'instance are set to accept ssh traffic.')


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


def GetInternalIPAddress(instance_resource):
  """Returns the internal IP address of the instance.

  Args:
    instance_resource: An instance resource object.

  Raises:
    ToolException: If instance has no network interfaces.

  Returns:
    A string IP or None if no_raise is True and no ip exists.
  """
  if instance_resource.networkInterfaces:
    return instance_resource.networkInterfaces[0].networkIP
  raise exceptions.ToolException(
      'Instance [{0}] in zone [{1}] has no network interfaces.'.format(
          instance_resource.name,
          path_simplifier.Name(instance_resource.zone)))


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
      prompt_message = ('The following SSH key will be removed from your '
                        'project because your sshKeys metadata value has '
                        'reached its maximum allowed size of {0} bytes: {1}')
      prompt_message = prompt_message.format(
          constants.MAX_METADATA_VALUE_SIZE_IN_BYTES, key)
      console_io.PromptContinue(message=prompt_message, cancel_on_no=True)
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


def _MetadataHasBlockProjectSshKeys(metadata):
  """Return true if the metadata has 'block-project-ssh-keys' set and 'true'."""
  if not (metadata and metadata.items):
    return False
  matching_values = [item.value for item in metadata.items
                     if item.key == constants.SSH_KEYS_BLOCK_METADATA_KEY]
  if not matching_values:
    return False
  return matching_values[0].lower() == 'true'


def _MetadataHasOsloginEnable(metadata):
  """Return true if the metadata has 'oslogin-enable' set and 'true'.

  Args:
    metadata: Instance or Project metadata.

  Returns:
    True if Enabled, False if Disabled, None if key is not present.
  """
  if not (metadata and metadata.items):
    return None
  matching_values = [item.value for item in metadata.items
                     if item.key == constants.OSLOGIN_ENABLE_METADATA_KEY]
  if not matching_values:
    return None
  return matching_values[0].lower() == 'true'


class BaseSSHHelper(object):
  """Helper class for subcommands that need to connect to instances using SSH.

  Clients can call EnsureSSHKeyIsInProject() to make sure that the
  user's public SSH key is placed in the project metadata before
  proceeding.

  Attributes:
    keys: ssh.Keys, the public/private key pair.
    env: ssh.Environment, the current environment, used by subclasses.
  """

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Please add arguments in alphabetical order except for no- or a clear-
    pair for that argument which can follow the argument itself.
    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        '--force-key-file-overwrite',
        action='store_true',
        default=None,
        help="""\
        If enabled gcloud will regenerate and overwrite the files associated
        with a broken SSH key without asking for confirmation in both
        interactive and non-interactive environment.

        If disabled gcloud will not attempt to regenerate the files associated
        with a broken SSH key and fail in both interactive and non-interactive
        environment.""")

    # Last line empty to preserve spacing between last paragraph and calliope
    # attachment "Use --no-force-key-file-overwrite to disable."
    parser.add_argument(
        '--ssh-key-file',
        help="""\
        The path to the SSH key file. By default, this is ``{0}''.
        """.format(ssh.Keys.DEFAULT_KEY_FILE))

  def Run(self, args):
    """Sets up resources to be used by concrete subclasses.

    Subclasses must call this in their Run() before continuing.

    Args:
      args: argparse.Namespace, arguments that this command was invoked with.

    Raises:
      ssh.CommandNotFoundError: SSH is not supported.
    """

    self.keys = ssh.Keys.FromFilename(args.ssh_key_file)
    self.env = ssh.Environment.Current()
    self.env.RequireSSH()

  def GetInstance(self, client, instance_ref):
    """Fetch an instance based on the given instance_ref."""
    request = (client.apitools_client.instances,
               'Get',
               client.messages.ComputeInstancesGetRequest(
                   instance=instance_ref.Name(),
                   project=instance_ref.project,
                   zone=instance_ref.zone))

    return client.MakeRequests([request])[0]

  def GetProject(self, client, project):
    """Returns the project object.

    Args:
      client: The compute client.
      project: str, the project we are requesting or None for value from
        from properties

    Returns:
      The project object
    """
    return client.MakeRequests(
        [(client.apitools_client.projects, 'Get',
          client.messages.ComputeProjectsGetRequest(
              project=project or
              properties.VALUES.core.project.Get(required=True),))])[0]

  def _SetProjectMetadata(self, client, new_metadata):
    """Sets the project metadata to the new metadata."""
    errors = []
    client.MakeRequests(
        requests=[
            (client.apitools_client.projects,
             'SetCommonInstanceMetadata',
             client.messages.ComputeProjectsSetCommonInstanceMetadataRequest(
                 metadata=new_metadata,
                 project=properties.VALUES.core.project.Get(
                     required=True),
             ))],
        errors_to_collect=errors)
    if errors:
      utils.RaiseException(
          errors,
          SetProjectMetadataError,
          error_message='Could not add SSH key to project metadata:')

  def SetProjectMetadata(self, client, new_metadata):
    """Sets the project metadata to the new metadata with progress tracker."""
    with progress_tracker.ProgressTracker('Updating project ssh metadata'):
      self._SetProjectMetadata(client, new_metadata)

  def _SetInstanceMetadata(self, client, instance, new_metadata):
    """Sets the project metadata to the new metadata."""
    errors = []
    # API wants just the zone name, not the full URL
    zone = instance.zone.split('/')[-1]
    client.MakeRequests(
        requests=[
            (client.apitools_client.instances,
             'SetMetadata',
             client.messages.ComputeInstancesSetMetadataRequest(
                 instance=instance.name,
                 metadata=new_metadata,
                 project=properties.VALUES.core.project.Get(
                     required=True),
                 zone=zone
             ))],
        errors_to_collect=errors)
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not add SSH key to instance metadata:')

  def SetInstanceMetadata(self, client, instance, new_metadata):
    """Sets the instance metadata to the new metadata with progress tracker."""
    with progress_tracker.ProgressTracker('Updating instance ssh metadata'):
      self._SetInstanceMetadata(client, instance, new_metadata)

  def EnsureSSHKeyIsInInstance(self, client, user, instance, iam_keys=False):
    """Ensures that the user's public SSH key is in the instance metadata.

    Args:
      client: The compute client.
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
    public_key = self.keys.GetPublicKey().ToEntry(include_comment=True)
    new_metadata = _AddSSHKeyToMetadataMessage(
        client.messages, user, public_key, instance.metadata, iam_keys=iam_keys)
    has_new_metadata = new_metadata != instance.metadata
    if has_new_metadata:
      self.SetInstanceMetadata(client, instance, new_metadata)
    return has_new_metadata

  def EnsureSSHKeyIsInProject(self, client, user, project=None):
    """Ensures that the user's public SSH key is in the project metadata.

    Args:
      client: The compute client.
      user: str, the name of the user associated with the SSH key in the
          metadata
      project: Project, the project SSH key will be added to

    Returns:
      bool, True if the key was newly added, False if it was in the metadata
          already
    """
    public_key = self.keys.GetPublicKey().ToEntry(include_comment=True)
    if not project:
      project = self.GetProject(client, None)
    existing_metadata = project.commonInstanceMetadata
    new_metadata = _AddSSHKeyToMetadataMessage(
        client.messages, user, public_key, existing_metadata)
    if new_metadata != existing_metadata:
      self.SetProjectMetadata(client, new_metadata)
      return True
    else:
      return False

  def _EnsureSSHKeyExistsForUser(self, http, fetcher, user):
    """Ensure the user's public SSH key is known by the Account Service."""
    public_key = self.keys.GetPublicKey().ToEntry(include_comment=True)
    should_upload = True
    try:
      user_info = fetcher.LookupUser(user)
    except user_client.UserException:
      owner_email = gaia.GetAuthenticatedGaiaEmail(http)
      fetcher.CreateUser(user, owner_email)
      user_info = fetcher.LookupUser(user)
    for remote_public_key in user_info.publicKeys:
      if remote_public_key.key.rstrip() == public_key:
        expiration_time = remote_public_key.expirationTimestamp

        if expiration_time and time_util.IsExpired(expiration_time):
          # If a key is expired we remove and reupload
          fetcher.RemovePublicKey(
              user_info.name, remote_public_key.fingerprint)
        else:
          should_upload = False
        break

    if should_upload:
      fetcher.UploadPublicKey(user, public_key)
    return True

  def EnsureSSHKeyExists(self, compute_client, cua_client, user, instance,
                         project, use_account_service=False):
    """Controller for EnsureSSHKey* variants.

    Sends the key to the project metadata, instance metadata or account service,
    and signals whether the key was newly added.

    Args:
      compute_client: The compute client.
      cua_client: The clouduseraccounts client.
      user: str, The user name.
      instance: Instance, the instance to connect to.
      project: Project, the project instance is in
      use_account_service: bool, when false upload ssh keys to project metadata.

    Returns:
      bool, True if the key was newly added.
    """
    if use_account_service:
      log.status.Print('using accounts service')
      fetcher = user_client.UserResourceFetcher(
          cua_client,
          properties.VALUES.core.project.GetOrFail(),
          compute_client.apitools_client.http, compute_client.batch_url)
      try:
        keys_newly_added = self._EnsureSSHKeyExistsForUser(
            compute_client.apitools_client.http, fetcher, user)
      # TODO(b/37739425): find out what desired fallback mechanism is and
      # implement it.
      except  user_client.UserException as e:
        log.info(
            'Error when attempting to prepare keys using clouduaseraccounts '
            'API, falling back to metadata keys: %s', e)
        use_account_service = False
    if not use_account_service:
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
        keys_newly_added = self.EnsureSSHKeyIsInInstance(
            compute_client, user, instance)
      elif _MetadataHasBlockProjectSshKeys(instance.metadata):
        # If the instance 'ssh-keys' metadata overrides the project-wide
        # 'sshKeys' metadata, we should put our key there.
        keys_newly_added = self.EnsureSSHKeyIsInInstance(
            compute_client, user, instance, iam_keys=True)
      else:
        # Otherwise, try to add to the project-wide metadata. If we don't have
        # permissions to do that, add to the instance 'ssh-keys' metadata.
        try:
          keys_newly_added = self.EnsureSSHKeyIsInProject(
              compute_client, user, project)
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
          keys_newly_added = self.EnsureSSHKeyIsInInstance(
              compute_client, user, instance, iam_keys=True)
    return keys_newly_added

  def CheckForOsloginAndGetUser(self, instance,
                                project, requested_user, release_track, http):
    """Checks instance/project metadata for oslogin and update username."""
    # Instance metadata has priority
    use_oslogin = False
    oslogin_enabled = _MetadataHasOsloginEnable(instance.metadata)
    if oslogin_enabled is None:
      project_metadata = project.commonInstanceMetadata
      oslogin_enabled = _MetadataHasOsloginEnable(project_metadata)

    if not oslogin_enabled:
      return requested_user, use_oslogin

    # Connect to the oslogin API and add public key to oslogin user account.
    oslogin = oslogin_client.OsloginClient(release_track)
    if not oslogin:
      log.warn('OS Login is enabled on Instance/Project, but is not availabe '
               'in the {0} version of gcloud.'.format(release_track.id))
      return requested_user, use_oslogin
    public_key = self.keys.GetPublicKey().ToEntry(include_comment=True)
    user_email = gaia.GetAuthenticatedGaiaEmail(http)
    login_profile = oslogin.ImportSshPublicKey(user_email, public_key)
    use_oslogin = True

    # Get the username for the oslogin user. If the username is the same as the
    # default user, return that one. Otherwise, return the 'primary' username.
    # If no 'primary' exists, return the first username.
    oslogin_user = None
    for pa in login_profile.loginProfile.posixAccounts:
      oslogin_user = oslogin_user or pa.username
      if pa.username == requested_user:
        return requested_user, use_oslogin
      elif pa.primary:
        oslogin_user = pa.username

    log.warn('Using OS Login user [{0}] instead of default user [{1}]'
             .format(oslogin_user, requested_user))
    return oslogin_user, use_oslogin

  def GetConfig(self, host_key_alias, strict_host_key_checking=None):
    """Returns a dict of default `ssh-config(5)` options on the OpenSSH format.

    Args:
      host_key_alias: str, Alias of the host key in the known_hosts file.
      strict_host_key_checking: str or None, whether to enforce strict host key
        checking. If None, it will be determined by existence of host_key_alias
        in the known hosts file. Accepted strings are 'yes', 'ask' and 'no'.

    Returns:
      Dict with OpenSSH options.
    """
    config = {}
    known_hosts = ssh.KnownHosts.FromDefaultFile()
    config['UserKnownHostsFile'] = known_hosts.file_path
    # Ensure our SSH key trumps any ssh_agent
    config['IdentitiesOnly'] = 'yes'
    config['CheckHostIP'] = 'no'

    if not strict_host_key_checking:
      if known_hosts.ContainsAlias(host_key_alias):
        strict_host_key_checking = 'yes'
      else:
        strict_host_key_checking = 'no'
    config['StrictHostKeyChecking'] = strict_host_key_checking
    config['HostKeyAlias'] = host_key_alias
    return config


class BaseSSHCLIHelper(BaseSSHHelper):
  """Helper class for subcommands that use ssh or scp."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Please add arguments in alphabetical order except for no- or a clear-
    pair for that argument which can follow the argument itself.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    super(BaseSSHCLIHelper, BaseSSHCLIHelper).Args(parser)

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help=('If provided, prints the command that would be run to standard '
              'out instead of executing it.'))

    parser.add_argument(
        '--plain',
        action='store_true',
        help="""\
        Suppresses the automatic addition of *ssh(1)*/*scp(1)* flags. This flag
        is useful if you want to take care of authentication yourself or
        use specific ssh/scp features.
        """)

    parser.add_argument(
        '--strict-host-key-checking',
        choices=['yes', 'no', 'ask'],
        help="""\
        Override the default behavior of StrictHostKeyChecking. By default,
        StrictHostKeyChecking is set to 'no' the first time you connect to an
        instance and will be set to 'yes' for all subsequent connections. Use
        this flag to specify a value for the connection.
        """)

  def Run(self, args):
    super(BaseSSHCLIHelper, self).Run(args)
    if not args.plain:
      self.keys.EnsureKeysExist(args.force_key_file_overwrite,
                                allow_passphrase=True)

  def PreliminarylyVerifyInstance(self, instance_id, remote, identity_file,
                                  options):
    """Verify the instance's identity by connecting and running a command.

    Args:
      instance_id: str, id of the compute instance.
      remote: ssh.Remote, remote to connect to.
      identity_file: str, optional key file.
      options: dict, optional ssh options.

    Raises:
      ssh.CommandError: The ssh command failed.
      core_exceptions.NetworkIssueError: The instance id does not match.
    """
    metadata_id_url = (
        'http://metadata.google.internal/computeMetadata/v1/instance/id')
    # Exit codes 255 and 1 are taken by OpenSSH and PuTTY.
    # 23 chosen by fair dice roll.
    remote_command = [
        '[ `curl "{}" -H "Metadata-Flavor: Google" -q` = {} ] || exit 23'
        .format(metadata_id_url, instance_id)]
    cmd = ssh.SSHCommand(remote, identity_file=identity_file,
                         options=options, remote_command=remote_command)
    return_code = cmd.Run(self.env, force_connect=True)
    if return_code == 0:
      return
    elif return_code == 23:
      raise core_exceptions.NetworkIssueError(
          'Established connection with host {} but was unable to '
          'confirm ID of the instance.'.format(remote.host))
    raise ssh.CommandError(cmd, return_code=return_code)


def HostKeyAlias(instance):
  return 'compute.{0}'.format(instance.id)


def GetUserAndInstance(user_host, use_account_service, http):
  """Returns pair consiting of user name and instance name."""
  parts = user_host.split('@')
  if len(parts) == 1:
    if use_account_service:  # Using Account Service.
      user = gaia.GetDefaultAccountName(http)
    else:  # Uploading keys through metadata.
      user = ssh.GetDefaultSshUsername(warn_on_account_user=True)
    instance = parts[0]
    return user, instance
  if len(parts) == 2:
    return parts
  raise exceptions.ToolException(
      'Expected argument of the form [USER@]INSTANCE; received [{0}].'
      .format(user_host))
