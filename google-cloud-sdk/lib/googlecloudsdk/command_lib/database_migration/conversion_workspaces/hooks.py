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
"""Hooks for conversion workspaces declerative yaml commands."""

import argparse
import re
from typing import Any, Dict, Generator

from apitools.base.py import encoding
from googlecloudsdk.generated_clients.apis.datamigration.v1 import datamigration_v1_messages as messages

_DISPLAY_NAME_PATTERN = re.compile(
    r'(?P<fileNo>\d+)-(?P<ruleOrder>\d+)-(?P<ruleName>.*)',
)


def ModifyMappingRuleResponse(
    response: Generator[messages.MappingRule, None, None],
    _: argparse.Namespace,
) -> Generator[Dict[str, Any], None, None]:
  """Modifies the mapping rule response to by more user friendly.

  Args:
    response: The mapping rule response to modify.
    _: argparse.Namespace, unused.

  Yields:
    The modified mapping rule response.
  """
  for rule in response:
    rule = encoding.MessageToDict(rule)

    rule['ruleScope'] = _RemovePrefix(
        value=rule['ruleScope'],
        prefix='DATABASE_ENTITY_TYPE_',
    )

    display_name = rule['displayName']
    display_name_matches = re.match(_DISPLAY_NAME_PATTERN, display_name)
    if display_name_matches:
      rule['displayName'] = display_name_matches.group('ruleName')

    yield rule


def _RemovePrefix(value: str, prefix: str) -> str:
  """Removes the prefix from the value if it exists."""
  if value.startswith(prefix):
    return value[len(prefix) :]
  return value
