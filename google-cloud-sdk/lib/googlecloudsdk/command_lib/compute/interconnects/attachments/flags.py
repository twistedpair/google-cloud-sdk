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
"""Flags and helpers for the compute interconnects commands."""

from googlecloudsdk.command_lib.compute import flags as compute_flags


def InterconnectAttachmentArgument(required=True, plural=False):
  return compute_flags.ResourceArgument(
      resource_name='interconnect attachment',
      completion_resource_id='compute.interconnectAttachments',
      plural=plural,
      required=required,
      regional_collection='compute.interconnectAttachments',
      region_explanation=compute_flags.REGION_PROPERTY_EXPLANATION)


def InterconnectAttachmentArgumentForRouter(required=False,
                                            plural=False,
                                            operation_type='added'):
  resource_name = 'interconnectAttachment{0}'.format('s' if plural else '')
  return compute_flags.ResourceArgument(
      resource_name=resource_name,
      name='--interconnect-attachment',
      completion_resource_id='compute.interconnectAttachments',
      plural=plural,
      required=required,
      regional_collection='compute.interconnectAttachments',
      short_help='The interconnect attachment of the interface being {0}.'
      .format(operation_type),
      region_explanation='If not specified it will be set to the region of '
      'the router.')
