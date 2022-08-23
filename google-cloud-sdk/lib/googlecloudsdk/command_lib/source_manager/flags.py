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
"""Flag helpers for the source-manager commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers


def AddMaxWait(parser,
               default_max_wait,
               help_text="Time to synchronously wait for the operation to "
               "complete, after which the operation continues asynchronously. "
               "Ignored if --no-async isn't specified. "
               "See $ gcloud topic datetimes for information on time formats."):
  parser.add_argument(
      "--max-wait",
      dest="max_wait",
      required=False,
      default=default_max_wait,
      help=help_text,
      type=arg_parsers.Duration())


def AddAdminAccount(parser,
                    help_text="The first user when the instance is created. "
                    "Default to the current account."):
  parser.add_argument(
      "--admin-account",
      dest="admin_account",
      required=False,
      help=help_text
  )
