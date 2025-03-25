# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Common argument processors for migration vms surface arguments."""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import properties


# Helper Functions
def GetMessageClass(msg_type_name):
  """Gets API message object for given message type name."""
  msg = apis.GetMessagesModule('vmmigration', 'v1')
  return getattr(msg, msg_type_name)


# Argument Processors
def GetEncryptionTransform(value):
  """Returns empty Encryption entry."""
  del value
  return GetMessageClass('Encryption')()


def SetLocationAsGlobal():
  """Set default location to global."""
  return 'global'


def FixTargetDetailsCommonFields(ref, args, target_details):
  """"Fixes the target details common fields."""

  if not args.target_project:
    # Handle default target project being the host project.
    target = args.project or properties.VALUES.core.project.Get(required=True)
    target_details.targetProject = (
        ref.Parent().Parent().RelativeName() +
        '/locations/global/targetProjects/' + target
    )
  elif '/' not in args.target_project:
    # Handle prepending path to target project short-name.
    target_details.targetProject = (
        ref.Parent().Parent().RelativeName() +
        '/locations/global/targetProjects/' + args.target_project
    )
