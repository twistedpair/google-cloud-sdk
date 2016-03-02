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

import httplib
import json
import os
import os.path
import subprocess
import threading
import time
import urllib

from googlecloudsdk.api_lib.emulators import util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import platforms
from tests.lib import exec_utils


class BrokerError(exceptions.Error):
  pass


class BrokerNotRunningError(BrokerError):
  pass


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

  def __init__(self, address, config_file=None, conn_factory=None):
    """Constructor.

    Args:
      address: The host or host-port of the broker server. The server may
          already be running.
      config_file: The full path to the broker config file.
      conn_factory: Factory for HTTPConnection objects.
    """
    if config_file is not None:
      assert os.path.isabs(config_file)

    self._address = address
    self._config_file = config_file
    self._conn_factory = conn_factory

    self._host_port = arg_parsers.HostPort.Parse(address)
    self._broker_dir = os.path.join(util.GetCloudSDKRoot(), 'bin', 'broker')
    self._current_platform = platforms.Platform.Current()
    self._process = None
    self._comm_thread = None

  def Start(self, redirect_output=False, logtostderr=False, wait_secs=10):
    """Starts the broker server, optionally with output redirection."""
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
    # We issue an RPC to check if the broker is running.
    try:
      response, _ = self._SendJsonRequest('GET', _EmulatorPath())
      return response.status == httplib.OK
    except IOError:
      return False

  def Shutdown(self, wait_secs=10):
    """Shuts down the broker server."""
    if self._process:
      try:
        exec_utils.KillSubprocess(self._process)
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
      except IOError:
        raise BrokerError('Broker failed to shutdown: '
                          'failed to send shutdown request')
      except httplib.HTTPException:
        # We may get an exception reading the response to the shutdown request,
        # because the shutdown may preempt the response.
        pass

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
    """Creates a new emulator entry."""
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
    try:
      response, data = self._SendJsonRequest('POST', url, body=body)
      if response.status != httplib.OK:
        log.warn('Failed to create emulator: {0} ({1})'.format(response.reason,
                                                               response.status))
        raise BrokerError('Failed to create emulator: %s' % data)
    except IOError:
      raise BrokerError('Failed to create emulator: '
                        'failed to send create request')

  def GetEmulator(self, emulator_id):
    """Returns emulator entry (Json dict)."""
    if not self.IsRunning():
      raise BrokerNotRunningError('Failed to get emulator: %s' % emulator_id)

    try:
      response, data = self._SendJsonRequest('GET', _EmulatorPath(emulator_id))
      if response.status != httplib.OK:
        raise BrokerError('Failed to get emulator: %s' % data)
    except IOError:
      raise BrokerError('Failed to get emulator: failed to send get request')

    return json.loads(data)

  def ListEmulators(self):
    """Returns the list of emulators, or None.

    Returns:
      A list of emulator objects (Json dicts), or None if the list operation
      fails.

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
    except IOError:
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
    try:
      response, data = self._SendJsonRequest('POST', url)
      if response.status != httplib.OK:
        log.warn('Failed to start emulator {0}: {1} ({2})'.format(
            emulator_id, response.reason, response.status))
        raise BrokerError('Failed to start emulator: %s' % data)
    except IOError:
      raise BrokerError('Failed to start emulator: '
                        'failed to send start request')

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
    try:
      response, data = self._SendJsonRequest('POST', url)
      if response.status != httplib.OK:
        log.warn('Failed to stop emulator {0}: {1} ({2})'.format(
            emulator_id, response.reason, response.status))
        raise BrokerError('Failed to stop emulator: %s' % data)
    except IOError:
      raise BrokerError('Failed to stop emulator: failed to send stop request')

  def _BrokerBinary(self):
    """Returns the path to the broker binary."""
    return '{0}/broker'.format(self._broker_dir)

  def _NewConnection(self):
    """Returns a new HTTPConnection to the broker address."""
    if self._conn_factory:
      return self._conn_factory(self._address)
    return httplib.HTTPConnection(self._address)

  def _SendJsonRequest(self, method, url, body=None):
    """Sends a request to the broker.

    Args:
      method: (str) The HTTP method.
      url: (str) The URL path.
      body: (str) The request body.

    Returns:
      (HTTPResponse, str) or (None, None).

    Raises:
      IOError: The request could not be sent.
    """
    conn = self._NewConnection()
    headers = {}
    if body is not None:
      headers['Content-Type'] = 'application/json'
    try:
      conn.request(method, url, body=body, headers=headers)
      resp = conn.getresponse()
      data = resp.read()
      return (resp, data)
    except IOError as e:
      log.debug('Error sending request: %r', e)
      raise
    finally:
      conn.close()
