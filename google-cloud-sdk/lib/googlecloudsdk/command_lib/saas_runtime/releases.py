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
"""Utilities for releases commands."""

import re


def AddParentToUpgradeableFromReleases(ref, args, request):
  """Request hook to add parent to upgradeable from releases if missing.

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
      and hasattr(request, "release")
      and hasattr(
          request.release.releaseRequirements, "upgradeableFromReleases"
      )
  ):
    updated_upgradeable_from_releases = []
    for (
        upgradeable_from_release
    ) in request.release.releaseRequirements.upgradeableFromReleases:
      if not upgradeable_from_release.startswith("projects/"):
        full_uri = f"{parent}/releases/{upgradeable_from_release}"
      else:
        full_uri = upgradeable_from_release
      updated_upgradeable_from_releases.append(full_uri)
    request.release.releaseRequirements.upgradeableFromReleases = (
        updated_upgradeable_from_releases
    )
  return request
