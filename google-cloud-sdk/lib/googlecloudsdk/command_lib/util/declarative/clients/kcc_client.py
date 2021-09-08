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

import collections
import io
import os
import re

from apitools.base.py import encoding
from googlecloudsdk.api_lib.asset import client_util
from googlecloudsdk.api_lib.services import enable_api
from googlecloudsdk.command_lib.asset import utils as asset_utils
from googlecloudsdk.command_lib.util.anthos import binary_operations as bin_ops
from googlecloudsdk.command_lib.util.declarative.clients import client_base
from googlecloudsdk.command_lib.util.resource_map.declarative import resource_name_translator
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import yaml
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.credentials import store
from googlecloudsdk.core.resource import resource_filter
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import times

_ASSET_INVENTORY_STRING = '{{"name":"{}","asset_type":"{}"}}\n'
_ASSET_TYPE_REGEX = re.compile(r'\"asset_type\"\: (\".*?)\,')
_KRM_GROUP_SUFFIX = '.cnrm.cloud.google.com'

ApiClientArgs = collections.namedtuple('ApiClientArgs', [
    'snapshot_time', 'limit', 'page_size', 'asset_types', 'parent',
    'content_type', 'filter_func', 'relationship_types'
])

RESOURCE_LIST_FORMAT = (
    'table[box](GVK.Kind:label="KRM KIND", SupportsBulkExport.yesno("x", '
    '""):label="BULK EXPORT?", SupportsExport.yesno("x", ""):label="EXPORT?")')


class KrmGroupValueKind(object):
  """Value class for KRM Group Value Kind Data."""

  def __init__(self,
               kind,
               group,
               bulk_export_supported,
               export_supported,
               version=None,
               resource_name_format=None):
    self.kind = kind
    self.group = group
    self.version = version
    self.bulk_export_supported = bulk_export_supported
    self.export_supported = export_supported
    self.resource_name_format = resource_name_format

  def AsDict(self):
    """Convert to Config Connector compatible dict format."""
    gvk = collections.OrderedDict()
    output = collections.OrderedDict()
    gvk['Group'] = self.group
    gvk['Kind'] = self.kind
    gvk['Version'] = self.version or ''
    output['GVK'] = gvk
    output['ResourceNameFormat'] = self.resource_name_format or ''
    output['SupportsBulkExport'] = self.bulk_export_supported
    output['SupportsExport'] = self.export_supported
    return output

  def __str__(self):
    return yaml.dump(self.AsDict(), round_trip=True)

  def __repr__(self):
    return self.__str__()

  def __eq__(self, o):
    if not isinstance(o, KrmGroupValueKind):
      return False
    return (self.kind == o.kind and
            self.group == o.group and
            self.version == o.version and
            self.bulk_export_supported == o.bulk_export_supported and
            self.export_supported == o.export_supported and
            self.resource_name_format == o.resource_name_format)

  def __hash__(self):
    return sum(
        map(hash, [
            self.kind, self.group, self.version,
            self.bulk_export_supported, self.export_supported,
            self.resource_name_format
        ]))


class ResourceNotFoundException(client_base.ClientException):
  """General Purpose Exception."""


class AssetInventoryNotEnabledException(client_base.ClientException):
  """Exception for when Asset Inventory Is Not Enabled."""


# TODO(b/181223251): Remove this workaround once config-connector is updated.
def _NormalizeResourceFormat(resource_format):
  """Translate Resource Format from gcloud values to config-connector values."""
  if resource_format == 'terraform':
    return 'hcl'
  return resource_format


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


def _GetTempAssetInventoryFilePath():
  """Create a temporary file path for AssetInventory export/list results."""
  date_string = times.FormatDateTime(times.Now(), fmt='%Y%m%dT%H%M%S%3f')
  return os.path.join(files.GetCWD(),
                      'gcloud_assetexport_temp_{}.json'.format(date_string))


