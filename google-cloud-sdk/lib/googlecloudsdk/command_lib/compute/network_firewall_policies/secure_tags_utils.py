# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Code that's shared between multiple org firewall policies subcommands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.resource_manager import tag_utils


def TranslateSecureTagsForFirewallPolicy(client, secure_tags):
  """Returns a list of firewall policy rule secure tags, translating namespaced tags if needed.

  Args:
    client: compute client
    secure_tags: array of secure tag values

  Returns:
    List of firewall policy rule secure tags
  """

  ret_secure_tags = []
  for tag in secure_tags:
    if tag.startswith('tagValues/'):
      ret_secure_tags.append(
          client.messages.FirewallPolicyRuleSecureTag(name=tag))
    else:
      ret_secure_tags.append(
          client.messages.FirewallPolicyRuleSecureTag(
              name=tag_utils.GetNamespacedResource(
                  tag, tag_utils.TAG_VALUES
              ).name
          )
      )

  return ret_secure_tags
