# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the Assured related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.assured import message_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.command_lib.assured import resource_args
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def AddListWorkloadsFlags(parser):
  parser.add_argument(
      '--location',
      required=True,
      help=(
          'The location of the Assured Workloads environments. For a '
          'current list of supported LOCATION values, see '
          '[Assured Workloads locations]'
          '(https://cloud.google.com/assured-workloads/docs/locations).'
      ),
  )
  parser.add_argument(
      '--organization',
      required=True,
      help=(
          'The parent organization of the Assured Workloads environments, '
          'provided as an organization ID.'
      ),
  )


def AddListOperationsFlags(parser):
  parser.add_argument(
      '--location',
      required=True,
      help=(
          'The location of the Assured Workloads operations. For a '
          'current list of supported LOCATION values, see '
          '[Assured Workloads locations]'
          '(https://cloud.google.com/assured-workloads/docs/locations).'
      ),
  )
  parser.add_argument(
      '--organization',
      required=True,
      help=(
          'The parent organization of the Assured Workloads operations, '
          'provided as an organization ID.'
      ),
  )


def AddCreateWorkloadFlags(parser, release_track):
  """Adds required flags to the assured workloads create command.

  Args:
    parser: Parser, Parser used to construct the command flags.
    release_track: ReleaseTrack, Release track of the command being called.

  Returns:
    None.
  """
  parser.add_argument(
      '--location',
      required=True,
      help=(
          'The location of the new Assured Workloads environment. For a '
          'current list of supported LOCATION values, see '
          '[Assured Workloads locations]'
          '(https://cloud.google.com/assured-workloads/docs/locations).'
      ),
  )
  parser.add_argument(
      '--organization',
      required=True,
      help=(
          'The parent organization of the new Assured Workloads environment, '
          'provided as an organization ID'
      ),
  )
  parser.add_argument(
      '--external-identifier',
      help='The external identifier of the new Assured Workloads environment',
  )
  parser.add_argument(
      '--display-name',
      required=True,
      help='The display name of the new Assured Workloads environment',
  )
  arg_utils.ChoiceEnumMapper(
      '--compliance-regime',
      message_util.GetComplianceRegimesEnum(release_track),
      include_filter=lambda regime: regime != 'COMPLIANCE_REGIME_UNSPECIFIED',
      required=True,
      help_str='The compliance regime of the new Assured Workloads environment',
  ).choice_arg.AddToParser(parser)
  arg_utils.ChoiceEnumMapper(
      '--partner',
      message_util.GetPartnersEnum(release_track),
      include_filter=lambda regime: regime != 'PARTNER_UNSPECIFIED',
      help_str=(
          'The partner choice when creating a workload managed by local trusted'
          ' partners.'
      ),
  ).choice_arg.AddToParser(parser)
  parser.add_argument(
      '--partner-permissions',
      type=arg_parsers.ArgDict(
          spec={
              'data-logs-viewer': bool,
          }
      ),
      metavar='KEY=VALUE',
      help=(
          'The partner permissions for the partner regime, for example,'
          ' data-logs-viewer=true/false'
      ),
  )
  parser.add_argument(
      '--partner-services-billing-account',
      required=False,
      help=(
          'Billing account necessary for purchasing services from Sovereign'
          ' Partners. This field is required for creating SIA/PSN/CNTXT'
          ' partner workloads. The caller should have'
          " 'billing.resourceAssociations.create' IAM permission on this"
          ' billing-account. The format of this string is'
          ' billingAccounts/AAAAAA-BBBBBB-CCCCCC'
      ),
  )
  parser.add_argument(
      '--billing-account',
      required=True,
      help=(
          'The billing account of the new Assured Workloads environment, for '
          'example, billingAccounts/0000AA-AAA00A-A0A0A0'
      ),
  )
  parser.add_argument(
      '--next-rotation-time',
      help=(
          'The next rotation time of the KMS settings of new Assured '
          'Workloads environment, for example, 2020-12-30T10:15:30.00Z'
      ),
  )
  parser.add_argument(
      '--rotation-period',
      help=(
          'The rotation period of the KMS settings of the new Assured '
          'Workloads environment, for example, 172800s'
      ),
  )
  parser.add_argument(
      '--labels',
      type=arg_parsers.ArgDict(),
      metavar='KEY=VALUE',
      help=(
          'The labels of the new Assured Workloads environment, for example, '
          'LabelKey1=LabelValue1,LabelKey2=LabelValue2'
      ),
  )
  parser.add_argument(
      '--provisioned-resources-parent',
      help=(
          'The parent of the provisioned projects, for example, '
          'folders/{FOLDER_ID}'
      ),
  )
  parser.add_argument(
      '--enable-sovereign-controls',
      type=bool,
      default=False,
      help=(
          'If true, enable sovereign controls for the new Assured Workloads '
          'environment, currently only supported by EU_REGIONS_AND_SUPPORT'
      ),
  )
  _AddResourceSettingsFlag(parser, release_track)


