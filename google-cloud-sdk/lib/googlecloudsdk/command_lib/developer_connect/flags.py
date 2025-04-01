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
"""Flags and helpers for the Developer Connect CLI."""


# Flags
def AddDiscoveryArgument(parser):
  """Creates state argument."""
  parser.add_argument(
      '--run-discovery',
      action='store_true',
      help=(
          'Sets the state of the insight config to PENDING and kicks off the'
          ' discovery flow.'
      ),
  )


def AddArtifactArgument(parser):
  """Creates artifact argument."""
  parser.add_argument(
      '--artifact-uri',
      metavar='ARTIFACT_URI',
      dest='artifact_uri',
      required=True,
      help=(
          'Identifier for the specific artifact you want to update'
      ),
  )


def AddBuildProjectArgument(parser):
  """Creates build project argument."""
  parser.add_argument(
      '--build-project',
      metavar='BUILD_PROJECT',
      dest='build_project',
      required=True,
      help=(
          'The project ID of the project to where the artifact is built.'
      ),
  )
