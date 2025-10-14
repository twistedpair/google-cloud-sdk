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
"""Code that's shared between multiple network policies subcommands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Any

from googlecloudsdk.api_lib.compute import layer4_config_utils
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.resource_manager import tag_utils


def TranslateSecureTags(client, secure_tags: list[str]) -> list[Any]:
  """Returns a list of network policy rule secure tags, translating namespaced tags if needed.

  Args:
    client: compute client
    secure_tags: array of secure tag values

  Returns:
    List of network policy rule secure tags
  """

  return [
      client.messages.NetworkPolicyTrafficClassificationRuleSecureTag(
          name=_TranslateSecureTag(tag)
      )
      for tag in secure_tags
  ]


def _TranslateSecureTag(secure_tag: str) -> Any:
  """Returns a unified secure tag identifier.

  Translates the namespaced tag if required.

  Args:
    secure_tag: secure tag value in format tagValues/ID or
      ORG_ID/TAG_KEY_NAME/TAG_VALUE_NAME

  Returns:
    Secure tag name in unified format tagValues/ID
  """
  if secure_tag.startswith('tagValues/'):
    return secure_tag
  return tag_utils.GetNamespacedResource(secure_tag, tag_utils.TAG_VALUES).name


def ParseLayer4Configs(
    layer4_configs: list[str],
    message_classes: Any,
) -> list[Any]:
  """Parses protocol:port mappings for --layer4-configs command line."""
  return [
      message_classes.NetworkPolicyTrafficClassificationRuleMatcherLayer4Config(
          ipProtocol=config.ip_protocol,
          ports=[config.ports] if config.ports else [],
      )
      for config in (
          layer4_config_utils.ParseLayer4Config(layer4_config)
          for layer4_config in layer4_configs
      )
  ]


def ConvertPriorityToInt(priority: str) -> int:
  try:
    int_priority = int(priority)
  except ValueError as e:
    raise calliope_exceptions.InvalidArgumentException(
        'priority', 'priority must be a valid non-negative integer.'
    ) from e
  if int_priority < 0:
    raise calliope_exceptions.InvalidArgumentException(
        'priority', 'priority must be a valid non-negative integer.'
    )
  return int_priority
