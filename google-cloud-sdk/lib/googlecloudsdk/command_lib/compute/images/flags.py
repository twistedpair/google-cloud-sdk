# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Flags and helpers for the compute backend-buckets commands."""

from googlecloudsdk.command_lib.compute import flags as compute_flags

_SOURCE_DISK_DETAILED_HELP = """\
        A source disk to create the image from. The value for this option can be
        the name of a disk with the zone specified via ``--source-disk-zone''
        flag.

        This flag is mutually exclusive with ``--source-uri''.
"""
_SOURCE_DISK_ZONE_EXPLANATION = compute_flags.ZONE_PROPERTY_EXPLANATION

DISK_IMAGE_ARG = compute_flags.ResourceArgument(
    resource_name='disk image',
    completion_resource_id='compute.images',
    global_collection='compute.images')

SOURCE_DISK_ARG = compute_flags.ResourceArgument(
    resource_name='source disk',
    name='--source-disk',
    completion_resource_id='compute.disks',
    zonal_collection='compute.disks',
    detailed_help=_SOURCE_DISK_DETAILED_HELP,
    zone_explanation=_SOURCE_DISK_ZONE_EXPLANATION,
    required=False)
