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
"""Utility library for configuring access to the Google Container Registry.

Sets docker up to authenticate with the Google Container Registry using the
active gcloud credential.
"""

import base64
import errno
import json
import os
import subprocess
import sys
import tempfile
import urlparse

from distutils import version as distutils_version
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.credentials import store
from googlecloudsdk.core.docker import constants
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms

_USERNAME = 'oauth2accesstoken'
_EMAIL = 'not@val.id'
_EMAIL_FLAG_DEPRECATED_VERSION = distutils_version.LooseVersion('1.11.0')
_DOCKER_NOT_FOUND_ERROR = 'Docker is not installed.'
_CREDENTIAL_STORE_KEY = 'credsStore'


def _GetUserHomeDir():
  if platforms.OperatingSystem.Current() == platforms.OperatingSystem.WINDOWS:
    # %HOME% has precedence over %USERPROFILE% for os.path.expanduser('~')
    # The Docker config resides under %USERPROFILE% on Windows
    return os.path.expandvars('%USERPROFILE%')
  else:
    return platforms.GetHomePath()


def _GetNewConfigDirectory():
  # Return the value of $DOCKER_CONFIG, if it exists, otherwise ~/.docker
  # see https://github.com/docker/docker/blob/master/cliconfig/config.go
  if os.environ.get('DOCKER_CONFIG') is not None:
    return os.environ.get('DOCKER_CONFIG')
  else:
    return os.path.join(_GetUserHomeDir(), '.docker')


class DockerError(exceptions.Error):
  """Base class for docker errors."""


class InvalidDockerConfigError(DockerError):
  """The docker configuration file could not be read."""


class UnsupportedRegistryError(DockerError):
  """Indicates an attempt to use an unsupported registry."""

  def __init__(self, image_url):
    self.image_url = image_url

  def __str__(self):
    return ('{0} is not in a supported registry.  Supported registries are '
            '{1}'.format(self.image_url, constants.ALL_SUPPORTED_REGISTRIES))


# Other tools like the python docker library (used by gcloud app)
# also rely on Docker's authorization configuration (in addition
# to the docker CLI client)
# NOTE: Lazy for manipulation of HOME / mocking.
def GetDockerConfig(force_new=False):
  """Retrieve the path to Docker's configuration file, noting its format.

  Args:
    force_new: bool, whether to force usage of the new config file regardless
               of whether it exists (for testing).

  Returns:
    The path to Docker's configuration file, and whether it is in the
    new configuration format.
  """
  # Starting in Docker 1.7.0, the Docker client moved where it writes
  # credentials to ~/.docker/config.json.  It is half backwards-compatible,
  # if the new file doesn't exist, it falls back on the old file.
  # if the new file exists, it IGNORES the old file.
  # This is a problem when a user has logged into another registry on 1.7.0
  # and then uses 'gcloud docker'.
  # This must remain compatible with: https://github.com/docker/docker-py
  new_path = os.path.join(_GetNewConfigDirectory(), 'config.json')
  if os.path.exists(new_path) or force_new:
    return new_path, True

  # Only one location will be probed to locate the new config.
  # This is consistent with the Docker client's behavior:
  # https://github.com/docker/docker/blob/master/cliconfig/config.go#L83
  old_path = os.path.join(_GetUserHomeDir(), '.dockercfg')
  return old_path, False


def _ReadFullDockerConfiguration():
  """Retrieve the full contents of the Docker configuration file.

  Returns:
    The full contents of the configuration file, and whether it
    is in the new configuration format.
  """
  path, new_format = GetDockerConfig()
  with open(path, 'r') as reader:
    contents = reader.read()
    # If the file is empty, return empty JSON.
    # This helps if someone 'touched' the file or manually deleted the contents.
    if not contents or contents.isspace():
      return {}, new_format

    try:
      return json.loads(contents), new_format
    except ValueError as err:
      raise InvalidDockerConfigError(
          ('Docker configuration file [{}] could not be read as JSON: '
           '{}').format(path, str(err)))


