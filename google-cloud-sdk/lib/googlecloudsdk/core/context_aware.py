# -*- coding: utf-8 -*- #
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Helper module for context aware access."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import atexit
import json
import os

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files

DEFAULT_AUTO_DISCOVERY_FILE_PATH = os.path.join(
    files.GetHomeDir(), ".secureConnect", "context_aware_metadata.json")


def _AutoDiscoveryFilePath():
  """Return the file path of the context aware configuration file."""
  # auto_discovery_file_path is an override used for testing purposes.
  cfg_file = properties.VALUES.context_aware.auto_discovery_file_path.Get()
  if cfg_file is not None:
    return cfg_file
  return DEFAULT_AUTO_DISCOVERY_FILE_PATH


class ConfigException(exceptions.Error):
  pass


class CertProviderUnexpectedExit(exceptions.Error):
  pass


class CertProvisionException(exceptions.Error):
  pass


class Config(object):
  """Represents the configurations associated with context aware access.

  Only one instance of Config can be created for the program.
  """

  def __init__(self):
    self.use_client_certificate = (
        properties.VALUES.context_aware.use_client_certificate.GetBool())
    self._cert_and_key_path = None
    self.client_cert_path = None
    atexit.register(self.Cleanup)
    if self.use_client_certificate:
      # Search for configuration produced by endpoint verification
      cfg_file = _AutoDiscoveryFilePath()
      # Autodiscover context aware settings from configuration file created by
      # end point verification agent
      try:
        contents = files.ReadFileContents(cfg_file)
        log.debug("context aware settings detected at %s", cfg_file)
        json_out = json.loads(contents)
        if "cert_provider_command" in json_out:
          # Execute the cert provider to provision client certificates for
          # context aware access
          cmd = json_out["cert_provider_command"]
          # Remember the certificate path when auto provisioning
          # to cleanup after use
          self._cert_and_key_path = os.path.join(
              config.Paths().global_config_dir, "caa_cert.pem")
          # Certs provisioned using endpoint verification are stored as a
          # single file holding both the public certificate
          # and the private key
          self._ProvisionClientCert(cmd, self._cert_and_key_path)
          self.client_cert_path = self._cert_and_key_path
        else:
          raise CertProvisionException("no cert provider detected")
      except files.Error as e:
        log.debug("context aware settings discovery file %s - %s", cfg_file, e)
      except CertProvisionException as e:
        log.error("failed to provision client certificate - %s", e)
      if self.client_cert_path is None:
        raise ConfigException("Use of client certificate requires endpoint "
                              "verification agent")

  def Cleanup(self):
    """Cleanup any files or resource provisioned during config init."""
    self._UnprovisionClientCert()

  def _ProvisionClientCert(self, cmd, cert_path):
    """Executes certificate provider to obtain client certificate and keys."""
    try:
      with files.FileWriter(cert_path) as f:
        ret_val = execution_utils.Exec(
            cmd, no_exit=True, out_func=f.write,
            err_func=log.file_only_logger.debug)
        if ret_val:
          raise CertProviderUnexpectedExit(
              "certificate provider exited with error")
    except (files.Error,
            execution_utils.PermissionError,
            execution_utils.InvalidCommandError,
            CertProviderUnexpectedExit) as e:
      raise CertProvisionException(e)

  def _UnprovisionClientCert(self):
    if self._cert_and_key_path is not None:
      try:
        os.remove(self._cert_and_key_path)
        log.debug("unprovisioned client cert - %s", self._cert_and_key_path)
      except (files.Error) as e:
        log.error("failed to remove client certificate - %s", e)
