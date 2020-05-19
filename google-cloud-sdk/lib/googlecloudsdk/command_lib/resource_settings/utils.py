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
"""Resource Settings command utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

SETTINGS_PREFIX = 'settings/'


def GetSettingFromArgs(args):
  """Returns the setting from the user-specified arguments.

  A setting has the following syntax: settings/{setting_name}.

  This handles both cases in which the user specifies and does not specify the
  constraint prefix.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
  """
  if args.setting_name.startswith(SETTINGS_PREFIX):
    return args.setting_name

  return SETTINGS_PREFIX + args.setting_name


def GetSettingNameFromArgs(args):
  """Returns the setting name from the user-specified arguments.

  This handles both cases in which the user specifies and does not specify the
  setting prefix.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
  """
  if args.setting_name.startswith(SETTINGS_PREFIX):
    return args.setting_name[len(SETTINGS_PREFIX):]

  return args.setting_name


def GetParentResourceFromArgs(args):
  """Returns the resource from the user-specified arguments.

  A resource has the following syntax:
  [organizations|folders|projects]/{resource_id}.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
  """
  resource_id = args.organization or args.folder or args.project

  if args.organization:
    resource_type = 'organizations'
  elif args.folder:
    resource_type = 'folders'
  else:
    resource_type = 'projects'

  return '{}/{}'.format(resource_type, resource_id)


def GetSettingsPathFromArgs(args):
  """Returns the settings path from the user-specified arguments.

  A settings path has the following syntax:
  [organizations|folders|projects]/{resource_id}/settings/{setting_name}.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
  """
  resource = GetParentResourceFromArgs(args)
  setting_name = GetSettingNameFromArgs(args)

  return '{}/settings/{}'.format(resource, setting_name)
