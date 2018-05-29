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
"""General utilties for Cloud Source commands."""

from __future__ import absolute_import
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

_API_NAME = 'sourcerepo'
_API_VERSION = 'v1'

_MESSAGES = apis.GetMessagesModule(_API_NAME, _API_VERSION)


def ParseProjectConfig(args, pubsub_configs=None):
  """Parse and create ProjectConfig message."""
  project_ref = resources.REGISTRY.Create(
      'sourcerepo.projects',
      projectsId=args.project or properties.VALUES.core.project.GetOrFail())
  project_name = project_ref.RelativeName()

  enable_pushblock = args.enable_pushblock
  return _MESSAGES.ProjectConfig(
      enablePrivateKeyCheck=enable_pushblock,
      name=project_name,
      pubsubConfigs=pubsub_configs)
