# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Module containing the KCC Declarative Client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io

from googlecloudsdk.command_lib.util.anthos import binary_operations as bin_ops
from googlecloudsdk.command_lib.util.declarative.clients import client_base
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.credentials import store

_ASSET_INVENTORY_STRING = '{{"name":"{}","asset_type":"{}"}}\n'


class ResourceNotFoundException(client_base.ClientException):
  """General Purpose Exception."""


def _NormalizeUri(resource_uri):
  if 'www.googleapis.com/' in resource_uri:
    api = resource_uri.split('www.googleapis.com/')[1].split('/')[0]
    return resource_uri.replace('www.googleapis.com/{api}'.format(api=api),
                                '{api}.googleapis.com/{api}'.format(api=api))
  return resource_uri


def _NormalizeUris(resource_uris):
  if not isinstance(resource_uris, list):
    raise Exception(
        'Implementation Error: _NormalizeUris requires a list, not str.')
  normalized_uris = []
  for resource_uri in resource_uris:
    normalized_uris.append(_NormalizeUri(resource_uri))
  return normalized_uris


def _GetAssetInventoryInput(resource_uris, resource_type):
  if not isinstance(resource_uris, list):
    raise Exception(
        'Implementation Error: Resource URIs must be a list, not string.')
  asset_inventory_input = ''
  for uri in resource_uris:
    asset_inventory_input += _ASSET_INVENTORY_STRING.format(uri, resource_type)
  return asset_inventory_input


def _ExecuteBinary(cmd, in_str=None):
  output_value = io.StringIO()
  error_value = io.StringIO()
  exit_code = execution_utils.Exec(
      args=cmd,
      no_exit=True,
      in_str=in_str,
      out_func=output_value.write,
      err_func=error_value.write)
  return exit_code, output_value.getvalue(), error_value.getvalue()


def _ExecuteBinaryWithStreaming(cmd, in_str=None):
  exit_code = execution_utils.ExecWithStreamingOutput(args=cmd, in_str=in_str)
  if exit_code != 0:
    raise client_base.ClientException(
        'The bulk-export command could not finish correctly.')


class KccClient(client_base.DeclarativeClient):
  """KRM Yaml Export based Declarative Client."""

  CC_PROMPT = (
      'This command requires the `config-connector` binary to be installed '
      'to export GCP resource configurations. Would you like to install the'
      '`config-connector` binary to continue command execution?')

  def __init__(self, gcp_account=None, impersonated=False):
    if not gcp_account:
      gcp_account = properties.VALUES.core.account.Get()
    try:
      self._export_service = bin_ops.CheckForInstalledBinary('config-connector')
    except bin_ops.MissingExecutableException:
      self._export_service = bin_ops.InstallBinaryNoOverrides(
          'config-connector', prompt=self.CC_PROMPT)
    self._use_account_impersonation = impersonated
    self._account = gcp_account

  def _GetToken(self):
    try:
      cred = store.LoadFreshCredential(
          self._account,
          allow_account_impersonation=self._use_account_impersonation)
      return cred.access_token
    except Exception as e:  # pylint: disable=broad-except
      raise client_base.ClientException(
          'Error Configuring KCC Client: [{}]'.format(e))

  def _OutputToFileOrDir(self, args):
    if args.path.strip() == '-':
      return False
    return True

  def _GetBinaryCommand(self, args, command_name, resource_uri=None):
    # Populate universal flags to command.
    cmd = [
        self._export_service, '--oauth2-token',
        self._GetToken(), command_name
    ]

    # If command is single resource export, add single resource flags to cmd.
    if command_name == 'export':
      if not resource_uri:
        raise ValueError(
            '`_GetBinaryCommand` requires a resource uri for export commands.')
      cmd.extend([resource_uri])

    # Populate flags for bulk-export command.
    if command_name == 'bulk-export':
      cmd.extend(['--on-error', getattr(args, 'on_error', 'ignore')])

      # If bulk export call is not being used for single resource --all, add
      # scope flag to command.
      if not getattr(args, 'all', None):
        if args.IsSpecified('organization'):
          cmd.extend(['--organization', args.organization])
        elif args.IsSpecified('folder'):
          cmd.extend(['--folder', args.folder])
        else:
          project = args.project or properties.VALUES.core.project.GetOrFail()
          cmd.extend(['--project', project])

    if getattr(args, 'resource_format', None):
      cmd.extend(['--resource-format', args.resource_format])

      # Terraform does not support iam currently.
      if args.resource_format == 'terraform':
        cmd.extend(['--iam-format', 'none'])

    # If a file or directory path is specified, add path to command.
    if self._OutputToFileOrDir(args):
      cmd.extend(['--output', args.path])

    return cmd

  def Export(self, args, resource_uri):
    normalized_resource_uri = _NormalizeUri(resource_uri)
    with progress_tracker.ProgressTracker(
        message='Exporting resources', aborted_message='Aborted Export.'):
      cmd = self._GetBinaryCommand(
          args=args,
          command_name='export',
          resource_uri=normalized_resource_uri)
      exit_code, output_value, error_value = _ExecuteBinary(cmd)

    if exit_code != 0:
      if 'resource not found' in error_value:
        raise client_base.ResourceNotFoundException(
            'Could not fetch resource: \n - The resource [{}] does not exist.'
            .format(normalized_resource_uri))
      else:
        raise client_base.ClientException(
            'Error executing export:: [{}]'.format(error_value))
    if not self._OutputToFileOrDir(args):
      log.out.Print(output_value)
    log.status.Print('Exported successfully.')
    return exit_code

  def ExportAll(self, args, resource_uris, resource_type):
    normalized_resource_uris = _NormalizeUris(resource_uris)
    cmd = self._GetBinaryCommand(args, 'bulk-export')

    asset_inventory_input = _GetAssetInventoryInput(
        resource_uris=normalized_resource_uris, resource_type=resource_type)

    if self._OutputToFileOrDir(args):
      with progress_tracker.ProgressTracker(
          message='Exporting resources', aborted_message='Aborted Export.'):
        exit_code, _, error_value = _ExecuteBinary(
            cmd=cmd, in_str=asset_inventory_input)
        if exit_code != 0:
          raise client_base.ClientException(
              'Error executing export:: [{}]'.format(error_value))
      return exit_code
    else:
      return _ExecuteBinaryWithStreaming(cmd=cmd, in_str=asset_inventory_input)

  def BulkExport(self, args):
    cmd = self._GetBinaryCommand(args, 'bulk-export')

    if self._OutputToFileOrDir(args):
      with progress_tracker.ProgressTracker(
          message='Exporting resources', aborted_message='Aborted Export.'):
        exit_code, _, error_value = _ExecuteBinary(cmd)

        if exit_code != 0:
          raise client_base.ClientException(
              'Error executing export:: [{}]'.format(error_value))

      return exit_code
    else:
      return _ExecuteBinaryWithStreaming(cmd)
