# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Design Center Command Lib Flags."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def GetProjectResourceSpec():
  return concepts.ResourceSpec(
      'designcenter.projects',
      resource_name='project',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def GetProjectResourceArg(
    arg_name='project',
    help_text=None,
    positional=False,
    required=True,
):
  """Constructs and returns the Project Resource Argument."""
  help_text = help_text or 'Project ID.'
  return concept_parsers.ConceptParser.ForResource(
      '{}{}'.format('' if positional else '--', arg_name),
      GetProjectResourceSpec(),
      help_text,
      required=required,
  )


def LocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='The Cloud location for the {resource}.',
  )


def GetLocationResourceSpec():
  return concepts.ResourceSpec(
      'designcenter.projects.locations',
      resource_name='location',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def GetLocationResourceArg(
    arg_name='location',
    help_text=None,
    positional=False,
    required=True,
):
  """Constructs and returns the Location Resource Argument."""

  help_text = help_text or 'Location.'

  return concept_parsers.ConceptParser.ForResource(
      '{}{}'.format('' if positional else '--', arg_name),
      GetLocationResourceSpec(),
      help_text,
      required=required,
  )


def SpaceResourceAttributeConfig(arg_name, help_text):
  """Helper function for constructing ResourceAttributeConfig."""

  return concepts.ResourceParameterAttributeConfig(
      name=arg_name,
      help_text=help_text,
  )


def GetSpaceResourceSpec(arg_name='space', help_text=None):
  """Constructs and returns the Resource specification for Space."""

  return concepts.ResourceSpec(
      'designcenter.projects.locations.spaces',
      resource_name='space',
      spacesId=SpaceResourceAttributeConfig(arg_name, help_text),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
  )


def GetSpaceResourceArg(
    arg_name='space', help_text=None, positional=True, required=True
):
  """Constructs and returns the Space ID Resource Argument."""

  help_text = help_text or 'The Space ID.'

  return concept_parsers.ConceptParser.ForResource(
      '{}{}'.format('' if positional else '--', arg_name),
      GetSpaceResourceSpec(arg_name, help_text),
      help_text,
      required=required,
  )


# -- Revision Resource and Flags --


def CatalogAttributeConfig():
  """Creates an attribute config for the catalog."""
  return concepts.ResourceParameterAttributeConfig(
      name='catalog',
      help_text='The ID of the catalog.'
  )


def CatalogTemplateAttributeConfig():
  """Creates an attribute config for the template."""
  return concepts.ResourceParameterAttributeConfig(
      name='template',
      help_text='The ID of the template.'
  )


def GetCatalogTemplateRevisionResourceSpec():
  """Creates the resource spec for a revision."""
  return concepts.ResourceSpec(
      'designcenter.projects.locations.spaces.catalogs.templates.revisions',
      resource_name='revision',
      revisionsId=concepts.ResourceParameterAttributeConfig(
          name='revision', help_text='The ID of the revision to create.'
      ),
      templatesId=CatalogTemplateAttributeConfig(),
      catalogsId=CatalogAttributeConfig(),
      spacesId=SpaceResourceAttributeConfig('space', 'The ID of the space.'),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def AddDescribeLocationFlags(parser):
  GetLocationResourceArg(positional=True).AddToParser(parser)


def AddGetIamPolicyFlags(parser):
  GetSpaceResourceArg().AddToParser(parser)


def AddSetIamPolicyFlags(parser):
  GetSpaceResourceArg().AddToParser(parser)


def AddTestIamPermissionsFlags(parser):
  GetSpaceResourceArg().AddToParser(parser)


def AddCreateCatalogTemplateRevisionFlags(parser):
  """Adds all flags for the create revision command.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in tests.
  """
  # This defines the resource argument for the revision.
  # By using the full resource spec and a positional name ('revision'), the
  # SDK automatically creates a positional argument for the revision ID and
  # flags for all its parents (--template, --catalog, --space, etc.).
  concept_parsers.ConceptParser.ForResource(
      'revision',
      GetCatalogTemplateRevisionResourceSpec(),
      'The revision to create.',
      required=True,
  ).AddToParser(parser)
  parser.add_argument('--description', help='A description for the revision.')

  source_group = parser.add_group(mutex=True, required=True)

  dev_connect_group = source_group.add_group(
      help='Flags for Developer Connect source.'
  )
  dev_connect_group.add_argument(
      '--developer-connect-repo',
      help=(
          'The Developer Connect repository to use as a source. Example: '
          'projects/my-project/locations/us-central1/connections/my-connection/'
          'gitRepositoryLinks/my-repo'
      ),
      required=True,
  )
  dev_connect_group.add_argument(
      '--developer-connect-repo-ref',
      help=(
          'The Git ref (branch or tag) within the repository to use. Example:'
          ' "refs/tags/v1.0.0" or "refs/heads/main" or '
          '"refs/commits/269b518b99d06b31ff938a2d182e75f5e41941c7".'
      ),
      required=True,
  )
  dev_connect_group.add_argument(
      '--developer-connect-repo-dir',
      help=(
          'The directory within the repository to use. Example:'
          ' "modules/my-product"'
      ),
      required=True,
  )

  git_source_group = source_group.add_group(
      help='Flags for Git source.'
  )
  git_source_group.add_argument(
      '--git-source-repo',
      help='Git repository for Git source. Example:'
      ' GoogleCloudPlatform/terraform-google-cloud-run',
      required=True,
  )
  git_source_group.add_argument(
      '--git-source-ref-tag',
      help='Git reference tag for Git source. Example: "v1.0.0"',
      required=True,
  )
  git_source_group.add_argument(
      '--git-source-dir',
      help=(
          'Git directory for Git source. Example: "modules/my-product".'
          ' This field is optional.'
      ),
      required=False,
  )

  source_group.add_argument(
      '--application-template-revision-source',
      help=(
          'Application template revision to use as source. Example:'
          ' projects/my-project/locations/us-central1/spaces/my-space/catalogs/my-catalog/templates/my-template/revisions/r1'
      ),
      required=False,
  )

  source_group.add_argument(
      '--gcs-source-uri',
      help=(
          'Google Cloud Storage URI for source. Example:'
          ' gs://my-bucket/my-template.'
      ),
      required=False,
  )

  oci_repo_group = source_group.add_group(help='Flags for OCI Repo source.')
  oci_repo_group.add_argument(
      '--oci-repo-uri',
      help=(
          'OCI Repo URI for OCI Repo source. Example:'
          ' oci://us-west1-docker.pkg.dev/my-project/my-repo/my-chart'
      ),
      required=True,
  )
  oci_repo_group.add_argument(
      '--oci-repo-version',
      help=(
          'OCI Repo version for OCI Repo source. Example: "1.0.0". This field'
          ' is optional.'
      ),
      required=False,
  )

  parser.add_argument(
      '--metadata',
      type=arg_parsers.YAMLFileContents(),
      help=(
          'Path to a local YAML file containing the template metadata. Example:'
          ' "path/to/metadata.yaml".'
      ),
  )
