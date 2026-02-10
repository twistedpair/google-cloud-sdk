# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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
"""Utilities for BigLake Delta Sharing commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def SetParentAndCatalogId(ref, args, request):
  """Hook to fix the parent and catalog ID parameters in Create request."""
  del args  # Unused
  if ref:
    request.deltaSharingCatalogId = ref.Name()
    request.parent = ref.Parent().RelativeName()
  return request


SetParent = SetParentAndCatalogId


def SetParentForList(ref, args, request):
  """Hook to fix the parent parameter in List request."""
  del args  # Unused
  if ref:
    request.parent = ref.RelativeName()
  return request
