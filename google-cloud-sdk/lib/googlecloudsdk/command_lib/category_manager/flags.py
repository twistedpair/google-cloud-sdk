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
"""Helpers for commandline flags in Cloud Category Manager."""

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties


def AddOrganizationIdArg(parser):
  """Adds 'organization_id' argument as a required CLI input."""
  concept_parsers.ConceptParser.ForResource(
      name='organization_id',
      resource_spec=concepts.ResourceSpec('cloudresourcemanager.organizations'),
      group_help='Your organization\'s id.',
      required=True).AddToParser(parser)


def _AssetAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='asset', help_text='An asset reference.')


def _ProjectAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='project',
      help_text='The Cloud project for the {resource}.',
      fallthroughs=[deps.PropertyFallthrough(properties.VALUES.core.project)])


def _TaxonomyAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='taxonomy', help_text='The ID of the taxonomy.')


def _AnnotationsAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='annotation', help_text='The ID of the annotation.')


def _GetAssetResourceSpec():
  return concepts.ResourceSpec(
      'categorymanager.assets',
      resource_name='asset',
      assetId=_AssetAttributeConfig())


def _GetProjectAnnotationResourceSpec():
  return concepts.ResourceSpec(
      'categorymanager.projects.taxonomies.annotations',
      resource_name='annotation',
      projectsId=_ProjectAttributeConfig(),
      taxonomiesId=_TaxonomyAttributeConfig(),
      annotationsId=_AnnotationsAttributeConfig())


def CreateAnnotationResourceArg(positional=False):
  return concept_parsers.ResourcePresentationSpec(
      'annotation' if positional else '--annotation',
      _GetProjectAnnotationResourceSpec(),
      'An annotation reference.',
      required=True,
      prefixes=False)


def CreateAssetResourceArg(positional=False):
  return concept_parsers.ResourcePresentationSpec(
      'asset' if positional else '--asset',
      _GetAssetResourceSpec(),
      group_help='The asset reference.',
      required=True,
      prefixes=False)


def AddSubAssetFlag(parser, hidden=False):
  help_text = """\
  The name of the sub-asset to apply an annotation to. For instance, for
          Google Cloud Bigquery, this is the name of the column in the table
          (which is the asset). """
  parser.add_argument('--sub-asset', help=help_text, hidden=hidden)