def _AddResourceSettingsFlag(parser, release_track):
  """Adds the resource settings flag to the assured workloads create command.

  Args:
    parser: Parser, Parser used to construct the command flags.
    release_track: ReleaseTrack, Release track of the command being called.

  Returns:
    None.
  """
  if release_track == calliope_base.ReleaseTrack.GA:
    parser.add_argument(
        '--resource-settings',
        type=arg_parsers.ArgDict(
            spec={
                'consumer-project-id': str,
                'consumer-project-name': str,
                'encryption-keys-project-id': str,
                'encryption-keys-project-name': str,
                'keyring-id': str,
            }
        ),
        metavar='KEY=VALUE',
        help=(
            'A comma-separated, key=value map of custom resource settings such'
            ' as custom project ids, for example:'
            ' consumer-project-id={CONSUMER_PROJECT_ID} Note: Currently only'
            ' consumer-project-id, consumer-project-name,'
            ' encryption-keys-project-id, encryption-keys-project-name and'
            ' keyring-id are supported. The encryption-keys-project-id,'
            ' encryption-keys-project-name and keyring-id settings can be'
            ' specified only if KMS settings are provided'
        ),
    )
  else:
    parser.add_argument(
        '--resource-settings',
        type=arg_parsers.ArgDict(
            spec={
                'encryption-keys-project-id': str,
                'encryption-keys-project-name': str,
                'keyring-id': str,
            }
        ),
        metavar='KEY=VALUE',
        help=(
            'A comma-separated, key=value map of custom resource settings such'
            ' as custom project ids, for example:'
            ' consumer-project-id={CONSUMER_PROJECT_ID} Note: Currently only'
            ' encryption-keys-project-id, encryption-keys-project-name and'
            ' keyring-id are supported. The encryption-keys-project-id,'
            ' encryption-keys-project-name and keyring-id settings can be'
            ' specified only if KMS settings are provided'
        ),
    )


def AddDeleteWorkloadFlags(parser):
  AddWorkloadResourceArgToParser(parser, verb='delete')
  parser.add_argument(
      '--etag',
      help=(
          'The etag acquired by reading the Assured Workloads environment or '
          'AW "resource".'
      ),
  )


def AddDescribeWorkloadFlags(parser):
  AddWorkloadResourceArgToParser(parser, verb='describe')


def AddDescribeViolationFlags(parser):
  AddViolationResourceArgToParser(parser, verb='describe')


def AddEnableResourceMonitoringFlags(parser):
  AddWorkloadResourceArgToParser(parser, verb='enable-resource-monitoring')


def AddUpdateWorkloadFlags(parser):
  """Method to add update workload flags."""
  AddWorkloadResourceArgToParser(parser, verb='update')
  parser.add_argument(
      '--etag',
      help=(
          'The etag acquired by reading the Assured Workloads environment '
          'before updating.'
      ),
  )
  updatable_fields = parser.add_group(
      required=True,
      help='Settings that can be updated on the Assured Workloads environment.',
  )
  updatable_fields.add_argument(
      '--display-name',
      help='The new display name of the Assured Workloads environment.',
  )
  updatable_fields.add_argument(
      '--violation-notifications-enabled',
      help='The notification setting of the Assured Workloads environment.',
  )
  updatable_fields.add_argument(
      '--labels',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      help=(
          'The new labels of the Assured Workloads environment, for example, '
          'LabelKey1=LabelValue1,LabelKey2=LabelValue2'
      ),
  )


def AddDescribeOperationFlags(parser):
  concept_parsers.ConceptParser.ForResource(
      'operation',
      resource_args.GetOperationResourceSpec(),
      'The Assured Workloads operation resource to describe.',
      required=True,
  ).AddToParser(parser)


def AddWorkloadResourceArgToParser(parser, verb):
  concept_parsers.ConceptParser.ForResource(
      'workload',
      resource_args.GetWorkloadResourceSpec(),
      'The Assured Workloads environment resource to {}.'.format(verb),
      required=True,
  ).AddToParser(parser)


def AddViolationResourceArgToParser(parser, verb):
  concept_parsers.ConceptParser.ForResource(
      'violation',
      resource_args.GetViolationResourceSpec(),
      'The Assured Workloads violation resource to {}.'.format(verb),
      required=True,
  ).AddToParser(parser)


def AddListViolationsFlags(parser):
  """Method to add list violations flags."""
  AddListWorkloadsFlags(parser)
  parser.add_argument(
      '--workload',
      required=True,
      help=(
          'The parent workload of the Assured Workloads violations, '
          'provided as workload ID.'
      ),
  )


def AddAcknowledgeViolationsFlags(parser):
  """Method to add acknowledge violations flags."""
  AddViolationResourceArgToParser(parser, verb='acknowledge')
  parser.add_argument(
      '--comment',
      required=True,
      help='Business justification used added to acknowledge a violation.',
  )
  parser.add_argument(
      '--acknowledge-type',
      help="""the acknowledge type for specified violation, which is one of:
      SINGLE_VIOLATION - to acknowledge specified violation,
      EXISTING_CHILD_RESOURCE_VIOLATIONS - to acknowledge specified org policy
      violation and all associated child resource violations.""",
  )
