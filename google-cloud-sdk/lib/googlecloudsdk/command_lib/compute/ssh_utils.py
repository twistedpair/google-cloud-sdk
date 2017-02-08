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
import logging

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.compute import metadata_utils
from googlecloudsdk.api_lib.compute import path_simplifier
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.api_lib.compute.users import client as user_client
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.util import gaia
from googlecloudsdk.command_lib.util import ssh
from googlecloudsdk.command_lib.util import time_util
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import progress_tracker

# The maximum amount of time to wait for a newly-added SSH key to
# propagate before giving up.
_SSH_KEY_PROPAGATION_TIMEOUT_SEC = 60

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


class SetProjectMetadataError(core_exceptions.Error):
  pass


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


def _MetadataHasBlockProjectSshKeys(metadata):
  """Return true if the metadata has 'block-project-ssh-keys' set and 'true'."""
  if not (metadata and metadata.items):
    return False
  matching_values = [item.value for item in metadata.items
                     if item.key == constants.SSH_KEYS_BLOCK_METADATA_KEY]
  if not matching_values:
    return False
  return matching_values[0].lower() == 'true'


class BaseSSHCommand(base_classes.BaseCommand):
  """Base class for subcommands that need to connect to instances using SSH.

  Subclasses can call EnsureSSHKeyIsInProject() to make sure that the
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
    force_key_file_overwrite = parser.add_argument(
        '--force-key-file-overwrite',
        action='store_true',
        default=None,
        help=('Force overwrite the files associated with a broken SSH key.')
    )
    force_key_file_overwrite.detailed_help = """\
        If enabled gcloud will regenerate and overwrite the files associated
        with a broken SSH key without asking for confirmation in both
        interactive and non-interactive environment.

        If disabled gcloud will not attempt to regenerate the files associated
        with a broken SSH key and fail in both interactive and non-interactive
        environment.

    """
    # Last line empty to preserve spacing between last paragraph and calliope
    # attachment "Use --no-force-key-file-overwrite to disable."
    ssh_key_file = parser.add_argument(
        '--ssh-key-file',
        help='The path to the SSH key file.')
    ssh_key_file.detailed_help = """\
        The path to the SSH key file. By default, this is ``{0}''.
        """.format(ssh.Keys.DEFAULT_KEY_FILE)

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

  def GetProject(self, project):
    """Returns the project object.

    Args:
      project: str, the project we are requesting or None for value from
        from properties

    Returns:
      The project object
    """
    errors = []
    objects = list(request_helper.MakeRequests(
        requests=[(self.compute.projects,
                   'Get',
                   self.messages.ComputeProjectsGetRequest(
                       project=project or properties.VALUES.core.project.Get(
                           required=True),
                   ))],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors))
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not fetch project resource:')
    return objects[0]

  def _SetProjectMetadata(self, new_metadata):
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
        errors=errors))
    if errors:
      utils.RaiseException(
          errors,
          SetProjectMetadataError,
          error_message='Could not add SSH key to project metadata:')

  def SetProjectMetadata(self, new_metadata):
    """Sets the project metadata to the new metadata with progress tracker."""
    with progress_tracker.ProgressTracker('Updating project ssh metadata'):
      self._SetProjectMetadata(new_metadata)

  def _SetInstanceMetadata(self, instance, new_metadata):
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
        errors=errors))
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not add SSH key to instance metadata:')

  def SetInstanceMetadata(self, instance, new_metadata):
    """Sets the instance metadata to the new metadata with progress tracker."""
    with progress_tracker.ProgressTracker('Updating instance ssh metadata'):
      self._SetInstanceMetadata(instance, new_metadata)

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
    public_key = self.keys.GetPublicKey().ToEntry(include_comment=True)
    new_metadata = _AddSSHKeyToMetadataMessage(self.messages, user, public_key,
                                               instance.metadata,
                                               iam_keys=iam_keys)
    if new_metadata != instance.metadata:
      self.SetInstanceMetadata(instance, new_metadata)
      return True
    else:
      return False

  def EnsureSSHKeyIsInProject(self, user, project_name=None):
    """Ensures that the user's public SSH key is in the project metadata.

    Args:
      user: str, the name of the user associated with the SSH key in the
          metadata
      project_name: str, the project SSH key will be added to

    Returns:
      bool, True if the key was newly added, False if it was in the metadata
          already
    """
    public_key = self.keys.GetPublicKey().ToEntry(include_comment=True)
    project = self.GetProject(project_name)
    existing_metadata = project.commonInstanceMetadata
    new_metadata = _AddSSHKeyToMetadataMessage(
        self.messages, user, public_key, existing_metadata)
    if new_metadata != existing_metadata:
      self.SetProjectMetadata(new_metadata)
      return True
    else:
      return False

  def _EnsureSSHKeyExistsForUser(self, fetcher, user):
    """Ensure the user's public SSH key is known by the Account Service."""
    public_key = self.keys.GetPublicKey().ToEntry(include_comment=True)
    should_upload = True
    try:
      user_info = fetcher.LookupUser(user)
    except user_client.UserException:
      owner_email = gaia.GetAuthenticatedGaiaEmail(self.http)
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

  @property
  def resource_type(self):
    return 'instances'


