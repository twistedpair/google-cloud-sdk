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

from googlecloudsdk.calliope import arg_parsers


def AddCreateWorkloadFlags(parser):
  parser.add_argument(
      '--location',
      required=True,
      choices=[
          'us-central1', 'us-east1', 'us-east4', 'us-west1', 'us-west2',
          'us-west3', 'us-west4'
      ],
      help=('The location of the new Assured Workloads environment. For a '
            'current list of supported LOCATION values, see '
            '[Assured Workloads locations]'
            '(http://cloud/assured-workloads/docs/locations).'))
  parser.add_argument(
      '--organization',
      required=True,
      help=('The parent organization of the new Assured Workloads environment, '
            'provided as an organization ID'))
  parser.add_argument(
      '--external-identifier',
      help='The external identifier of the new Assured Workloads environment')
  parser.add_argument(
      '--display-name',
      required=True,
      help='The display name of the new Assured Workloads environment')
  parser.add_argument(
      '--compliance-regime',
      required=True,
      choices=['CJIS', 'FEDRAMP_HIGH', 'FEDRAMP_MODERATE', 'IL4'],
      help='The compliance regime of the new Assured Workloads environment')
  parser.add_argument(
      '--billing-account',
      required=True,
      help=('The billing account of the new Assured Workloads environment, for '
            'example, billingAccounts/0000AA-AAA00A-A0A0A0'))
  parser.add_argument(
      '--next-rotation-time',
      required=True,
      help=('The next rotation time of the new Assured Workloads environment, '
            'for example, 2020-12-30T10:15:30.00Z'))
  parser.add_argument(
      '--rotation-period',
      required=True,
      help=('The billing account of the new Assured Workloads environment, '
            'for example, 172800s'))
  parser.add_argument(
      '--labels',
      type=arg_parsers.ArgDict(),
      metavar='KEY=VALUE',
      help=('The labels of the new Assured Workloads environment, for example, '
            'LabelKey1=LabelValue1,LabelKey2=LabelValue2'))


def AddDeleteWorkloadFlags(parser):
  parser.add_argument(
      'resource',
      help=('The Assured Workloads resource to delete, for example, '
            'organizations/{ORG_ID}/locations/{LOCATION}/'
            'workloads/{WORKLOAD_ID}.'))
  # TODO(b/166449888): Add support for multiple resource formats
  parser.add_argument(
      '--etag',
      help=('The etag acquired by reading the Assured Workloads environment or '
            'AW "resource".'))


def AddDescribeWorkloadFlags(parser):
  # TODO(b/166449888): add support for resources in multiple formats
  parser.add_argument(
      'resource',
      help=('The Assured Workloads resource to describe, for example, '
            'organizations/{ORG_ID}/locations/{LOCATION}/'
            'workloads/{WORKLOAD_ID}.'))


def AddUpdateWorkloadFlags(parser):
  parser.add_argument(
      'resource',
      help=('The Assured Workloads environment resource to update, in the '
            'form: organizations/{ORG_ID}/locations/{LOCATION}/'
            'workloads/{WORKLOAD_ID}.'))
  parser.add_argument(
      '--etag',
      help=('The etag acquired by reading the Assured Workloads environment '
            'before updating.'))
  updatable_fields = parser.add_group(
      required=True,
      help='Settings that can be updated on the Assured Workloads environment.')
  updatable_fields.add_argument(
      '--display-name',
      help='The new display name of the Assured Workloads environment.')
  updatable_fields.add_argument(
      '--labels',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      help=('The new labels of the Assured Workloads environment, for example, '
            'LabelKey1=LabelValue1,LabelKey2=LabelValue2'))


def AddDescribeOperationFlags(parser):
  parser.add_argument(
      'resource',
      help=('The Assured Workloads operation resource to describe, for example,'
            ' organizations/{ORG_ID}/locations/{LOCATION}/'
            'operations/{OPERATION_ID}.'))