def _CredentialHelperConfigured():
  """Returns True if a credential helper is specified in the docker config.

  Returns:
    True if a credential helper is specified in the docker config.
    False if the config file does not exist or does not contain a
    'credsStore' key.
  """
  try:
    new_config_1_7_0_plus, new_format = _ReadFullDockerConfiguration()
    if new_format:
      return _CREDENTIAL_STORE_KEY in new_config_1_7_0_plus
    else:
      # The old format is for Docker <1.7.0.
      # Older Docker clients (<1.11.0) don't support credential helpers.
      return False
  except IOError:
    # Config file doesn't exist.
    return False


def _GCRCredHelperConfigured():
  """Returns True if docker-credential-gcr is the docker credential store.

  Returns:
    True if docker-credential-gcr is specified in the docker config.
    False if the config file does not exist, does not contain a
    'credsStore' key, or if the credstore is not docker-credential-gcr.
  """
  try:
    new_config_1_7_0_plus, new_format = _ReadFullDockerConfiguration()
    if new_format and _CREDENTIAL_STORE_KEY in new_config_1_7_0_plus:
      return new_config_1_7_0_plus[_CREDENTIAL_STORE_KEY] == 'gcr'
    else:
      # Docker <1.7.0 (no credential store support) or credsStore == null
      return False
  except IOError:
    # Config file doesn't exist or can't be parsed.
    return False


def ReadDockerConfig():
  """Retrieve the contents of the Docker authorization entry.

  NOTE: This is public only to facilitate testing.

  Returns:
    The map of authorizations used by docker.
  """
  structure, new_format = _ReadFullDockerConfiguration()
  if new_format:
    return structure['auths'] if 'auths' in structure else {}
  else:
    return structure


def WriteDockerConfig(structure):
  """Write out a complete set of Docker authorization entries.

  This is public only to facilitate testing.

  Args:
    structure: The dict of authorization mappings to write to the
               Docker configuration file.
  """
  cfg, new_format = GetDockerConfig()
  if new_format:
    full_cfg, _ = _ReadFullDockerConfiguration()
    full_cfg['auths'] = structure
    contents = json.dumps(full_cfg, indent=2)
  else:
    contents = json.dumps(structure, indent=2)

  if platforms.OperatingSystem.Current() == platforms.OperatingSystem.WINDOWS:
    # On windows, there is no good way to atomically write this file.
    with files.OpenForWritingPrivate(cfg) as writer:
      writer.write(contents)
    return

  # This opens files with 0600, which are the correct permissions.
  with tempfile.NamedTemporaryFile(
      dir=os.path.dirname(cfg), delete=False) as tf:
    tf.write(contents)
    # This was a user-submitted patch to fix a race condition that we couldn't
    # reproduce. It may be due to the file being renamed before the OS's buffer
    # flushes to disk.
    tf.flush()
    # This pattern atomically writes the file on non-Windows systems.
    os.rename(tf.name, cfg)