class BaseSSHCLICommand(BaseSSHCommand):
  """Base class for subcommands that use ssh or scp."""

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

  def Run(self, args):
    super(BaseSSHCLICommand, self).Run(args)
    if not args.plain:
      self.keys.EnsureKeysExist(args.force_key_file_overwrite)

  def GetInstance(self, instance_ref):
    """Fetch an instance based on the given instance_ref."""
    request = (self.compute.instances,
               'Get',
               self.messages.ComputeInstancesGetRequest(
                   instance=instance_ref.Name(),
                   project=instance_ref.project,
                   zone=instance_ref.zone))

    errors = []
    objects = list(request_helper.MakeRequests(
        requests=[request],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors))
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not fetch instance:')
    return objects[0]

  def HostKeyAlias(self, instance):
    return 'compute.{0}'.format(instance.id)

  def ActuallyRun(self, args, cmd_args, user, instance, project,
                  strict_error_checking=True, use_account_service=False,
                  wait_for_sshable=True, ignore_ssh_errors=False):
    """Runs the scp/ssh command specified in cmd_args.

    If the scp/ssh command exits non-zero, this command will exit with the same
    exit code.

    Args:
      args: argparse.Namespace, The calling command invocation args.
      cmd_args: [str], The argv for the command to execute.
      user: str, The user name.
      instance: Instance, the instance to connect to
      project: str, the project instance is in
      strict_error_checking: bool, whether to fail on a non-zero, non-255 exit
        code (alternative behavior is to return the exit code
      use_account_service: bool, when false upload ssh keys to project metadata.
      wait_for_sshable: bool, when false skip the sshability check.
      ignore_ssh_errors: bool, when true ignore all errors, including the 255
        exit code.

    Raises:
      CommandError: If the scp/ssh command fails.

    Returns:
      int, the exit code of the command that was run
    """
    cmd_args = ssh.LocalizeCommand(cmd_args, self.env)
    if args.dry_run:
      log.out.Print(' '.join(cmd_args))
      return

    if args.plain:
      keys_newly_added = []
    elif use_account_service:
      fetcher = user_client.UserResourceFetcher(
          self.clouduseraccounts, self.project, self.http, self.batch_url)
      keys_newly_added = self._EnsureSSHKeyExistsForUser(fetcher, user)
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
          keys_newly_added = self.EnsureSSHKeyIsInProject(user, project)
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
      external_ip_address = GetExternalIPAddress(instance)
      host_key_alias = self.HostKeyAlias(instance)
      ssh.WaitUntilSSHable(
          user, external_ip_address, self.env, self.keys.key_file,
          host_key_alias, args.plain, args.strict_host_key_checking,
          _SSH_KEY_PROPAGATION_TIMEOUT_SEC)

    logging.debug('%s command: %s', cmd_args[0], ' '.join(cmd_args))

    try:
      return ssh.RunExecutable(cmd_args,
                               strict_error_checking=strict_error_checking,
                               ignore_ssh_errors=ignore_ssh_errors)
    except ssh.CommandError as e:
      raise CommandError(e)
