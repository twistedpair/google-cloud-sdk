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

"""SSH client utilities for key-generation, dispatching the ssh commands etc."""
import errno
import getpass
import logging
import os
import re
import subprocess
import enum

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.util import gaia
from googlecloudsdk.command_lib.util import time_util
from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms


# `ssh` exits with this exit code in the event of an SSH error (as opposed to a
# successful `ssh` execution where the *command* errored).
_SSH_ERROR_EXIT_CODE = 255

# Normally, all SSH output is simply returned to the user (or sent to
# /dev/null if user output is disabled). For testing, this value can be
# overridden with a file path.
SSH_OUTPUT_FILE = None

DEFAULT_SSH_KEY_FILE = os.path.join('~', '.ssh', 'google_compute_engine')

PER_USER_SSH_CONFIG_FILE = os.path.join('~', '.ssh', 'config')

# The default timeout for waiting for a host to become reachable.
# Useful for giving some time after VM booting, key propagation etc.
_DEFAULT_TIMEOUT = 60


class CommandError(core_exceptions.Error):
  """Raise for a failure when invoking ssh, scp, or similar."""

  def __init__(self, cmd, message=None, return_code=None):
    if not (message or return_code):
      raise ValueError('One of message or return_code is required.')

    self.cmd = cmd

    message_text = '[{0}]'.format(message) if message else None
    return_code_text = ('return code [{0}]'.format(return_code)
                        if return_code else None)
    why_failed = ' and '.join(filter(None, [message_text, return_code_text]))

    super(CommandError, self).__init__(
        '[{0}] exited with {1}.'.format(self.cmd, why_failed),
        exit_code=return_code)


def _IsValidSshUsername(user):
  # All characters must be ASCII, and no spaces are allowed
  # This may grant false positives, but will prevent backwards-incompatible
  # behavior.
  return all(ord(c) < 128 and c != ' ' for c in user)


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
  if not platforms.OperatingSystem.IsWindows():
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


class KeyFileStatus(enum.Enum):
  PRESENT = 'OK'
  ABSENT = 'NOT FOUND'
  BROKEN = 'BROKEN'


class KeyFileKind(enum.Enum):
  """List of supported (by gcloud) key file kinds."""
  PRIVATE = 'private'
  PUBLIC = 'public'
  PPK = 'PuTTY PPK'


