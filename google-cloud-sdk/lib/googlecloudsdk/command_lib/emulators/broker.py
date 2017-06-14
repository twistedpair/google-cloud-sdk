# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Library for controlling instances of cloud-testenv-broker processes."""

import errno
import httplib
import json
import os
import os.path
import socket
import subprocess
import threading
import time
import urllib

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.emulators import util
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core.util import platforms
import httplib2


class BrokerError(exceptions.ToolException):
  """All errors raised by this module subclass BrokerError."""
  pass


class BrokerNotRunningError(BrokerError):
  pass


class RequestError(BrokerError):
  """Errors associated with failed HTTP requests subclass RequestError."""
  pass


class RequestTimeoutError(RequestError):
  pass


class RequestSocketError(RequestError):
  """A socket error. Check the errno field."""

  def __init__(self, *args, **kwargs):
    super(RequestError, self).__init__(*args)
    self.errno = None


def SocketConnResetErrno():
  """The errno value for a socket connection reset error."""
  current_os = platforms.OperatingSystem.Current()
  if current_os == platforms.OperatingSystem.WINDOWS:
    return errno.WSAECONNRESET
  return errno.ECONNRESET


def SocketConnRefusedErrno():
  """The errno value for a socket connection refused error."""
  current_os = platforms.OperatingSystem.Current()
  if current_os == platforms.OperatingSystem.WINDOWS:
    return errno.WSAECONNREFUSED
  return errno.ECONNREFUSED


def _Await(fn, timeout_secs):
  """Waits up to timeout_secs for fn() to return True."""
  deadline = time.time() + timeout_secs
  while time.time() < deadline:
    if fn():
      return True
    time.sleep(0.2)

  return False


def _EmulatorPath(emulator_id=None, verb=None):
  """Builds a broker request path for operating on the specified emulator."""
  path = '/v1/emulators'
  if emulator_id:
    path += '/' + urllib.quote(emulator_id)
    if verb:
      path += ':' + urllib.quote(verb)
  return path


