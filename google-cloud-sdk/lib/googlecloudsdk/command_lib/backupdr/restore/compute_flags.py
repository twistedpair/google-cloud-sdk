# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Flags for backup-dr restore compute commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def AddNameArg(parser, required=True):
  parser.add_argument(
      '--name',
      type=str,
      required=required,
      help='Name of the restored Compute Instance.',
  )


def AddTargetZoneArg(parser, required=True):
  parser.add_argument(
      '--target-zone',
      type=str,
      required=required,
      help='Zone where the target instance is restored.',
  )


def AddTargetProjectArg(parser, required=True):
  name = '--target-project'
  project_spec = concepts.ResourceSpec(
      'backupdr.projects',
      resource_name='Target Project',
      disable_auto_completers=False,
  )

  concept_parsers.ConceptParser.ForResource(
      name,
      project_spec,
      'Project where the restore should happen.',
      required=required,
  ).AddToParser(parser)
