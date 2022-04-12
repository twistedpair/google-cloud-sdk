# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Common Flags for Overwatch commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import base


def get_organization_id_flag():
  return base.Argument(
      'ORGANIZATION',
      help='The organization ID in the format organizations/<ORG_ID>')


def get_size_flag():
  return base.Argument(
      '--size', required=False, help='The page size of overwatch list.')


def get_page_token_flag():
  return base.Argument(
      '--page-token',
      required=False,
      help='The page token to retrieve next page.')


def get_overwatch_path_flag():
  return base.Argument(
      'OVERWATCH',
      help="""The overwatch path specified in the resource format
           organizations/<ORG_ID>/locations/<REGION>/overwatches/<OVERWATCH_ID>.
            """)


def get_blueprint_plan_flag():
  return base.Argument(
      '--blueprint-plan-file',
      required=True,
      help='Path of the JSON file containing the blueprint plan.')


def get_update_mask_flag():
  return base.Argument(
      '--update-mask',
      help='Update mask providing the fields that are required to be updated.')


def get_operation_flag():
  return base.Argument(
      'OPERATION',
      help="""Operation ID of the long running operation to get status. Format
       operations/<OPERATION_ID>""")