class Broker(object):
  """Broker manages a single instance of a broker process.

  The broker process may be started through an instance of this class. An
  already-running process can be manipulated through an instance of this class
  as well.
  """

  def __init__(self, address, config_file=None, broker_dir=None):
    """Constructor.

    Args:
      address: (str) The host or host-port of the broker server. The server may
          already be running.
      config_file: (str) The full path to the broker config file.
      broker_dir: (str) A custom path to the broker directory.
    """
    if config_file is not None:
      assert os.path.isabs(config_file)

    self._address = address
    self._config_file = config_file
    if broker_dir:
      self._broker_dir = broker_dir
    else:
      self._broker_dir = os.path.join(util.GetCloudSDKRoot(), 'bin', 'broker')

    self._host_port = arg_parsers.HostPort.Parse(address)
    self._current_platform = platforms.Platform.Current()
    self._process = None
    self._comm_thread = None

  def Start(self, redirect_output=False, logtostderr=False, wait_secs=10):
    """Starts the broker server, optionally with output redirection.

    Args:
      redirect_output: (bool) Whether to merge the stdout and stderr of the
          broker server with the current process' output.
      logtostderr: (bool) Whether the broker should log to stderr instead of
          to a log file.
      wait_secs: (float) The maximum time to wait for the broker to start
          serving.

    Raises:
      BrokerError: If start failed.
    """
    if self._process or self.IsRunning():
      # Already started, possibly by another process.
      return

    args = [self._BrokerBinary()]
    if self._host_port.host:
      args.append('--host={0}'.format(self._host_port.host))
    if self._host_port.port:
      args.append('--port={0}'.format(self._host_port.port))
    if self._config_file:
      args.append('--config_file={0}'.format(self._config_file))
    if logtostderr:
      args.append('--logtostderr')  # Disables file logging.

    # The broker is run as a detached (daemon) process.
    popen_args = self._current_platform.AsyncPopenArgs()

    log.info('Starting broker: %r', args)

    if redirect_output:
      # Pipe the broker's output to our own, communicating on another thread
      # to avoid blocking the current thread.
      self._process = subprocess.Popen(args,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       **popen_args)
      self._comm_thread = threading.Thread(target=self._process.communicate)
      self._comm_thread.start()
    else:
      self._process = subprocess.Popen(args, **popen_args)

    if not _Await(self.IsRunning, wait_secs):
      log.warn('Broker did not start within {0}s'.format(wait_secs))
      try:
        # Clean up.
        self.Shutdown()
      except BrokerError:
        pass
      raise BrokerError('Broker failed to start')

    log.info('Started broker: %s' % self._address)

  def IsRunning(self):
    """Returns True iff the broker is known to be running."""
    # We issue an RPC to check if the broker is running.
    try:
      response, _ = self._SendJsonRequest('GET', _EmulatorPath(),
                                          timeout_secs=1.0)
      return response.status == httplib.OK
    except RequestError:
      return False

  def Shutdown(self, wait_secs=10):
    """Shuts down the broker server.

    Args:
      wait_secs: (float) The maximum time to wait for the broker to shutdown.

    Raises:
      BrokerError: If shutdown failed.
    """
    if self._process:
      try:
        execution_utils.KillSubprocess(self._process)
        self._process = None
        if self._comm_thread:
          self._comm_thread.join()
          self._comm_thread = None
      except RuntimeError as e:
        log.warn('Failed to shutdown broker: %s' % e)
        raise BrokerError('Broker failed to shutdown: %s' % e)
    else:
      # Invoke the /shutdown handler.
      try:
        self._SendJsonRequest('POST', '/shutdown')
      except RequestSocketError as e:
        if e.errno not in (SocketConnRefusedErrno(), SocketConnResetErrno()):
          raise
        # We may get an exception reading the response to the shutdown
        # request, because the shutdown may preempt the response.

    if not _Await(lambda: not self.IsRunning(), wait_secs):
      log.warn('Failed to shutdown broker: still running after {0}s'.format(
          wait_secs))
      raise BrokerError('Broker failed to shutdown: timed-out')

    log.info('Shutdown broker.')

  def CreateEmulator(self,
                     emulator_id,
                     path,
                     args,
                     target_patterns,
                     resolved_host=None):
    """Creates a new emulator entry.

    Args:
      emulator_id: (str) The emulator id
      path: (str) The path to the emulator binary.
      args: (list of str) The command line arguments to the emulator.
      target_patterns: (list or str) The regular expressions used to match
          input targets for the emulator.
      resolved_host: (str) The address to use when resolving the new emulator.
          Only specified if the lifetime of this emulator is not managed by
          this broker.

    Raises:
      BrokerNotRunningError: If the broker is not running.
      BrokerError: If the creation failed.
    """
    if not self.IsRunning():
      raise BrokerNotRunningError('Failed to create emulator')

    emulator = {
        'emulator_id': emulator_id,
        'start_command': {
            'path': path,
            'args': args,
        },
        'rule': {
            'rule_id': emulator_id,
            'target_patterns': target_patterns,
        }
    }
    if resolved_host:
      emulator['rule']['resolved_host'] = resolved_host

    url = _EmulatorPath()
    body = json.dumps(emulator)
    response, data = self._SendJsonRequest('POST', url, body=body)
    if response.status != httplib.OK:
      log.warn('Failed to create emulator: {0} ({1})'.format(response.reason,
                                                             response.status))
      raise BrokerError('Failed to create emulator: %s' % data)

  def GetEmulator(self, emulator_id):
    """Returns emulator entry (Json dict).

    Args:
      emulator_id: (str) The id of the emulator to get.

    Returns:
      A Json dict representation of a google.emulators.Emulator proto message.

    Raises:
      BrokerNotRunningError: If the broker is not running.
      BrokerError: If the get failed.
    """
    if not self.IsRunning():
      raise BrokerNotRunningError('Failed to get emulator: %s' % emulator_id)

    response, data = self._SendJsonRequest('GET', _EmulatorPath(emulator_id))
    if response.status != httplib.OK:
      raise BrokerError('Failed to get emulator: %s' % data)

    return json.loads(data)

  def ListEmulators(self):
    """Returns the list of emulators, or None.

    Returns:
      A list of Json dicts representing google.emulators.Emulator proto
      messages, or None if the list operation fails.

    Raises:
      BrokerNotRunningError: If the broker is not running.
    """
    if not self.IsRunning():
      raise BrokerNotRunningError('Failed to list emulators')

    try:
      response, data = self._SendJsonRequest('GET', _EmulatorPath())
      if response.status != httplib.OK:
        log.warn('Failed to list emulators: {0} ({1})'.format(response.reason,
                                                              response.status))
        return
    except RequestError:
      return

    list_response = json.loads(data)
    try:
      return list_response['emulators']
    except KeyError:
      # The expected values were not present.
      return

  def StartEmulator(self, emulator_id):
    """Starts the specified emulator via the broker, which must be running.

    Args:
      emulator_id: (str) The id of the emulator to start.

    Returns:
      True if the emulator is started. False if it was already running, cannot
      be started, or is unknown.

    Raises:
      BrokerNotRunningError: If the broker is not running.
      BrokerError: If the emulator could not be started for another reason.
    """
    if not self.IsRunning():
      raise BrokerNotRunningError('Failed to start emulator: %s' % emulator_id)

    url = _EmulatorPath(emulator_id, verb='start')
    response, data = self._SendJsonRequest('POST', url)
    if response.status != httplib.OK:
      log.warn('Failed to start emulator {0}: {1} ({2})'.format(
          emulator_id, response.reason, response.status))
      raise BrokerError('Failed to start emulator: %s' % data)

  def StopEmulator(self, emulator_id):
    """Stops the specified emulator via the broker, which must be running.

    Args:
      emulator_id: (str) The id of the emulator to stop.

    Returns:
      True if the emulator is stopped or wasn't running to begin with. False
      if the emulator could not be stopped or is unknown.

    Raises:
      BrokerNotRunningError: If the broker is not running.
      BrokerError: If the emulator could not be stopped for another reason.
    """
    if not self.IsRunning():
      raise BrokerNotRunningError('Failed to stop emulator: %s' % emulator_id)

    url = _EmulatorPath(emulator_id, verb='stop')
    response, data = self._SendJsonRequest('POST', url)
    if response.status != httplib.OK:
      log.warn('Failed to stop emulator {0}: {1} ({2})'.format(
          emulator_id, response.reason, response.status))
      raise BrokerError('Failed to stop emulator: %s' % data)

  def _BrokerBinary(self):
    """Returns the path to the broker binary."""
    return '{0}/broker'.format(self._broker_dir)

  def _SendJsonRequest(self, method, path, body=None, timeout_secs=300):
    """Sends a request to the broker.

    Args:
      method: (str) The HTTP method.
      path: (str) The URI path.
      body: (str) The request body.
      timeout_secs: (float) The request timeout, in seconds.

    Returns:
      (HTTPResponse, str) or (None, None).

    Raises:
      RequestTimeoutError: The request timed-out.
      RequestSocketError: The request failed due to a socket error.
      RequestError: The request errored out in some other way.
    """
    uri = 'http://{0}{1}'.format(self._address, path)
    http_client = httplib2.Http(timeout=timeout_secs)
    try:
      return http_client.request(
          uri=uri,
          method=method,
          headers={'Content-Type': 'application/json; charset=UTF-8'},
          body=body)
    except socket.error as e:
      if isinstance(e, socket.timeout):
        raise RequestTimeoutError(e)
      error = RequestSocketError(e)
      if e.errno:
        error.errno = e.errno
      raise error
    except httplib.HTTPException as e:
      if isinstance(e, httplib.ResponseNotReady):
        raise RequestTimeoutError(e)
      raise RequestError(e)
    except httplib2.HttpLib2Error as e:
      raise RequestError(e)
