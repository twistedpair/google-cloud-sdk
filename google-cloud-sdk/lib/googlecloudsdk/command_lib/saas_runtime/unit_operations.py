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
"""Utilities for unit operations commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def HandleEmptyProvision(unused_ref, args, request):
  """Request hook to handle use of --provision flag.

  Args:
    unused_ref: A resource ref to the parsed resource.
    args: Parsed args namespace containing the flags.
    request: The request message to be modified.

  Returns:
    The modified request message.
  """
  if not args.IsSpecified('provision'):
    return request
  if args.IsSpecified('provision_release') or args.IsSpecified(
      'provision_input_variables'
  ):
    return request
  request.unitOperation.provision = {}
  return request


def HandleEmptyUpgrade(unused_ref, args, request):
  """Request hook to handle use of --upgrade flag.

  Args:
    unused_ref: A resource ref to the parsed resource.
    args: Parsed args namespace containing the flags.
    request: The request message to be modified.

  Returns:
    The modified request message.
  """
  if not args.IsSpecified('upgrade'):
    return request
  if args.IsSpecified('upgrade_release') or args.IsSpecified(
      'upgrade_input_variables'
  ):
    return request
  request.unitOperation.upgrade = {}
  return request


def HandleEmptyDeprovision(unused_ref, args, request):
  """Request hook to handle use of --deprovision flag.

  Args:
    unused_ref: A resource ref to the parsed resource.
    args: Parsed args namespace containing the flags.
    request: The request message to be modified.

  Returns:
    The modified request message.
  """
  if not args.IsSpecified('deprovision'):
    return request
  request.unitOperation.deprovision = {}
  return request


def HandleOneOfOperationTypeUpdate(unused_ref, args, request):
  """Request hook to handle updates to the operation type.

  The declarative framework does not fully support one_of fields in updates. For
  example, if the command 'saas-runtime unit-operations update --provision' is
  run, the request will have an empty upgrade field but that field should not be
  present at all. This hook will delete the unspecified one_of field from the
  request.

  Args:
    unused_ref: A resource ref to the parsed resource.
    args: Parsed args namespace containing the flags.
    request: The request message to be modified.

  Returns:
    The modified request message.
  """
  provision_flags = [
      'add_provision_input_variables',
      'clear_provision_input_variables',
      'clear_provision_release',
      'provision',
      'provision_input_variables',
      'provision_release',
      'remove_provision_input_variables',
  ]
  upgrade_flags = [
      'add_upgrade_input_variables',
      'clear_upgrade_input_variables',
      'clear_upgrade_release',
      'upgrade',
      'upgrade_input_variables',
      'upgrade_release',
      'remove_upgrade_input_variables',
  ]
  deprovision_flags = ['deprovision']

  operation_flags = {
      'provision': any(args.IsSpecified(flag) for flag in provision_flags),
      'upgrade': any(args.IsSpecified(flag) for flag in upgrade_flags),
      'deprovision': any(args.IsSpecified(flag) for flag in deprovision_flags),
  }

  for operation, is_specified in operation_flags.items():
    if (
        not is_specified
        and hasattr(request.unitOperation, operation)
        and getattr(request.unitOperation, operation) is not None
    ):
      setattr(request.unitOperation, operation, None)
  return request
