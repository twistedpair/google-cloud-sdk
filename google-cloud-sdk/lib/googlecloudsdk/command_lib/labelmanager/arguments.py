# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Utilities for defining Label Manager arguments on a parser."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import base


def AddDisplayNameArgToParser(parser):
  """Adds argument for the label key display name to the parser.

  Args:
    parser: ArgumentInterceptor, An argparse parser.
  """
  parser.add_argument(
      'DISPLAY_NAME',
      metavar='DISPLAY_NAME',
      help=('Display name for the label key. The display name must be 1-63 '
            'characters, beginning and ending with an alphanumeric character '
            '([a-z0-9A-Z]) with dashes (-), underscores (_), dots (.), and '
            'alphanumerics between.'))


def AddParentArgToParser(parser):
  """Adds argument for the label parent to the parser.

  Args:
    parser: ArgumentInterceptor, An argparse parser.
  """
  parser.add_argument(
      'PARENT',
      metavar='PARENT',
      help=(
          'Parent of the label key or value. This must be the form '
          'organizations/{org_id} for a label key and labelKeys/{lable_key_id} '
          'for a label value.'))


def AddLabelParentArgToParser(parser):
  """Adds argument for the label parent to the parser.

  Args:
    parser: ArgumentInterceptor, An argparse parser.
  """
  parser.add_argument(
      '--label-parent',
      required=True,
      metavar='LABEL_PARENT',
      help=(
          'Parent of the label key or value. This must be the form '
          'organizations/{org_id} for a label key and labelKeys/{lable_key_id} '
          'for a label value.'))


def AddDescriptionArgToParser(parser):
  """Adds argument for the label description to the parser.

  Args:
    parser: ArgumentInterceptor, An argparse parser.
  """
  parser.add_argument(
      '--description',
      metavar='DESCRIPTION',
      help=('Optional user-assigned description of the label. '
            'Must not exceed 256 characters.'))


def AddAsyncArgToParser(parser):
  """Adds async flag to the parser.

  Args:
    parser: ArgumentInterceptor, An argparse parser.
  """
  base.ASYNC_FLAG.AddToParser(parser)
