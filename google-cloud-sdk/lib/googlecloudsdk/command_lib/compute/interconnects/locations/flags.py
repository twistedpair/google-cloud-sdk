# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Flags and helpers for the compute networks commands."""

from googlecloudsdk.command_lib.compute import flags as compute_flags


def InterconnectLocationArgument(required=True):
  return compute_flags.ResourceArgument(
      resource_name='interconnect location',
      completion_resource_id='compute.interconnectLocations',
      plural=False,
      required=required,
      global_collection='compute.interconnectLocations')


def InterconnectLocationArgumentForOtherResource(short_help,
                                                 required=True,
                                                 detailed_help=None):
  return compute_flags.ResourceArgument(
      name='--location',
      resource_name='interconnectLocation',
      completion_resource_id='compute.interconnectLocations',
      plural=False,
      required=required,
      global_collection='compute.interconnectLocations',
      short_help=short_help,
      detailed_help=detailed_help)
