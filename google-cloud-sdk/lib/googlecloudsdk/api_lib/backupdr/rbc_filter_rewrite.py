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

"""Helpers for list filter parameter."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import string

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core.resource import resource_expr_rewrite


class ListFilterRewrite(resource_expr_rewrite.Backend):
  """Limit filter expressions to those supported by the ProtectionSummary API backend."""
  _VALID_FILTER_MAPPING = {
      'targetResourceDisplayName': 'target_resource_display_name',
      'targetResourceType': 'target_resource_type',
      'backupConfigured': 'backup_configured',
      'vaulted': 'vaulted',
      'backupConfigsDetails.backupConfigSourceDisplayName':
          'backup_configs_details.backup_config_source_display_name',
      'backupConfigsDetails.type': 'backup_configs_details.type',
  }

  _VALID_SERVER_FILTERS = {
      'target_resource_display_name': string,
      'target_resource_type': string,
      'backup_configured': bool,
      'vaulted': bool,
      'backup_configs_details.backup_config_source_display_name': string,
      'backup_configs_details.type': string,
  }

  def RewriteTerm(self, key, op, operand, key_type):
    """Rewrites a <key op operand> term of a filter expression.

    Args:
      key: The key, a string.
      op: The operator, a string.
      operand: The operand, a string or list of strings.
      key_type: The key type, unknown if None.

    Returns:
      the new term, as a string.
    """
    key = self._RewriteKey(key)
    op = self._RewriteOp(key, op)
    operand = self._RewriteOperand(key, operand)
    return f'{key}{op}{operand}'

  def Parenthesize(self, expression):
    # Override parenthesize to not parenthesize AND/OR.
    return expression

  def _RewriteKey(self, key):
    if key in self._VALID_FILTER_MAPPING:
      return self._VALID_FILTER_MAPPING[key]
    if key in self._VALID_SERVER_FILTERS:
      return key
    else:
      raise exceptions.InvalidArgumentException(
          'filter',
          'Invalid filter key: %s. Valid filters are: %s'
          % (key, ', '.join(self._VALID_SERVER_FILTERS.keys()))
      )

  # _RewriteOp replaces the EQ operator with HAS for member fields such as:
  # backup_configs_details.backup_config_source_display_name,
  # backup_configs_details.type
  def _RewriteOp(self, key, op):
    if '.' not in key:
      return op
    if op == '=':
      return ':'
    return op

  def _RewriteOperand(self, key, operand):
    # If the key is a boolean field then do not quote the operand.
    if self._VALID_SERVER_FILTERS[key] == bool:
      return operand
    return self.QuoteOperand(operand, always=True)
