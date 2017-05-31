# Copyright 2017 Google Inc. All Rights Reserved.
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

"""Code that's shared between multiple security policies subcommands."""

import base64
import json

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core.resource import resource_printer
import yaml


def SecurityPolicyFromFile(input_file, messages, file_format):
  """Returns the security policy read from the given file.

  Args:
    input_file: file, A file with a security policy config.
    messages: messages, The set of available messages.
    file_format: string, the format of the file to read from

  Returns:
    A security policy resource.
  """

  if file_format == 'yaml':
    try:
      parsed_security_policy = yaml.safe_load(input_file)
    except yaml.YAMLError as e:
      raise exceptions.BadFileException(
          'Error parsing YAML: {0}'.format(str(e)))
  else:
    try:
      parsed_security_policy = json.load(input_file)
    except ValueError as e:
      raise exceptions.BadFileException(
          'Error parsing JSON: {0}'.format(str(e)))

  security_policy = messages.SecurityPolicy()
  security_policy.description = parsed_security_policy['description']
  security_policy.fingerprint = base64.urlsafe_b64decode(
      parsed_security_policy['fingerprint'].encode('ascii'))

  rules = []
  for rule in parsed_security_policy['rules']:
    security_policy_rule = messages.SecurityPolicyRule()
    security_policy_rule.action = rule['action']
    security_policy_rule.description = rule['description']
    match = messages.SecurityPolicyRuleMatcher()
    match.srcIpRanges = rule['match']['srcIpRanges']
    security_policy_rule.match = match
    security_policy_rule.priority = rule['priority']
    security_policy_rule.preview = rule['preview']
    rules.append(security_policy_rule)

  security_policy.rules = rules

  return security_policy


def WriteToFile(output_file, security_policy, file_format):
  """Writes the given security policy in the given format to the given file.

  Args:
    output_file: file, File into which the security policy should be written.
    security_policy: resource, SecurityPolicy to be written out.
    file_format: string, the format of the file to write to.
  """
  resource_printer.Print(
      security_policy, print_format=file_format, out=output_file)