class KeyFilesVerifier(object):
  """Checks if SSH key files are correct.

   - Populates list of SSH key files (key pair, ppk key on Windows).
   - Checks if files are present and (to basic extent) correct.
   - Can remove broken key (if permitted by user).
   - Provides status information.
  """

  class KeyFileData(object):

    def __init__(self, filename):
      # We keep filename as file handle. Filesystem race is impossible to avoid
      # in this design as we spawn a subprocess and pass in filename.
      # TODO(b/33288605) fix it.
      self.filename = filename
      self.status = None

  def __init__(self, private_key_file, public_key_file):
    self.keys = {
        KeyFileKind.PRIVATE: self.KeyFileData(private_key_file),
        KeyFileKind.PUBLIC: self.KeyFileData(public_key_file)
    }
    if platforms.OperatingSystem.IsWindows():
      self.keys[KeyFileKind.PPK] = self.KeyFileData(private_key_file + '.ppk')

  def _StatusMessage(self):
    """Prepares human readable SSH key status information."""
    messages = []
    key_padding = 0
    status_padding = 0
    for kind in self.keys:
      data = self.keys[kind]
      key_padding = max(key_padding, len(kind.value))
      status_padding = max(status_padding, len(data.status.value))
    for kind in self.keys:
      data = self.keys[kind]
      messages.append('{} {} [{}]\n'.format(
          (kind.value + ' key').ljust(key_padding + 4),
          ('(' + data.status.value + ')') .ljust(status_padding + 2),
          data.filename))
    messages.sort()
    return ''.join(messages)

  def Validate(self):
    """Performs minimum key files validation.

    Returns:
      PRESENT if private and public meet minimum key file requirements.
      ABSENT if there is no sign of public nor private key file.
      BROKEN if there is some key, but it is broken or incomplete.
    """
    def ValidateFile(kind):
      status_or_line = self._WarnOrReadFirstKeyLine(self.keys[kind].filename,
                                                    kind.value)
      if isinstance(status_or_line, KeyFileStatus):
        return status_or_line
      else:  # returned line - present
        self.keys[kind].first_line = status_or_line
        return KeyFileStatus.PRESENT

    for file_kind in self.keys:
      self.keys[file_kind].status = ValidateFile(file_kind)

    # The remaining checks are for the public key file.

    # Must have at least 2 space separated fields.
    if self.keys[KeyFileKind.PUBLIC].status is KeyFileStatus.PRESENT:
      fields = self.keys[KeyFileKind.PUBLIC].first_line.split(' ')
      if len(fields) < 2 or _IsPublicKeyCorrupt95Through97(fields[1]):
        log.warn(
            'The public SSH key file for gcloud is corrupt.')
        self.keys[KeyFileKind.PUBLIC].status = KeyFileStatus.BROKEN

    # Summary
    collected_values = [x.status for x in self.keys.itervalues()]
    if all(x == KeyFileStatus.ABSENT for x in collected_values):
      return KeyFileStatus.ABSENT
    elif all(x == KeyFileStatus.PRESENT for x in collected_values):
      return KeyFileStatus.PRESENT
    else:
      return KeyFileStatus.BROKEN

  # TODO(b/33193000) Change non-interactive behavior for 2.06.2017 Release cut
  def RemoveKeyFilesIfPermittedOrFail(self, force_key_file_overwrite):
    """Removes all SSH key files if user permitted this behavior.

    User can express intent through --(no)--force-key-file-overwrite flag or
    prompt (only in interactive mode). Default behavior is to be
    non-destructive.

    Args:
      force_key_file_overwrite: bool, value of the flag specified or not by user
    """
    permissive = True  # TODO(b/33193000) Flip this bool value
    message = 'Your SSH key files are broken.\n' + self._StatusMessage()
    if force_key_file_overwrite is False:
      raise console_io.OperationCancelledError(message + 'Operation aborted.')
    message += 'We are going to overwrite all above files.'
    if force_key_file_overwrite:
      # self.force_key_file_overwrite is True
      log.warn(message)
    else:
      # self.force_key_file_overwrite is None
      # Deprecated code path is triggered only when flags are not provided.
      # Show deprecation warning only in that case.
      # Show deprecation warning before prompt to increase chance user read
      # this.
      # TODO(b/33193000) Remove this deprecation warning
      log.warn('Permissive behavior in non-interactive mode is DEPRECATED '
               'and will be removed 1st Jun 2017.\n'
               'Use --no-force-key-file-overwrite flag to opt-in for new '
               'behavior now.\n'
               'If You want to preserve old behavior, You can opt-out from '
               'new behavior using --force-key-file-overwrite flag.')
      try:
        console_io.PromptContinue(message, default=False,
                                  throw_if_unattended=permissive,
                                  cancel_on_no=True)
      except console_io.UnattendedPromptError:
        # Used to workaround default in non-interactive prompt for old behavior
        pass  # TODO(b/33193000) Remove this - exception will not be raised

    # Remove existing broken key files and prepare to regenerate them.
    # User agreed.
    for key_file in self.keys.viewvalues():
      try:
        os.remove(key_file.filename)
      except OSError as e:
        # May be due to the fact that key_file.filename points to a directory
        if e.errno == errno.EISDIR:
          raise

  def _WarnOrReadFirstKeyLine(self, path, kind):
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
        # encoded so it cannot contain any unicode. Comments may contain
        # unicode, but they are ignored in the key file analysis here, so
        # replacing invalid chars with ? is OK.
        line = f.readline().strip().decode('utf8', 'replace')
        if line:
          return line
        msg = 'is empty'
        status = KeyFileStatus.BROKEN
    except IOError as e:
      if e.errno == errno.ENOENT:
        msg = 'does not exist'
        status = KeyFileStatus.ABSENT
      else:
        msg = 'is not readable'
        status = KeyFileStatus.BROKEN
    log.warn('The %s SSH key file for gcloud %s.', kind, msg)
    return status


