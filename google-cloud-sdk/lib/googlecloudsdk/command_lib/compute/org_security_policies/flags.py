# -*- coding: utf-8 -*- #
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Flags and helpers for the compute organization security policies commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags


DEFAULT_LIST_FORMAT = """\
    table(
      name:label=ID,
      displayName,
      shortName,
      description
    )"""


class OrgSecurityPoliciesCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(OrgSecurityPoliciesCompleter, self).__init__(
        collection='compute.organizationSecurityPolicies',
        list_command='beta compute org-security-policies list --uri',
        **kwargs
    )


def OrgSecurityPolicyRuleListArgument(required=False,
                                      plural=False,
                                      operation=None):
  return compute_flags.ResourceArgument(
      name='SECURITY_POLICY',
      resource_name='security policy',
      completer=OrgSecurityPoliciesCompleter,
      plural=plural,
      required=required,
      custom_plural='security policies',
      short_help='Short name of the security policy to {0}.'.format(operation),
      global_collection='compute.organizationSecurityPolicies',
  )


def OrgSecurityPolicyArgument(required=False, plural=False, operation=None):
  return compute_flags.ResourceArgument(
      name='SECURITY_POLICY',
      resource_name='security policy',
      completer=OrgSecurityPoliciesCompleter,
      plural=plural,
      required=required,
      custom_plural='security policies',
      short_help='Short name or ID of the security policy to {0}.'.format(
          operation
      ),
      global_collection='compute.organizationSecurityPolicies',
  )


def OrgSecurityPolicyAssociationsArgument(required=False, plural=False):
  return compute_flags.ResourceArgument(
      name='name',
      resource_name='association',
      completer=OrgSecurityPoliciesCompleter,
      plural=plural,
      required=required,
      global_collection='compute.organizationSecurityPolicies')


def OrgSecurityPolicyRuleArgument(
    required=False,
    plural=False,
    operation=None,
):
  return compute_flags.ResourceArgument(
      name='priority',
      resource_name='security policy rule',
      completer=OrgSecurityPoliciesCompleter,
      plural=plural,
      required=required,
      global_collection='compute.organizationSecurityPolicies',
      short_help='Priority of the security policy rule to {}.'.format(
          operation))


def AddArgSpCreation(parser):
  """Adds the argument for security policy creation."""
  parser.add_argument(
      '--display-name', help='A textual name of the security policy.'
  )

  parser.add_argument(
      '--short-name', help='A textual name of the security policy.'
  )

  group = parser.add_group(required=True, mutex=True)

  group.add_argument(
      '--organization',
      help=('Organization in which the organization security policy'
            ' is to be created.'))

  group.add_argument(
      '--folder',
      help=('Folder in which the organization security policy is to be'
            ' created.'))

  parser.add_argument(
      '--description',
      help=('An optional, textual description for the organization security'
            ' policy.'))

  creation_options = parser.add_group(mutex=True, help='Creation options.')

  creation_options.add_argument(
      '--type',
      choices=['CLOUD_ARMOR', 'FIREWALL'],
      type=lambda x: x.upper().replace('-', '_'),
      metavar='SECURITY_POLICY_TYPE',
      help=(
          'The type indicates the intended use of the organization security '
          'policy.'
      ),
  )

  creation_options.add_argument(
      '--file-name',
      help=(
          'The name of the JSON or YAML file to create a organization '
          'security policy config from.'
      ),
  )

  parser.add_argument(
      '--file-format',
      choices=['json', 'yaml'],
      help=(
          'The format of the file to create the organization security policy '
          'config from. Specify either yaml or json. Defaults to yaml if not '
          'specified. Will be ignored if --file-name is not specified.'
      ),
  )


def AddArgsCopyRules(parser):
  """Adds the argument for security policy copy rules."""
  parser.add_argument(
      '--source-security-policy',
      required=True,
      help=('The URL of the source security policy to copy the rules from.'))

  parser.add_argument(
      '--organization',
      help=(
          'Organization in which the organization security policy to copy the'
          ' rules to. Must be set if security-policy is the short name.'
      ),
  )


def AddArgsListSp(parser):
  """Adds the argument for security policy list."""
  group = parser.add_group(required=True, mutex=True)

  group.add_argument(
      '--organization',
      help=('Organization in which security policies are listed'))

  group.add_argument(
      '--folder', help=('Folder in which security policies are listed'))


