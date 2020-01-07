# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Declarative hooks for reCAPTCHA Enterprise Keys CLI."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.projects import util as projects_command_util

import six

def SwapProjectName(parent_string):
  components = parent_string.split('/')
  if len(components) < 2:
    return parent_string
  components[1] = six.text_type(projects_command_util.GetProjectNumber(components[1]))
  return '/'.join(components)


def SetParent(unused_ref, unused_args, request):
  if hasattr(request, 'parent'):
    request.parent = SwapProjectName(request.parent)
  elif hasattr(request,'name'):
    request.name = SwapProjectName(request.name)
  return request