def _BuildAssetTypeFilterFromKind(kind_list):
  """Get assetType Filter from KRM Kind list."""
  if not kind_list:
    return None
  name_translator = resource_name_translator.ResourceNameTranslator()
  kind_filters = []
  for kind in kind_list:
    krm_kind = kind
    if '/' in kind:
      _, krm_kind = kind.split('/')

    matching_kind_objects = name_translator.find_krmkinds_by_kind(krm_kind)
    try:
      for kind_obj in matching_kind_objects:  # Add all matching KrmKinds
        meta_resource = name_translator.get_resource(krm_kind=kind_obj)
        kind_filters.append(meta_resource.asset_inventory_type)
    except resource_name_translator.ResourceIdentifierNotFoundError:
      continue  # no KRM mapping for this Asset Inventory Type

  return kind_filters


def _GetAssetInventoryListInput(folder,
                                project,
                                org,
                                file_path=None,
                                asset_types_filter=None,
                                filter_expression=None,
                                krm_kind_filter=None):
  """Generate a AssetInventory export data set from api list call.


  Calls AssetInventory List API via shared api client (AssetListClient) and
  generates a list of exportable assets. If `asset_types_filter`,
  `gvk_kind_filter` or `filter_expression` is passed, it will filter out
  non-matching resources. If `file_path` is None list will be returned as a
  string otherwise it is written to disk at specified path.

  Args:
    folder: string, folder parent for resource export.
    project: string, project parent for resource export.
    org: string, organization parent for resource export.
    file_path: string, path to write AssetInventory export file to. If None,
      results are returned as string.
    asset_types_filter: [string], list of asset types to include in the output
      file.
    filter_expression: string, a valid gcloud filter expression.
      See `gcloud topic filter` for more details.
    krm_kind_filter: [string], list of KrmKinds corresponding to asset
    types to include in the output.

  Returns:
    string: file path where AssetInventory data has been written or raw data if
      `temp_file_path` is None. Returns None if no results returned from API.

  Raises:
    RequiredArgumentException: If none of folder, project or org is provided.
    ResourceNotFoundException: If no resources are found or returned from
      filtering.
    ClientException: Writing file to disk.
  """
  root_asset = asset_utils.GetParentNameForExport(organization=org,
                                                  project=project,
                                                  folder=folder)
  asset_client = client_util.AssetListClient(root_asset)
  filter_func = (resource_filter.Compile(filter_expression.strip()).Evaluate
                 if filter_expression else None)
  asset_filter = asset_types_filter or []
  if krm_kind_filter:
    kind_filters = _BuildAssetTypeFilterFromKind(krm_kind_filter)
    if not kind_filters:
      raise ResourceNotFoundException(
          'No matching resource types found for {}'.format(krm_kind_filter))
    asset_filter.extend(kind_filters)

  args = ApiClientArgs(
      snapshot_time=None,
      limit=None,
      page_size=None,
      content_type=None,
      asset_types=sorted(asset_filter),
      parent=root_asset,
      filter_func=filter_func,
      relationship_types=[])
  asset_results = asset_client.List(args, do_filter=True)
  asset_string_array = []
  for item in asset_results:  # list of apitools Asset messages.
    item_str = encoding.MessageToJson(item)
    item_str = item_str.replace('"assetType"', '"asset_type"')
    asset_string_array.append(item_str)

  if not asset_string_array:
    if asset_types_filter:
      asset_msg = '\n With resource types in [{}].'.format(asset_types_filter)
    else:
      asset_msg = ''
    if filter_expression:
      filter_msg = '\n Matching provided filter [{}].'.format(filter_expression)
    else:
      filter_msg = ''
    raise ResourceNotFoundException(
        'No matching resources found for [{parent}] {assets} {filter}'.format(
            parent=root_asset, assets=asset_msg, filter=filter_msg))
  if not file_path:
    return '\n'.join(asset_string_array)
  else:
    try:
      files.WriteFileAtomically(file_path, '\n'.join(asset_string_array))
    except (ValueError, TypeError) as e:
      raise client_base.ClientException(e)
    return file_path


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
  exit_code = execution_utils.ExecWithStreamingOutput(args=cmd,
                                                      no_exit=True,
                                                      in_str=in_str)
  if exit_code != 0:
    raise client_base.ClientException(
        'The bulk-export command could not finish correctly.')
  log.status.Print('\nExport complete.')
  return exit_code


