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


def AddAllowMissing(
    parser,
    help_text="If set to true, and the repository is not found, the request will succeed but no action will be taken on the server.",
):
  parser.add_argument(
      "--allow-missing",
      dest="allow_missing",
      required=False,
      default=False,
      help=help_text,
      action="store_true",
  )


def AddInstance(
    parser,
    help_text="Secure Source Manager instance used to create the repo",
):
  parser.add_argument(
      "--instance", dest="instance", required=True, help=help_text
  )


def AddKmsKey(parser, help_text="KMS key used to encrypt instance optionally."):
  parser.add_argument(
      "--kms-key", dest="kms_key", required=False, help=help_text
  )


def AddMaxWait(
    parser,
    default_max_wait,
    help_text="Time to synchronously wait for the operation to complete, after which the operation continues asynchronously. Ignored if `--no-async` isn't specified. See $ gcloud topic datetimes for information on time formats.",
):
  parser.add_argument(
      "--max-wait",
      dest="max_wait",
      required=False,
      default=default_max_wait,
      help=help_text,
      type=arg_parsers.Duration(),
  )

def AddIsPrivate(parser, help_text="Bool indicator for private instance."):
  parser.add_argument(
      "--is-private",
      dest="is_private",
      action="store_true",
      required=False,
      help=help_text,
  )

def AddCAPool(parser, help_text="CA Pool path for private instance."):
  parser.add_argument(
      "--ca-pool", dest="ca_pool", required=False, help=help_text
  )


def AddPageToken(
    parser,
    help_text="Token identifying a page of results the server should return.",
):
  parser.add_argument(
      "--page-token",
      dest="page_token",
      required=False,
      default=None,
      help=help_text,
  )