class KnownHosts(object):
  """Represents known hosts file, supports read, write and basic key management.

  Currently a very naive, but sufficient, implementation where each entry is
  simply a string, and all entries are list of those strings.
  """

  # TODO(b/33467618): Rename the file itself
  DEFAULT_PATH = os.path.realpath(os.path.expanduser(
      os.path.join('~', '.ssh', 'google_compute_known_hosts')))

  def __init__(self, known_hosts, file_path):
    """Construct a known hosts representation based on a list of key strings.

    Args:
      known_hosts: str, list each corresponding to a line in known_hosts_file.
      file_path: str, path to the known_hosts_file.
    """
    self.known_hosts = known_hosts
    self.file_path = file_path

  @classmethod
  def FromFile(cls, file_path):
    """Create a KnownHosts object given a known_hosts_file.

    Args:
      file_path: str, path to the known_hosts_file.

    Returns:
      KnownHosts object corresponding to the file. If the file could not be
      opened, the KnownHosts object will have no entries.
    """
    try:
      known_hosts = files.GetFileContents(file_path).splitlines()
    except files.Error as e:
      known_hosts = []
      log.debug('SSH Known Hosts File [{0}] could not be opened: {1}'
                .format(file_path, e))
    return KnownHosts(known_hosts, file_path)

  @classmethod
  def FromDefaultFile(cls):
    """Create a KnownHosts object from the default known_hosts_file.

    Returns:
      KnownHosts object corresponding to the default known_hosts_file.
    """
    return KnownHosts.FromFile(KnownHosts.DEFAULT_PATH)

  def ContainsAlias(self, host_key_alias):
    """Check if a host key alias exists in one of the known hosts.

    Args:
      host_key_alias: str, the host key alias

    Returns:
      bool, True if host_key_alias is in the known hosts file. If the known
      hosts file couldn't be opened it will be treated as if empty and False
      returned.
    """
    return any(host_key_alias in line for line in self.known_hosts)

  def Add(self, hostname, host_key, overwrite=False):
    """Add or update the entry for the given hostname.

    If there is no entry for the given hostname, it will be added. If there is
    an entry already and overwrite_keys is False, nothing will be changed. If
    there is an entry and overwrite_keys is True, the key will be updated if it
    has changed.

    Args:
      hostname: str, The hostname for the known_hosts entry.
      host_key: str, The host key for the given hostname.
      overwrite: bool, If true, will overwrite the entry corresponding to
        hostname with the new host_key if it already exists. If false and an
        entry already exists for hostname, will ignore the new host_key value.
    """
    new_key_entry = '{0} {1}'.format(hostname, host_key)
    for i, key in enumerate(self.known_hosts):
      if key.startswith(hostname):
        if overwrite:
          self.known_hosts[i] = new_key_entry
        break
    else:
      self.known_hosts.append(new_key_entry)

  def Write(self):
    """Writes the file to disk."""
    with files.OpenForWritingPrivate(self.file_path) as f:
      f.write('\n'.join(self.known_hosts) + '\n')


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
    account_user = gaia.MapGaiaEmailToDefaultAccountName(full_account)
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