def UpdateDockerCredentials(server, refresh=True):
  """Updates the docker config to have fresh credentials.

  This reads the current contents of Docker's keyring, and extends it with
  a fresh entry for the provided 'server', based on the active gcloud
  credential.  If a credential exists for 'server' this replaces it.

  Args:
    server: The hostname of the registry for which we're freshening
       the credential.
    refresh: Whether to force a token refresh on the active credential.

  Raises:
    store.Error: There was an error loading the credentials.
  """

  # Loading credentials will ensure that we're logged in.
  # And prompt/abort to 'run gcloud auth login' otherwise.
  # Disable refreshing, since we'll do this ourself.
  cred = store.Load(prevent_refresh=True)

  if refresh:
    # Ensure our credential has a valid access token,
    # which has the full duration available.
    store.Refresh(cred)

  if not cred.access_token:
    raise exceptions.Error(
        'No access token could be obtained from the current credentials.')

  url = _GetNormalizedURL(server)
  # Strip the port, if it exists. It's OK to butcher IPv6, this is only an
  # optimization for hostnames in constants.ALL_SUPPORTED_REGISTRIES.
  hostname = url.hostname.split(':')[0]

  third_party_cred_helper = (_CredentialHelperConfigured() and
                             not _GCRCredHelperConfigured())
  if (third_party_cred_helper or
      hostname not in constants.ALL_SUPPORTED_REGISTRIES):
    # If this is a custom host or if there's a third-party credential helper...
    try:
      # Update the credentials stored by docker, passing the access token
      # as a password, and benign values as the email and username.
      _DockerLogin(server, _EMAIL, _USERNAME, cred.access_token)
    except DockerError as e:
      # Only catch docker-not-found error
      if str(e) != _DOCKER_NOT_FOUND_ERROR:
        raise

      # Fall back to the previous manual .dockercfg manipulation
      # in order to support gcloud app's docker-binaryless use case.
      _UpdateDockerConfig(server, _USERNAME, cred.access_token)
      log.warn("'docker' was not discovered on the path. Credentials have been "
               'stored, but are not guaranteed to work with the Docker client '
               ' if an external credential store is configured.')
  elif not _GCRCredHelperConfigured():
    # If this is not a custom host and no third-party cred helper...
    _UpdateDockerConfig(server, _USERNAME, cred.access_token)

  # If this is a default registry and docker-credential-gcr is configured, no-op


def _DockerLogin(server, email, username, access_token):
  """Register the username / token for the given server on Docker's keyring."""

  # Sanitize and normalize the server input.
  parsed_url = _GetNormalizedURL(server)

  server = parsed_url.geturl()

  # 'docker login' must be used due to the change introduced in
  # https://github.com/docker/docker/pull/20107 .
  docker_args = ['login']
  if not _EmailFlagDeprecatedForDockerVersion():
    docker_args.append('--email=' + email)
  docker_args.append('--username=' + username)
  docker_args.append('--password=' + access_token)
  docker_args.append(server)  # The auth endpoint must be the last argument.

  docker_p = _GetProcess(
      docker_args,
      stdin_file=sys.stdin,
      stdout_file=subprocess.PIPE,
      stderr_file=subprocess.PIPE)

  # Wait for docker to finished executing and retrieve its stdout/stderr.
  stdoutdata, stderrdata = docker_p.communicate()

  if docker_p.returncode == 0:
    # If the login was successful, print only unexpected info.
    _SurfaceUnexpectedInfo(stdoutdata, stderrdata)
  else:
    # If the login failed, print everything.
    log.error('Docker CLI operation failed:')
    log.out.Print(stdoutdata)
    log.status.Print(stderrdata)
    raise DockerError('Docker login failed.')


def _EmailFlagDeprecatedForDockerVersion():
  """Checks to see if --email flag is deprecated.

  Returns:
    True if the installed Docker client version has deprecated the
    --email flag during 'docker login,' False otherwise.
  """
  try:
    version = _GetDockerVersion()

  except exceptions.Error:
    # Docker doesn't exist or doesn't like the modern version query format.
    # Assume that --email is not deprecated, return False.
    return False

  return version >= _EMAIL_FLAG_DEPRECATED_VERSION


def _GetDockerVersion():
  """Returns the installed Docker client version.

  Returns:
    The installed Docker client version.

  Raises:
    DockerError: Docker cannot be run or does not accept 'docker version
    --format '{{.Client.Version}}''.
  """
  docker_args = "version --format '{{.Client.Version}}'".split()

  docker_p = _GetProcess(
      docker_args,
      stdin_file=sys.stdin,
      stdout_file=subprocess.PIPE,
      stderr_file=subprocess.PIPE)

  # Wait for docker to finished executing and retrieve its stdout/stderr.
  stdoutdata, _ = docker_p.communicate()

  if docker_p.returncode != 0 or not stdoutdata:
    raise DockerError('could not retrieve Docker client version')

  # Remove ' from beginning and end of line.
  return distutils_version.LooseVersion(stdoutdata.strip("'"))


