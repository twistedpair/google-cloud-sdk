# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Create ECP configurations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum
import json
import os

from googlecloudsdk.core import config
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files

RESOURCE_TYPE = 'enterprise-certificate-proxy configuration file'


def get_platform_folder():
  sdk_root = config.Paths().sdk_root
  if not sdk_root:
    raise ECPConfigError(
        'Unable to find the SDK root path. The gcloud installation may be'
        ' corrupted.'
    )

  return os.path.join(sdk_root, 'platform', 'enterprise_cert')


def get_bin_folder():
  sdk_bin_path = config.Paths().sdk_bin_path
  if not sdk_bin_path:
    raise ECPConfigError(
        'Unable to find the SDK bin path. The gcloud installation may be'
        ' corrupted.'
    )

  return sdk_bin_path


class ConfigType(enum.Enum):
  PKCS11 = 1
  KEYCHAIN = 2
  MYSTORE = 3


class WindowsBinaryPathConfig(object):

  def __init__(self, ecp, ecp_client, tls_offload):
    self.ecp = ecp if ecp else os.path.join(get_bin_folder(), 'ecp.exe')
    self.ecp_client = (
        ecp_client
        if ecp_client
        else os.path.join(get_platform_folder(), 'libecp.dll')
    )
    self.tls_offload = (
        tls_offload
        if tls_offload
        else os.path.join(get_platform_folder(), 'libtls_offload.dll')
    )


class LinuxPathConfig(object):

  def __init__(self, ecp, ecp_client, tls_offload):
    self.ecp = ecp if ecp else os.path.join(get_bin_folder(), 'ecp')
    self.ecp_client = (
        ecp_client
        if ecp_client
        else os.path.join(get_platform_folder(), 'libecp.so')
    )
    self.tls_offload = (
        tls_offload
        if tls_offload
        else os.path.join(get_platform_folder(), 'libtls_offload.so')
    )


class MacOSBinaryPathConfig(object):

  def __init__(self, ecp, ecp_client, tls_offload):
    self.ecp = ecp if ecp else os.path.join(get_bin_folder(), 'ecp')
    self.ecp_client = (
        ecp_client
        if ecp_client
        else os.path.join(get_platform_folder(), 'libecp.dylib')
    )
    self.tls_offload = (
        tls_offload
        if tls_offload
        else os.path.join(get_platform_folder(), 'libtls_offload.dylib')
    )


class PKCS11Config(object):

  def __init__(self, module, slot, label, user_pin):
    self.module = module
    self.slot = slot
    self.label = label

    if user_pin:
      self.user_pin = user_pin


class KeyChainConfig(object):

  def __init__(self, cert_issuer):
    self.cert_issuer = cert_issuer


class MyStoreConfig(object):

  def __init__(self, cert_issuer, store, provider):
    self.cert_issuer = cert_issuer
    self.store = store
    self.provider = provider


def create_ecp_config(args, config_type):
  """Create an ECP config based on user arguments and the desired store type."""

  if config_type == ConfigType.PKCS11:
    key, ecp_config = 'pkcs11', PKCS11Config(
        args.module,
        args.slot,
        args.label,
        args.user_pin,
    )
    lib_config = LinuxPathConfig(args.ecp, args.ecp_client, args.tls_offload)
  elif config_type == ConfigType.KEYCHAIN:
    key, ecp_config = 'macos_keychain', KeyChainConfig(args.issuer)
    lib_config = MacOSBinaryPathConfig(
        args.ecp, args.ecp_client, args.tls_offload
    )
  elif config_type == ConfigType.MYSTORE:
    key, ecp_config = 'windows_store', MyStoreConfig(
        args.issuer, args.store, args.provider
    )
    lib_config = WindowsBinaryPathConfig(
        args.ecp, args.ecp_client, args.tls_offload
    )
  else:
    raise ECPConfigError(
        (
            'Unknown config_type {} passed to create enterprise certificate'
            ' configuration. Valid options are: [PKCS11, KEYCHAIN, MYSTORE]'
        ).format(config_type)
    )
  return {'cert_configs': {key: vars(ecp_config)}, 'libs': vars(lib_config)}


def create_config(args, config_type):
  """Creates the ECP config based on the passed in CLI arguments."""
  config.EnsureSDKWriteAccess()
  output = create_ecp_config(args, config_type)

  config_path = (
      args.output_file
      if args.output_file
      else config.CertConfigDefaultFilePath()
  )

  files.WriteFileContents(config_path, json.dumps(output, indent=2))
  log.CreatedResource(config_path, RESOURCE_TYPE)


class ECPConfigError(Exception):

  def __init__(self, message):
    super(ECPConfigError, self).__init__()
    self.message = message
