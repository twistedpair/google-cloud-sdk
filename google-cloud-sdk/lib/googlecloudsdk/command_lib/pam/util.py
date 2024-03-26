# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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

"""Utility functions for `gcloud pam` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def SetForceFieldInDeleteEntitlementRequest(unused_ref, unused_args, req):
  """Modify request hook to set the force field in delete entitlement requests to true."""
  req.force = True
  return req


def ParseEntitlementNameIntoCreateEntitlementRequest(unused_ref, args, req):
  """Modify request hook to parse the entitlement name into a CreateEntitlementRequest."""
  entitlement = args.CONCEPTS.entitlement.Parse()
  req.parent = entitlement.result.Parent().RelativeName()
  req.entitlementId = entitlement.result.Name()
  return req


def SetUpdateMaskInUpdateEntitlementRequest(unused_ref, unused_args, req):
  """Modify request hook to set the update mask field in update entitlement requests to '*'."""
  req.updateMask = '*'
  return req