def _BulkExportPostStatus(preexisting_file_count, path):
  if not preexisting_file_count:
    file_count = sum(
        [len(files_in_dir) for r, d, files_in_dir in os.walk(path)])
    log.status.write('Exported {} resource configuration(s) to [{}].\n'.format(
        file_count, path))
  else:
    log.status.write(
        'Exported resource configuration(s) to [{}].\n'.format(path))


def _TranslateCollectionToAssetType(collection):
  return resource_name_translator.ResourceNameTranslator().get_resource(
      collection_name=collection).asset_inventory_type


def CheckForAssetInventoryEnablementWithPrompt(project=None):
  """Checks if the cloudasset API is enabled, prompts to enable if not."""
  project = project or properties.VALUES.core.project.GetOrFail()
  service_name = 'cloudasset.googleapis.com'
  if not enable_api.IsServiceEnabled(project, service_name):
    if console_io.PromptContinue(
        default=False,
        prompt_string=(
            'API [{}] is required to continue, but is not enabled on project [{}]. '
            'Would you like to enable and retry (this will take a '
            'few minutes)?').format(service_name, project)):
      enable_api.EnableService(project, service_name)
    else:
      raise AssetInventoryNotEnabledException(
          'Aborted by user: API [{}] must be enabled on project [{}] to continue.'
          .format(service_name, project))


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
      return store.GetFreshAccessToken(
          account=self._account,
          allow_account_impersonation=self._use_account_impersonation)
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

      # # If bulk export call is not being used for single resource --all, add
      # # scope flag to command.
      if not getattr(args, 'all', None):
        if args.IsSpecified('organization'):
          cmd.extend(['--organization', args.organization])
        elif args.IsSpecified('folder'):
          cmd.extend(['--folder', args.folder])
        else:
          project = args.project or properties.VALUES.core.project.GetOrFail()
          cmd.extend(['--project', project])

    if getattr(args, 'storage_path', None):
      cmd.extend(['--storage-key', args.storage_path])

    if getattr(args, 'resource_format', None):
      cmd.extend(['--resource-format',
                  _NormalizeResourceFormat(args.resource_format)])

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

  def ExportAll(self, args, collection):
    cmd = self._GetBinaryCommand(args, 'bulk-export')
    asset_type = [_TranslateCollectionToAssetType(collection)]
    asset_list_input = _GetAssetInventoryListInput(
        folder=getattr(args, 'folder', None),
        project=(getattr(args, 'project', None) or
                 properties.VALUES.core.project.GetOrFail()),
        org=getattr(args, 'organization', None),
        asset_types_filter=asset_type,
        filter_expression=getattr(args, 'filter', None))
    cmd = self._GetBinaryCommand(args, 'bulk-export')
    return self._CallBulkExport(cmd, args, asset_list_input)

  def _CallBulkExport(self, cmd, args, asset_list_input=None):
    """Execute actual bulk-export command on config-connector binary."""
    if self._OutputToFileOrDir(args):
      try:
        if not files.HasWriteAccessInDir(args.path):
          raise client_base.ClientException(
              'Can not export to path [{}]. Ensure that path exists and '
              'is writeable.'.format(args.path)
              )
      except ValueError:
        raise client_base.ClientException(
            'Can not export to path [{}]. Path not found.'.format(args.path))

      preexisting_file_count = sum(
          [len(files_in_dir) for r, d, files_in_dir in os.walk(args.path)])
      with progress_tracker.ProgressTracker(
          message='Exporting resource configurations to [{}]'.format(args.path),
          aborted_message='Aborted Export.'):
        exit_code, _, error_value = _ExecuteBinary(
            cmd=cmd, in_str=asset_list_input)

      if exit_code != 0:
        raise client_base.ClientException(
            'Error executing export:: [{}]'.format(error_value))
      else:
        _BulkExportPostStatus(preexisting_file_count, args.path)

      return exit_code

    else:
      log.status.write('Exporting resource configurations to stdout...\n')
      return _ExecuteBinaryWithStreaming(cmd=cmd, in_str=asset_list_input)

  def BulkExport(self, args):
    CheckForAssetInventoryEnablementWithPrompt(
        getattr(args, 'project', None))
    cmd = self._GetBinaryCommand(args, 'bulk-export')
    return self._CallBulkExport(cmd, args, asset_list_input=None)

  def _ParseKindTypesFileData(self, file_data):
    """Parse Resource Types data into input string Array."""
    if not file_data:
      return None
    return [x for x in re.split(r'\s+|,+', file_data) if x]

  def BulkExportFromAssetList(self, args):
    """BulkExport with support for resource kind/asset type and filtering."""
    CheckForAssetInventoryEnablementWithPrompt(
        getattr(args, 'project', None))
    args.all = True  # Remove scope (e.g. project, org & folder) from cmd.
    kind_args = (
        getattr(args, 'resource_types', None) or self._ParseKindTypesFileData(
            getattr(args, 'resource_types_file', None)))

    asset_list_input = _GetAssetInventoryListInput(
        folder=getattr(args, 'folder', None),
        project=getattr(args, 'project', None),
        org=getattr(args, 'organization', None),
        krm_kind_filter=kind_args,
        filter_expression=getattr(args, 'filter', None))
    cmd = self._GetBinaryCommand(args, 'bulk-export')
    return self._CallBulkExport(cmd, args, asset_list_input=asset_list_input)

  def _CallPrintResources(self, output_format='table'):
    cmd = [
        self._export_service, 'print-resources', '--output-format',
        output_format
    ]
    exit_code, output_value, error_value = _ExecuteBinary(cmd)
    if exit_code != 0:
      raise client_base.ClientException(
          'Error occured while listing available resources: [{}]'.format(
              error_value))
    return output_value

  def ListResources(self,
                    project=None,
                    organization=None,
                    folder=None):
    """List all exportable resources.

    If parent (e.g. project, organization or folder) is passed then only list
    the exportable resources for that parent.

    Args:
      project: string, project to list exportable resources for.
      organization: string, organization to list exportable resources for.
      folder: string, folder to list exportable resources for.

    Returns:
      supported resources formatted output listing exportable resources.

    """
    if not (project or organization or folder):
      yaml_obj_list = yaml.load(
          self._CallPrintResources(output_format='yaml'), round_trip=True)
      return yaml_obj_list
    if project:
      msg_sfx = ' for project [{}]'.format(project)
    elif organization:
      msg_sfx = ' for organization [{}]'.format(organization)
    else:
      msg_sfx = ' for folder [{}]'.format(folder)

    with progress_tracker.ProgressTracker(
        message='Listing exportable resource types'+ msg_sfx,
        aborted_message='Aborted Export.'):
      supported_kinds = self.ListSupportedResourcesForParent(
          project=project, organization=organization, folder=folder)
      supported_kinds = [x.AsDict() for x in supported_kinds]
      return supported_kinds

  def ListSupportedResourcesForParent(self,
                                      project=None,
                                      organization=None,
                                      folder=None):
    """List all exportable resource types for a given project, org or folder."""
    if not (project or organization or folder):
      raise client_base.ClientException(
          'At least one of project, organization or folder must '
          'be specified for this operation')
    name_translator = resource_name_translator.ResourceNameTranslator()
    asset_list_data = _GetAssetInventoryListInput(
        folder=folder, org=organization, project=project)
    # Extract unique asset types from list data string
    asset_types = set([
        x.replace('\"', '')
        for x in _ASSET_TYPE_REGEX.findall(asset_list_data)
    ])
    exportable_kinds = []
    for asset in asset_types:
      try:
        meta_resource = name_translator.get_resource(
            asset_inventory_type=asset)
        gvk = KrmGroupValueKind(
            kind=meta_resource.krm_kind.krm_kind,
            group=meta_resource.krm_kind.krm_group+_KRM_GROUP_SUFFIX,
            bulk_export_supported=meta_resource.resource_data
            .support_bulk_export,
            export_supported=meta_resource.resource_data.support_single_export)
        exportable_kinds.append(gvk)
      except resource_name_translator.ResourceIdentifierNotFoundError:
        continue  # no KRM mapping for this Asset Inventory Type
    return sorted(exportable_kinds, key=lambda x: x.kind)