def AddArgsMove(parser):
  """Adds the argument for security policy move."""
  parser.add_argument(
      '--organization',
      help=(
          'Organization in which the organization security policy is to be'
          ' moved. Must be set if SECURITY_POLICY is the short name.'
      ),
  )

  parser.add_argument(
      '--folder',
      help=('Folder to which the organization security policy is to be'
            ' moved.'))


def AddArgsUpdateSp(parser):
  """Adds the argument for security policy update."""
  parser.add_argument(
      '--organization',
      help=(
          'Organization in which the organization security policy is to be'
          ' updated. Must be set if SECURITY_POLICY is the short name.'
      ),
  )
  parser.add_argument(
      '--description',
      help=('An optional, textual description for the organization security'
            ' policy.'))


def AddPriority(parser, operation, is_plural=False):
  """Adds the priority argument to the argparse."""
  parser.add_argument(
      'name' + ('s' if is_plural else ''),
      metavar='PRIORITY',
      nargs='*' if is_plural else None,
      completer=OrgSecurityPoliciesCompleter,
      help=('Priority of the rule{0} to {1}. Rules are evaluated in order '
            'from highest priority to lowest priority where 0 is the highest '
            'priority and 2147483647 is the lowest priority.'.format(
                's' if is_plural else '', operation)))


def AddAction(parser, required=True):
  """Adds the action argument to the argparse."""
  parser.add_argument(
      '--action',
      choices={
          'allow': 'Allows the request from HTTP(S) Load Balancing.',
          'goto-next': (
              'Defers enforcement to the next policy in the hierarchy.'
          ),
          'deny': '(DEPRECATED) Only used for Hierarchical Firewalls.',
          'deny-403': (
              'Denies the request from HTTP(S) Load Balancing, with an HTTP '
              'response status code of 403.'
          ),
          'deny-404': (
              'Denies the request from HTTP(S) Load Balancing, with an HTTP '
              'response status code of 404.'
          ),
          'deny-502': (
              'Denies the request from HTTP(S) Load Balancing, with an HTTP '
              'response status code of 502.'
          ),
          'redirect': (
              'Redirects the request from HTTP(S) Load Balancing, based on '
              'redirect options.'
          ),
      },
      type=lambda x: x.lower(),
      required=required,
      help='Action to take if the request matches the match condition.',
  )


def AddSecurityPolicyId(parser, required=True, operation=None):
  """Adds the security policy ID argument to the argparse."""
  parser.add_argument(
      '--security-policy',
      required=required,
      help=(
          'short name of the security policy into which the rule should '
          'be {}.'.format(operation)
      ),
  )


def AddOrganization(parser, required=True):
  parser.add_argument(
      '--organization',
      required=required,
      help=(
          'Organization which the organization security policy belongs to. '
          'Must be set if SECURITY_POLICY is short name.'
      ),
  )


def AddSrcIpRanges(parser, required=False):
  """Adds the source IP ranges."""
  parser.add_argument(
      '--src-ip-ranges',
      type=arg_parsers.ArgList(),
      required=required,
      metavar='SRC_IP_RANGE',
      help=('Source IP ranges to match for this rule. '
            'Can only be specified if DIRECTION is ingress.'))


def AddDestIpRanges(parser, required=False):
  """Adds the destination IP ranges."""
  parser.add_argument(
      '--dest-ip-ranges',
      type=arg_parsers.ArgList(),
      required=required,
      metavar='DEST_IP_RANGE',
      help=('Destination IP ranges to match for this rule. '
            'Can only be specified if DIRECTION is egress.'))


def AddDestPorts(parser, required=False):
  """Adds the destination ports."""
  parser.add_argument(
      '--dest-ports',
      type=arg_parsers.ArgList(),
      required=required,
      metavar='DEST_PORTS',
      help=('A list of destination protocols and ports to which the firewall '
            'rule will apply.'))


def AddLayer4Configs(parser, required=False):
  """Adds the layer4 configs."""
  parser.add_argument(
      '--layer4-configs',
      type=arg_parsers.ArgList(),
      required=required,
      metavar='LAYER4_CONFIG',
      help=('A list of destination protocols and ports to which the firewall '
            'rule will apply.'))