def RunExecutable(cmd_args, strict_error_checking=True,
                  ignore_ssh_errors=False):
  """Run the given command, handling errors appropriately.

  Args:
    cmd_args: list of str, the arguments (including executable path) to run
    strict_error_checking: bool, whether a non-zero, non-255 exit code should be
      considered a failure.
    ignore_ssh_errors: bool, when true ignore all errors, including the 255
      exit code.

  Returns:
    int, the return code of the command

  Raises:
    CommandError: if the command failed (based on the command exit code and
      the strict_error_checking flag)
  """
  outfile = SSH_OUTPUT_FILE or os.devnull
  with open(outfile, 'w') as output_file:
    if log.IsUserOutputEnabled() and not SSH_OUTPUT_FILE:
      stdout, stderr = None, None
    else:
      stdout, stderr = output_file, output_file
    if (platforms.OperatingSystem.IsWindows() and
        not cmd_args[0].endswith('winkeygen.exe')):
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
      raise CommandError(cmd_args[0], message=e.strerror)
    if not ignore_ssh_errors:
      if ((returncode and strict_error_checking) or
          returncode == _SSH_ERROR_EXIT_CODE):
        raise CommandError(cmd_args[0], return_code=returncode)
    return returncode


def _SdkHelperBin():
  """Returns the SDK helper executable bin directory."""
  return os.path.join(config.Paths().sdk_root, 'bin', 'sdk')


