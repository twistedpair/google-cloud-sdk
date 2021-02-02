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
"""Flags module for Essential Contacts commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def AddContactIdArg(parser, help_text='id of contact'):
  """Adds an arg for the contact id to the parser."""
  parser.add_argument('CONTACT_ID', type=str, help=help_text)


def AddParentArgs(parser):
  """Add args for the parent resource of a contact to the parser."""
  parent_group = parser.add_mutually_exclusive_group(required=False)
  parent_group.add_argument(
      '--project',
      help='project number or id. only one of --project, --folder, or --organization can be provided. If none are provided then it uses config property [core/project].'
  )
  parent_group.add_argument(
      '--folder',
      help='folder number. only one of --project, --folder, or --organization can be provided. If none are provided then it uses config property [core/project].'
  )
  parent_group.add_argument(
      '--organization',
      help='organization number. either --project, --folder, or --organization must be provided. If none are provided then it uses config property [core/project].'
  )