def AddDirection(parser, required=False):
  """Adds the direction of the traffic to which the rule is applied."""
  parser.add_argument(
      '--direction',
      required=required,
      choices=['INGRESS', 'EGRESS'],
      help=(
          'Direction of the traffic the rule is applied. The default is to '
          'apply on incoming traffic.'
      ),
  )


def AddEnableLogging(parser, required=False):
  """Adds the option to enable logging."""
  parser.add_argument(
      '--enable-logging',
      required=required,
      action=arg_parsers.StoreTrueFalseAction,
      help=('Use this flag to enable logging of connections that allowed or '
            'denied by this rule.'))


def AddNewPriority(parser, operation=None):
  """Adds the new security policy rule priority to the argparse."""
  parser.add_argument(
      '--new-priority',
      help=('New priority for the rule to {}. Valid in [0, 65535]. '.format(
          operation)))


def AddTargetResources(parser, required=False):
  """Adds the target resources the rule is applied to."""
  parser.add_argument(
      '--target-resources',
      type=arg_parsers.ArgList(),
      metavar='TARGET_RESOURCES',
      required=required,
      help=('List of URLs of target resources to which the rule is applied.'))


def AddTargetServiceAccounts(parser, required=False):
  """Adds the target service accounts for the rule."""
  parser.add_argument(
      '--target-service-accounts',
      type=arg_parsers.ArgList(),
      metavar='TARGET_SERVICE_ACCOUNTS',
      required=required,
      help=('List of target service accounts for the rule.'))


def AddDescription(parser, required=False):
  """Adds the description of this rule."""
  parser.add_argument(
      '--description',
      required=required,
      help=('An optional, textual description for the rule.'))


def AddArgsCreateAssociation(parser):
  """Adds the arguments of association creation."""
  parser.add_argument(
      '--security-policy',
      required=True,
      help=('Security policy ID of the association.'))
  parser.add_argument(
      '--organization',
      help=(
          'ID of the organization to associate the security policy with. Must'
          ' be set if SECURITY_POLICY is short name.'
      ),
  )

  group = parser.add_group(required=False, mutex=True)
  group.add_argument(
      '--folder', help='ID of the folder to associate the security policy with.'
  )
  group.add_argument(
      '--project-number',
      help='Project number to associate the security policy with.',
  )

  parser.add_argument(
      '--replace-association-on-target',
      action='store_true',
      default=False,
      required=False,
      help=(
          'By default, if you attempt to insert an association to an '
          'organization or folder resource that is already associated with a '
          'security policy the method will fail. If this is set, the existing '
          ' association will be deleted at the same time that the new '
          'association is created.'))

  parser.add_argument(
      '--name',
      help=('Name to identify this association. If unspecified, the '
            'name will be set to "organization-{ORGANIZATION_ID}" '
            'or "folder-{FOLDER_ID}".'))

  parser.add_argument(
      '--excluded-projects',
      type=arg_parsers.ArgList(),
      metavar='EXCLUDED_PROJECTS',
      required=False,
      help=(
          'List of projects to exclude from the application of this security'
          ' policy. Projects should be specified in the form "projects/123".'
      ),
  )

  parser.add_argument(
      '--excluded-folders',
      type=arg_parsers.ArgList(),
      metavar='EXCLUDED_FOLDERS',
      required=False,
      help=(
          'List of folders to exclude from the application of this security'
          ' policy. Folders should be specified in the form "folders/123".'
      ),
  )


def AddArgsDeleteAssociation(parser):
  """Adds the arguments of association deletion."""
  parser.add_argument(
      '--security-policy',
      required=True,
      help='short name or ID of the security policy ID of the association.',
  )

  parser.add_argument(
      '--organization',
      help=(
          'ID of the organization in which the security policy is to be'
          ' detached. Must be set if SECURITY_POLICY is short name.'
      ),
  )


def AddArgsListAssociation(parser):
  """Adds the arguments of association list."""
  group = parser.add_group(required=True, mutex=True)

  group.add_argument(
      '--organization',
      help=('ID of the organization with which the association is listed.'))

  group.add_argument(
      '--folder',
      help=('ID of the folder with which the association is listed.'))
