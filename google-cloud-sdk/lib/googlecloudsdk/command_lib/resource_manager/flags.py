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
"""Flags for commands that deal with the CRM API."""

from googlecloudsdk.api_lib.resource_manager import folders
from googlecloudsdk.api_lib.resource_manager import liens
from googlecloudsdk.api_lib.resource_manager import operations
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions

ORGS_COLLECTION = 'cloudresourcemanager.organizations'


def FolderIdArg(use_description):
  return base.Argument(
      'id',
      metavar='FOLDER_ID',
      completion_resource=folders.FOLDERS_COLLECTION,
      list_command_path='resource-manager folders',
      help='ID for the folder {0}'.format(use_description))


@base.Hidden
def FolderIdFlag(use_description):
  return base.Argument(
      '--folder',
      metavar='FOLDER_ID',
      completion_resource=folders.FOLDERS_COLLECTION,
      default=None,
      list_command_path='resource-manager folders',
      help='ID for the folder {0}'.format(use_description))


def OrganizationIdFlag(use_description):
  return base.Argument(
      '--organization',
      metavar='ORGANIZATION_ID',
      completion_resource=ORGS_COLLECTION,
      list_command_path='organizations',
      help='ID for the organization {0}'.format(use_description))


def OperationIdArg(use_description):
  return base.Argument(
      'id',
      metavar='OPERATION_ID',
      completion_resource=operations.OPERATIONS_COLLECTION,
      help='ID for the operation {0}'.format(use_description))


def OperationAsyncFlag():
  return base.Argument(
      '--async',
      action='store_true',
      help=(
          'Whether to return an asynchronous long-running operation immediately'
          ' instead of waiting for the operation to finish'))


def LienIdArg(use_description):
  return base.Argument(
      'id',
      metavar='LIEN_ID',
      completion_resource=liens.LIENS_COLLECTION,
      help='ID for the lien {0}'.format(use_description))


def AddParentFlagsToParser(parser):
  FolderIdFlag('to use as a parent').AddToParser(parser)
  OrganizationIdFlag('to use as a parent').AddToParser(parser)


def GetParentFromFlags(args):
  if args.folder:
    return 'folders/{0}'.format(args.folder)
  elif args.organization:
    return 'organizations/{0}'.format(args.organization)
  else:
    return None


def CheckParentFlags(args, parent_required=True):
  if args.folder and args.organization:
    raise exceptions.ConflictingArgumentsException('--folder', '--organization')
  if parent_required and not args.folder and not args.organization:
    raise exceptions.ToolException(
        'Neither --folder nor --organization provided, exactly one required')
