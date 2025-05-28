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
from googlecloudsdk.core import resources


def GetProject(args):
  return args.project or properties.VALUES.core.project.Get(required=True)


def GetLocation(args):
  return args.location or properties.VALUES.config_delivery.location.Get(
      required=True
  )


def AddLessFlag(parser):
  parser.add_argument(
      '--less',
      required=False,
      default=False,
      action='store_true',
      help='Show less verbose output.',
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
      required=True,
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


def AddForceDeleteFlag(parser, resource_name):
  parser.add_argument(
      '--force',
      required=False,
      default=False,
      action='store_true',
      help=(
          'If true, force deletion of any child resources. Otherwise,'
          f' attempting to delete a {resource_name} with children will fail.'
      ),
  )


def AddLifecycleFlag(parser):
  parser.add_argument(
      '--lifecycle', required=False, help='Lifecycle of the Release.'
  )


def AddVariantsPatternFlag(parser):
  parser.add_argument(
      '--variants-pattern',
      required=False,
      help="""Glob pattern to Variants of the Release, to be paired with the
        ``--source'' arg.
        ex: --source=/manifests-dir/ --variants-pattern=```**```,
            --source=/manifests-dir/ --variants-pattern=us-```*```.yaml,
            --source=/manifests/dir/ --variants-pattern=```*/*```.yaml""",
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
      name='fleet-package', help_text='Fleet Package name.'
  )


def RolloutAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='rollout', help_text='Rollout name.'
  )


def GetFleetPackageResourceSpec():
  return concepts.ResourceSpec(
      'configdelivery.projects.locations.fleetPackages',
      resource_name='fleet-package',
      fleetPackagesId=FleetPackageAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=ProjectAttributeConfig(),
  )


def GetRolloutResourceSpec():
  return concepts.ResourceSpec(
      'configdelivery.projects.locations.fleetPackages.rollouts',
      resource_name='rollout',
      rolloutsId=RolloutAttributeConfig(),
      fleetPackagesId=FleetPackageAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=ProjectAttributeConfig(),
  )


def AddUriFlags(parser, collection, api_version):
  """Adds `--uri` flag to the parser object for list commands.

  Args:
    parser: The argparse parser.
    collection: str, The resource collection name.
    api_version: str, The API version to use.
  """

  def _GetResourceUri(resource):
    resource_relative_name = resources.REGISTRY.ParseRelativeName(
        resource.name, collection=collection, api_version=api_version
    )
    return resource_relative_name.SelfLink()

  parser.display_info.AddUriFunc(_GetResourceUri)
