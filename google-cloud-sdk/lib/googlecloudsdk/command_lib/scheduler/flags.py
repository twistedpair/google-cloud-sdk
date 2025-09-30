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
"""Utilities for flags for `gcloud scheduler` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import base


def DescribeCmekConfigResourceFlag(parser):
  """Add flags for CMEK Describe."""

  kms_location_arg = base.Argument(
      '--location',
      required=True,
      help="""\
            Google Cloud location for the KMS key.
            """,
  )

  kms_location_arg.AddToParser(parser)


def UpdateAndClearCmekConfigResourceFlag(parser):
  """Add flags for CMEK Update."""

  kms_key_name_arg = base.Argument(
      '--kms-key-name',
      help=(
          'Fully qualified identifier for the key or just the key ID. The'
          ' latter requires that the --kms-keyring and --kms-project flags be'
          ' provided too.'
      ),
      required=True,
  )

  kms_keyring_arg = base.Argument(
      '--kms-keyring',
      help="""\
            KMS keyring of the KMS key.
            """,
  )
  kms_location_arg = base.Argument(
      '--location',
      help="""\
            Google Cloud location for the KMS key.
            """,
  )
  kms_project_arg = base.Argument(
      '--kms-project',
      help="""\
            Google Cloud project for the KMS key.
            """,
  )
  # UPDATE
  cmek_update_group = base.ArgumentGroup(
      help='Flags for Updating CMEK Resource key',
  )
  cmek_update_group.AddArgument(kms_key_name_arg)
  cmek_update_group.AddArgument(kms_keyring_arg)
  cmek_update_group.AddArgument(kms_project_arg)

  # CLEAR
  clear_kms_key_name_flag = base.Argument(
      '--clear-kms-key',
      action='store_true',
      required=True,
      help=(
          'Disables CMEK for Cloud Scheduler in the specified location by'
          ' clearing the Cloud KMS cryptokey from the Cloud Scheduler project'
          ' and CMEK configuration.'
      ),
  )
  cmek_clear_group = base.ArgumentGroup(
      help='Flags for clearing CMEK Resource key.',
  )
  cmek_clear_group.AddArgument(clear_kms_key_name_flag)

  # UPDATE AND CLEAR GROUP.
  cmek_clear_update_group = base.ArgumentGroup(
      help='Flags for Clearing or Updating CMEK Resource', mutex=True
  )
  cmek_clear_update_group.AddArgument(cmek_clear_group)
  cmek_clear_update_group.AddArgument(cmek_update_group)

  kms_location_arg.AddToParser(parser)
  cmek_clear_update_group.AddToParser(parser)
