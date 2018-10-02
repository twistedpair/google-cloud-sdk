# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Library for integrating serverless with GKE."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64
import contextlib
import os
import socket
import tempfile
import threading
from googlecloudsdk.api_lib.container import api_adapter
from googlecloudsdk.core import exceptions
from googlecloudsdk.core.util import files


class NoCaCertError(exceptions.Error):
  pass


class _AddressPatches(object):
  """Singleton class to hold patches on getaddrinfo."""

  _instance = None

  @classmethod
  def Initialize(cls):
    assert not cls._instance
    cls._instance = cls()

  @classmethod
  def Get(cls):
    assert cls._instance
    return cls._instance

  def __init__(self):
    self._custom_address_map = None
    self._old_getaddrinfo = None
    self._lock = threading.Lock()

  @contextlib.contextmanager
  def MonkeypatchGetaddrinfo(self, hostname, ip):
    """Change getaddrinfo for a "fake /etc/hosts" effect, implementation."""
    with self._lock:
      if self._custom_address_map is None:
        self._custom_address_map = {}
        self._old_getaddrinfo = socket.getaddrinfo
        socket.getaddrinfo = self._GetAddrInfo
      if hostname in self._custom_address_map:
        raise ValueError(
            'Cannot re-patch the same address: {}'.format(hostname))
      self._custom_address_map[hostname] = ip
    try:
      yield
    finally:
      with self._lock:
        del self._custom_address_map[hostname]
        if not self._custom_address_map:
          self._custom_address_map = None
          socket.getaddrinfo = self._old_getaddrinfo

  def _GetAddrInfo(self, host, *args, **kwargs):
    """Like socket.getaddrinfo, only with translation."""
    with self._lock:
      assert self._custom_address_map is not None
      if host in self._custom_address_map:
        host = self._custom_address_map[host]
    return self._old_getaddrinfo(host, *args, **kwargs)

_AddressPatches.Initialize()


def MonkeypatchGetaddrinfo(hostname, ip):
  """Change getaddrinfo to allow a "fake /etc/hosts" effect.

  GKE provides an IP address for talking to the k8s master, and a
  ca_certs that signs the tls certificate the master provides. Unfortunately,
  that tls certificate is for `kubernetes`, `kubernetes.default`,
  `kubernetes.default.svc`, or `kubernetes.default.svc.cluster.local`.

  This allows us to use one of those hostnames while still connecting to the ip
  address we know is the kubernetes server. This is ok, because we got the
  ca_cert that it'll use directly from the gke api.  Calls to `getaddrinfo` that
  specifically ask for a given hostname can be redirected to the ip address we
  provide for the hostname, as if we had edited /etc/hosts, without editing
  /etc/hosts.

  Arguments:
    hostname: hostname to replace
    ip: ip address to replace the hostname with
  Returns:
    A context manager that patches socket.getaddrinfo for its duration
  """
  return _AddressPatches.Get().MonkeypatchGetaddrinfo(hostname, ip)


@contextlib.contextmanager
def ClusterConnectionInfo(cluster_ref):
  """Get the info we need to use to connect to a GKE cluster.

  Arguments:
    cluster_ref: reference to the cluster to connect to.
  Yields:
    A tuple of (endpoint, ca_certs), where endpoint is the ip address
    of the GKE master, and ca_certs is the absolute path of a temporary file
    (lasting the life of the python process) holding the ca_certs to connect to
    the GKE cluster.
  Raises:
    NoCaCertError: if the cluster is missing certificate authority data.
  """
  adapter = api_adapter.NewAPIAdapter('v1')
  cluster = adapter.GetCluster(cluster_ref)
  auth = cluster.masterAuth
  if auth and auth.clusterCaCertificate:
    ca_data = auth.clusterCaCertificate
  else:
    # This should not happen unless the cluster is in an unusual error
    # state.
    raise NoCaCertError('Cluster is missing certificate authority data.')
  fd, filename = tempfile.mkstemp()
  os.close(fd)
  files.WriteBinaryFileContents(filename, base64.b64decode(ca_data),
                                private=True)
  try:
    yield cluster.endpoint, filename
  finally:
    os.remove(filename)