def _SurfaceUnexpectedInfo(stdoutdata, stderrdata):
  """Reads docker's output and surfaces unexpected lines.

  Docker's CLI has a certain amount of chattiness, even on successes.

  Args:
    stdoutdata: The raw data output from the pipe given to Popen as stdout.
    stderrdata: The raw data output from the pipe given to Popen as stderr.
  """

  # Split the outputs by lines.
  stdout = [s.strip() for s in stdoutdata.splitlines()]
  stderr = [s.strip() for s in stderrdata.splitlines()]

  for line in stdout:
    # Swallow 'Login Succeeded' and 'saved in,' surface any other std output.
    if (line != 'Login Succeeded') and (
        'login credentials saved in' not in line):
      line = '%s%s' % (line, os.linesep)
      log.out.Print(line)  # log.out => stdout

  for line in stderr:
    # Swallow warnings about --email and 'saved in', surface any other error
    # output.
    if ('--email' not in line) and ('login credentials saved in' not in line):
      line = '%s%s' % (line, os.linesep)
      log.status.Print(line)  # log.status => stderr


def _UpdateDockerConfig(server, username, access_token):
  """Register the username / token for the given server on Docker's keyring."""

  # NOTE: using "docker login" doesn't work as they're quite strict on what
  # is allowed in username/password.
  try:
    dockercfg_contents = ReadDockerConfig()
  except IOError:
    # If the file doesn't exist, start with an empty map.
    dockercfg_contents = {}

  # Add the entry for our server.
  auth = base64.b64encode(username + ':' + access_token)

  # Sanitize and normalize the server input.
  parsed_url = _GetNormalizedURL(server)

  server = parsed_url.geturl()
  server_unqualified = parsed_url.hostname

  # Clear out any unqualified stale entry for this server
  if server_unqualified in dockercfg_contents:
    del dockercfg_contents[server_unqualified]

  dockercfg_contents[server] = {'auth': auth, 'email': _EMAIL}

  WriteDockerConfig(dockercfg_contents)


def _GetNormalizedURL(server):
  """Sanitize and normalize the server input."""
  parsed_url = urlparse.urlparse(server)
  # Work around the fact that Python 2.6 does not properly
  # look for :// and simply splits on colon, so something
  # like 'gcr.io:1234' returns the scheme 'gcr.io'.
  if '://' not in server:
    # Server doesn't have a scheme, set it to HTTPS.
    parsed_url = urlparse.urlparse('https://' + server)
    if parsed_url.hostname == 'localhost':
      # Now that it parses, if the hostname is localhost switch to HTTP.
      parsed_url = urlparse.urlparse('http://' + server)

  return parsed_url


def EnsureDocker(func):
  """Wraps a function that uses subprocess to invoke docker.

  Rewrites OS Exceptions when not installed.

  Args:
    func: A function that uses subprocess to invoke docker.

  Returns:
    The decorated function.

  Raises:
    Error: Docker cannot be run.
  """

  def DockerFunc(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except OSError as e:
      if e.errno == errno.ENOENT:
        raise DockerError(_DOCKER_NOT_FOUND_ERROR)
      else:
        raise

  return DockerFunc


@EnsureDocker
def Execute(args):
  """Wraps an invocation of the docker client with the specified CLI arguments.

  Args:
    args: The list of command-line arguments to docker.

  Returns:
    The exit code from Docker.
  """
  return subprocess.call(
      ['docker'] + args, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


@EnsureDocker
def _GetProcess(docker_args, stdin_file, stdout_file, stderr_file):
  # Wraps the construction of a docker subprocess object with the specified
  # arguments and I/O files.
  return subprocess.Popen(
      ['docker'] + docker_args,
      stdin=stdin_file,
      stdout=stdout_file,
      stderr=stderr_file)