class SSHCommand(base.Command):
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
        """.format(DEFAULT_SSH_KEY_FILE)
    force_key_file_overwrite = parser.add_argument(
        '--force-key-file-overwrite',
        action='store_true',
        default=None,
        help=('Enable/Disable force overwrite of the files associated with a '
              'broken SSH key.')
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

  def GetPublicKey(self):
    """Generates an SSH key using ssh-keygen (if necessary) and returns it.

    Raises:
      CommandError: if the ssh-keygen command failed.

    Returns:
      str, The public key.
    """
    public_ssh_key_file = self.ssh_key_file + '.pub'

    key_files_summary = KeyFilesVerifier(self.ssh_key_file, public_ssh_key_file)

    key_files_validity = key_files_summary.Validate()

    if key_files_validity is KeyFileStatus.BROKEN:
      key_files_summary.RemoveKeyFilesIfPermittedOrFail(
          self.force_key_file_overwrite)
      # Fallthrough
    if key_files_validity is not KeyFileStatus.PRESENT:
      if key_files_validity is KeyFileStatus.ABSENT:
        # If key is broken, message is already displayed
        log.warn('You do not have an SSH key for gcloud.')
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

      keygen_args = [self.ssh_keygen_executable]
      if platforms.OperatingSystem.IsWindows():
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
      RunExecutable(keygen_args)

    with open(public_ssh_key_file) as f:
      # We get back a unicode list of keys for the remaining metadata, so
      # convert to unicode. Assume UTF 8, but if we miss a character we can just
      # replace it with a '?'. The only source of issues would be the hostnames,
      # which are relatively inconsequential.
      return f.readline().strip().decode('utf8', 'replace')

  def Run(self, args):
    """Subclasses must call this in their Run() before continuing."""

    # Used in GetPublicKey
    self.force_key_file_overwrite = args.force_key_file_overwrite

    if platforms.OperatingSystem.IsWindows():
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
        args.ssh_key_file or DEFAULT_SSH_KEY_FILE))


class SSHCLICommand(SSHCommand):
  """Base class for subcommands that use ssh or scp."""

  @staticmethod
  def Args(parser):
    SSHCommand.Args(parser)

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
        '-o', 'UserKnownHostsFile={0}'.format(KnownHosts.DEFAULT_PATH),
        '-o', 'IdentitiesOnly=yes',  # ensure our SSH key trumps any ssh_agent
        '-o', 'CheckHostIP=no'
    ]

  def _LocalizeWindowsCommand(self, cmd_args):
    """Translate cmd_args[1:] from ssh form to plink/putty form.

     The translations are:

        ssh form                      plink/putty form
        ========                      ================
        -i PRIVATE_KEY_FILE           -i PRIVATE_KEY_FILE.ppk
        -o ANYTHING                   <ignore>
        -p PORT                       -P PORT
        [USER]@HOST                   [USER]@HOST
        -BOOLEAN_FLAG                 -BOOLEAN_FLAG
        -FLAG WITH_VALUE              -FLAG WITH_VALUE
        POSITIONAL                    POSITIONAL

    Args:
      cmd_args: [str], The command line that will be executed.

    Returns:
      Returns translated_cmd_args, the localized command line.
    """
    positionals = 0
    cmd_args = list(cmd_args)  # Get a mutable copy.
    translated_args = [cmd_args.pop(0)]
    while cmd_args:  # Each iteration processes 1 or 2 args.
      arg = cmd_args.pop(0)
      if arg == '-i' and cmd_args:
        # -i private_key_file -- use private_key_file.ppk -- if it doesn't exist
        # then winkeygen will be called to generate it before attempting to
        # connect.
        translated_args.append(arg)
        translated_args.append(cmd_args.pop(0) + '.ppk')
      elif arg == '-o' and cmd_args:
        # Ignore `-o anything'.
        cmd_args.pop(0)
      elif arg == '-p' and cmd_args:
        # -p PORT => -P PORT
        translated_args.append('-P')
        translated_args.append(cmd_args.pop(0))
      elif arg in ['-2', '-a', '-C', '-l', '-load', '-m', '-pw', '-R', '-T',
                   '-v', '-x'] and cmd_args:
        # Pass through putty/plink flag with value.
        translated_args.append(arg)
        translated_args.append(cmd_args.pop(0))
      elif arg.startswith('-'):
        # Pass through putty/plink Boolean flags
        translated_args.append(arg)
      else:
        positionals += 1
        translated_args.append(arg)

    # If there is only 1 positional then it must be [USER@]HOST and we should
    # use self.ssh_term_executable to open an xterm window.
    if positionals == 1 and translated_args[0] == self.ssh_executable:
      translated_args[0] = self.ssh_term_executable

    return translated_args

  def LocalizeCommand(self, cmd_args):
    """Translates an ssh/scp command line to match the local implementation.

    Args:
      cmd_args: [str], The command line that will be executed.

    Returns:
      Returns translated_cmd_args, the localized command line.
    """
    if platforms.OperatingSystem.IsWindows():
      return self._LocalizeWindowsCommand(cmd_args)
    return cmd_args

  def GetHostKeyArgs(self, args, host_key_alias):
    """Returns default values for HostKeyAlias and StrictHostKeyChecking.

    Args:
      args: argparse.Namespace, The calling command invocation args.
      host_key_alias: Alias of the host key in the known_hosts file.

    Returns:
      list, list of arguments to add to the ssh command line.
    """
    if args.plain or platforms.OperatingSystem.IsWindows():
      return []

    known_hosts = KnownHosts.FromDefaultFile()
    if args.strict_host_key_checking:
      strict_host_key_value = args.strict_host_key_checking
    elif known_hosts.ContainsAlias(host_key_alias):
      strict_host_key_value = 'yes'
    else:
      strict_host_key_value = 'no'

    cmd_args = ['-o', 'HostKeyAlias={0}'.format(host_key_alias), '-o',
                'StrictHostKeyChecking={0}'.format(strict_host_key_value)]
    return cmd_args

  def WaitUntilSSHable(self, args, user, host, host_key_alias,
                       timeout=_DEFAULT_TIMEOUT):
    """Blocks until SSHing to the given host succeeds."""
    ssh_args_for_polling = [self.ssh_executable]
    ssh_args_for_polling.extend(self.GetDefaultFlags())
    ssh_args_for_polling.extend(self.GetHostKeyArgs(args, host_key_alias))

    ssh_args_for_polling.append(UserHost(user, host))
    ssh_args_for_polling.append('true')
    ssh_args_for_polling = self.LocalizeCommand(ssh_args_for_polling)

    start_sec = time_util.CurrentTimeSec()
    while True:
      logging.debug('polling instance for SSHability')
      retval = subprocess.call(ssh_args_for_polling)
      if retval == 0:
        break
      if time_util.CurrentTimeSec() - start_sec > timeout:
        raise exceptions.ToolException(
            'Could not SSH to the instance.  It is possible that '
            'your SSH key has not propagated to the instance yet. '
            'Try running this command again.  If you still cannot connect, '
            'verify that the firewall and instance are set to accept '
            'ssh traffic.')
      time_util.Sleep(5)


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
