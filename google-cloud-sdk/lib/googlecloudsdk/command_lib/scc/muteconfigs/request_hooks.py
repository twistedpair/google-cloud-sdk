# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Declarative Request Hooks for Cloud SCC's Mute Configs."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.command_lib.scc.hooks import CleanUpUserInput
from googlecloudsdk.command_lib.scc.hooks import InvalidSCCInputError


def CreateMuteConfigReqHook(ref, args, req):
  """Generates a mute config."""
  del ref
  req.parent = _ValidateAndGetParent(args)
  if req.parent is not None:
    req.muteConfigId = _ValidateAndGetMuteConfigId(args)
  else:
    mute_config = _ValidateAndGetMuteConfigFullResourceName(args)
    req.muteConfigId = _GetMuteConfigIdFromFullResourceName(mute_config)
    req.parent = _GetParentFromFullResourceName(mute_config)
  args.filter = ""
  return req


def DeleteMuteConfigReqHook(ref, args, req):
  """Deletes a mute config."""
  del ref
  parent = _ValidateAndGetParent(args)
  if parent is not None:
    mute_config_id = _ValidateAndGetMuteConfigId(args)
    req.name = parent + "/muteConfigs/" + mute_config_id
  else:
    mute_config = _ValidateAndGetMuteConfigFullResourceName(args)
    req.name = mute_config
  return req


def GetMuteConfigReqHook(ref, args, req):
  """Gets a mute config."""
  del ref
  parent = _ValidateAndGetParent(args)
  if parent is not None:
    mute_config_id = _ValidateAndGetMuteConfigId(args)
    req.name = parent + "/muteConfigs/" + mute_config_id
  else:
    mute_config = _ValidateAndGetMuteConfigFullResourceName(args)
    req.name = mute_config
  return req


def ListMuteConfigsReqHook(ref, args, req):
  """Lists mute configs."""
  del ref
  req.parent = _ValidateAndGetParent(args)
  return req


def UpdateMuteConfigReqHook(ref, args, req):
  """Updates a mute config."""
  del ref
  parent = _ValidateAndGetParent(args)
  if parent is not None:
    mute_config_id = _ValidateAndGetMuteConfigId(args)
    req.name = parent + "/muteConfigs/" + mute_config_id
  else:
    mute_config = _ValidateAndGetMuteConfigFullResourceName(args)
    req.name = mute_config
  req.updateMask = CleanUpUserInput(req.updateMask)
  args.filter = ""
  return req


def _ValidateAndGetParent(args):
  """Validates parent."""
  if args.organization is not None:
    if "/" in args.organization:
      pattern = re.compile("^organizations/[0-9]{1,19}$")
      if not pattern.match(args.organization):
        raise InvalidSCCInputError(
            "When providing a full resource path, it must include the pattern "
            "'^organizations/[0-9]{1,19}$'.")
      else:
        return args.organization
    else:
      pattern = re.compile("^[0-9]{1,19}$")
      if not pattern.match(args.organization):
        raise InvalidSCCInputError(
            "Organization does not match the pattern '^[0-9]{1,19}$'.")
      else:
        return "organizations/" + args.organization

  if args.folder is not None:
    if "/" in args.folder:
      pattern = re.compile("^folders/.*$")
      if not pattern.match(args.folder):
        raise InvalidSCCInputError(
            "When providing a full resource path, it must include the pattern "
            "'^folders/.*$'.")
      else:
        return args.folder
    else:
      return "folders/" + args.folder

  if args.project is not None:
    if "/" in args.project:
      pattern = re.compile("^projects/.*$")
      if not pattern.match(args.project):
        raise InvalidSCCInputError(
            "When providing a full resource path, it must include the pattern "
            "'^projects/.*$'.")
      else:
        return args.project
    else:
      return "projects/" + args.project


def _ValidateAndGetMuteConfigId(args):
  """Validate muteConfigId."""
  mute_config_id = args.mute_config
  pattern = re.compile("^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$")
  if not pattern.match(mute_config_id):
    raise InvalidSCCInputError(
        "Mute config id does not match the pattern '^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$'."
    )
  else:
    return mute_config_id


def _ValidateAndGetMuteConfigFullResourceName(args):
  """Validates muteConfig full resource name."""
  mute_config = args.mute_config
  resource_pattern = re.compile(
      "(organizations|projects|folders)/.*/muteConfigs/[a-z]([a-z0-9-]{0,61}[a-z0-9])?$"
  )
  if not resource_pattern.match(mute_config):
    raise InvalidSCCInputError(
        "Mute config must match the full resource name, or `--organization=`, `--folder=` or `--project=` must be provided."
    )
  return mute_config


def _GetMuteConfigIdFromFullResourceName(mute_config):
  """Gets muteConfig id from the full resource name."""
  mute_config_components = mute_config.split("/")
  return mute_config_components[len(mute_config_components) - 1]


def _GetParentFromFullResourceName(mute_config):
  """Gets parent from the full resource name."""
  mute_config_components = mute_config.split("/")
  return mute_config_components[0] + "/" + mute_config_components[1]
