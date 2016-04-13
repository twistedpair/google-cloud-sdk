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

"""Flags and helpers for the compute related commands."""

from googlecloudsdk.calliope import actions
from googlecloudsdk.core import properties

ZONE_PROPERTY_EXPLANATION = """\
If not specified, you will be prompted to select a zone.

To avoid prompting when this flag is omitted, you can set the
``compute/zone'' property:

  $ gcloud config set compute/zone ZONE

A list of zones can be fetched by running:

  $ gcloud compute zones list

To unset the property, run:

  $ gcloud config unset compute/zone

Alternatively, the zone can be stored in the environment variable
``CLOUDSDK_COMPUTE_ZONE''.
"""

ZONE_PROPERTY_EXPLANATION_NO_DEFAULT = """\
If not specified, you will be prompted to select a zone.

A list of zones can be fetched by running:

  $ gcloud compute zones list
"""

REGION_PROPERTY_EXPLANATION = """\
If not specified, you will be prompted to select a region.

To avoid prompting when this flag is omitted, you can set the
``compute/region'' property:

  $ gcloud config set compute/region REGION

A list of regions can be fetched by running:

  $ gcloud compute regions list

To unset the property, run:

  $ gcloud config unset compute/region

Alternatively, the region can be stored in the environment
variable ``CLOUDSDK_COMPUTE_REGION''.
"""

REGION_PROPERTY_EXPLANATION_NO_DEFAULT = """\
If not specified, you will be prompted to select a region.

A list of regions can be fetched by running:

  $ gcloud compute regions list
"""


def AddZoneFlag(parser, resource_type, operation_type,
                explanation=ZONE_PROPERTY_EXPLANATION):
  """Adds a --zone flag to the given parser."""
  short_help = 'The zone of the {0} to {1}.'.format(
      resource_type, operation_type)
  zone = parser.add_argument(
      '--zone',
      help=short_help,
      completion_resource='compute.zones',
      action=actions.StoreProperty(properties.VALUES.compute.zone))
  zone.detailed_help = '{0} {1}'.format(
      short_help, explanation)


def AddRegionFlag(parser, resource_type, operation_type,
                  explanation=REGION_PROPERTY_EXPLANATION):
  """Adds a --region flag to the given parser."""
  short_help = 'The region of the {0} to {1}.'.format(
      resource_type, operation_type)
  region = parser.add_argument(
      '--region',
      help=short_help,
      completion_resource='compute.regions',
      action=actions.StoreProperty(properties.VALUES.compute.region))
  region.detailed_help = '{0} {1}'.format(
      short_help, explanation)


