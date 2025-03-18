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
"""Utilities for unit kinds commands."""

import re


def AddParentToDependencies(ref, args, request):
  """Request hook to add parent to dependencies if missing.

  Args:
    ref: A resource ref to the parsed resource.
    args: Parsed args namespace containing the flags.
    request: The request message to be modified.

  Returns:
    The modified request message.
  """
  del ref, args  # Unused.
  parent = None
  if hasattr(request, "parent"):
    parent = request.parent
  elif hasattr(request, "name"):
    match = re.match(r"(projects/[^/]+/locations/[^/]+)", request.name)
    if match:
      parent = match.group(1)
  if (
      parent
      and hasattr(request, "unitKind")
      and hasattr(request.unitKind, "dependencies")
  ):
    for dependency in request.unitKind.dependencies:
      if hasattr(dependency, "unitKind"):
        if not dependency.unitKind.startswith("projects/"):
          full_uri = f"{parent}/unitKinds/{dependency.unitKind}"
          dependency.unitKind = full_uri
  return request
