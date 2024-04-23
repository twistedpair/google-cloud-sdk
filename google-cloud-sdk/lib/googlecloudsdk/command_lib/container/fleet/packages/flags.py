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
"""Common flags for fleet packages commands."""

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.core import properties


def GetProject(args):
  return args.project or properties.VALUES.core.project.Get(required=True)


def GetLocation(args):
  return args.location or properties.VALUES.config_delivery.location.Get(
      required=True
  )


def AddNameFlag(parser):
  parser.add_argument('name', help='Resource name.')


def AddReleaseFlag(parser):
  parser.add_argument(
      'release', help='Release identifier, either a version or tag.'
  )


def AddFleetPackageFlag(parser):
  parser.add_argument(
      '--fleet-package',
      required=True,
      help='Parent Fleet Package of the Rollout.',
  )


def AddSourceFlag(parser):
  parser.add_argument(
      '--source',
      required=False,
      help='Source file containing Fleet Package configuration.',
  )


def AddLocationFlag(parser):
  parser.add_argument(
      '--location', required=False, help='Google Cloud zone or region.'
  )


def AddDescriptionFlag(parser):
  parser.add_argument(
      '--description', required=False, help='Resource description.'
  )


def AddResourceBundleFlag(parser):
  parser.add_argument(
      '--resource-bundle', required=True, help='Resource Bundle name.'
  )


def AddLifecycleFlag(parser):
  parser.add_argument(
      '--lifecycle', required=False, help='Lifecycle of the Release.'
  )


def ProjectAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='project',
      help_text='Project ID for the {resource}.',
      fallthroughs=[deps.PropertyFallthrough(properties.VALUES.core.project)],
  )


def LocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='Google Cloud zone or region for the {resource}.',
      fallthroughs=[
          deps.PropertyFallthrough(properties.VALUES.config_delivery.location)
      ],
  )


def FleetPackageAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='fleet_package', help_text='Fleet Package name.'
  )


def GetLocationResourceSpec():
  return concepts.ResourceSpec(
      'configdelivery.projects.locations',
      resource_name='location',
      projectsId=ProjectAttributeConfig(),
  )


def GetFleetPackageResourceSpec():
  return concepts.ResourceSpec(
      'configdelivery.projects.locations.fleetPackages',
      resource_name='fleet_package',
      fleetPackagesId=FleetPackageAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=ProjectAttributeConfig(),
  )
