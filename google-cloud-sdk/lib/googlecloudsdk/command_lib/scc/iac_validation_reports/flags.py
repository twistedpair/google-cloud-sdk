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

"""Shared flags definitions for finding commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.calliope import base

FILTER_FLAG = base.Argument(
    "--filter",
    help="""Apply a Boolean filter EXPRESSION to each resource item to be listed.
    If the expression evaluates True, then that item is listed. For more details and
    examples of filter expressions, run $ gcloud topic filters. This flag interacts with
    other flags that are applied in this order: --flatten, --sort-by, --filter, --limit.""",
)


def AddParentOrFlagsGroup(parser):
  """Adds a mutually exclusive group that accepts either positional parent or --organization + --location."""
  group = parser.add_mutually_exclusive_group(required=True)

  # Positional parent argument
  group.add_argument(
      "PARENT",
      help=(
          "Parent of the IaC validation reports or fully qualified identifier"
          " for the IaC validation reports."
      ),
      nargs="?",
  )

  # Flag-based subgroup
  flags_group = group.add_argument_group(
      help="Specify organization and location using flags.",
  )
  flags_group.add_argument(
      "--organization",
      help="The organization ID (e.g., 123) that contains the resource.",
      required=True,
  )
  flags_group.add_argument(
      "--location",
      help=(
          "When data residency controls are enabled, this attribute specifies"
          " the location in which the resource is located and applicable."
      ),
      required=True,
  )
  return parser
