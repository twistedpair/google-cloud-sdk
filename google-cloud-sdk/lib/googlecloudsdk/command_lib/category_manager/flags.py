# -*- coding: utf-8 -*- #
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

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.projects import resource_args as project_resource_args
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs


def AddOrganizationIdArg(parser):
  """Adds 'organization' resource argument as a required CLI input."""
  concept_parsers.ConceptParser.ForResource(
      name='--organization',
      resource_spec=concepts.ResourceSpec(
          'cloudresourcemanager.organizations', resource_name='organization'),
      group_help='Your organization\'s id.',
      required=True).AddToParser(parser)


def _AssetAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='asset', help_text='An asset reference.')


def _TaxonomyAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='taxonomy', help_text='The ID of the taxonomy for the {resource}.')


def _AnnotationsAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='annotation',
      help_text='The ID of the annotation for the {resource}.')


def _GetAssetResourceSpec():
  return concepts.ResourceSpec(
      'categorymanager.assets',
      resource_name='asset',
      assetId=_AssetAttributeConfig())


def _GetProjectAnnotationResourceSpec():
  return concepts.ResourceSpec(
      'categorymanager.projects.taxonomies.annotations',
      resource_name='annotation',
      projectsId=project_resource_args.PROJECT_ATTRIBUTE_CONFIG,
      taxonomiesId=_TaxonomyAttributeConfig(),
      annotationsId=_AnnotationsAttributeConfig())


def _GetProjectTaxonomyResourceSpec():
  return concepts.ResourceSpec(
      'categorymanager.projects.taxonomies',
      resource_name='taxonomy',
      projectsId=project_resource_args.PROJECT_ATTRIBUTE_CONFIG,
      taxonomiesId=_TaxonomyAttributeConfig())


def CreateAnnotationResourceArg(plural=False, positional=False, required=True):
  name = 'annotation'
  help_text = 'An annotation reference.'
  if plural:
    name = 'annotations'
    help_text = 'A comma separated list of annotation references.'
  return presentation_specs.ResourcePresentationSpec(
      name if positional else ('--' + name),
      _GetProjectAnnotationResourceSpec(),
      help_text,
      plural=plural,
      prefixes=False,
      required=required)


def CreateTaxonomyResourceArg(positional=False):
  return presentation_specs.ResourcePresentationSpec(
      'taxonomy' if positional else '--taxonomy',
      _GetProjectTaxonomyResourceSpec(),
      'A taxonomy reference.',
      required=True,
      prefixes=False)


def CreateAssetResourceArg(positional=False):
  return presentation_specs.ResourcePresentationSpec(
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


def AddDisplayNameFlag(parser, resource, required=True):
  help_text = 'A human-readable name for the {}.'.format(resource)
  parser.add_argument('--display-name', help=help_text, required=required)


def AddDescriptionFlag(parser, resource, required=True):
  help_text = 'A human-readable description of the {}.'.format(resource)
  parser.add_argument('--description', help=help_text, required=required)


def AddParentAnnotationFlag(parser):
  help_text = ('The ID of the parent annotation for this annotation. If not '
               'given, this annotation will be at the root of the hierarchy.')
  parser.add_argument('--parent-annotation', help=help_text, required=False)


def AddMatchChildAnnotationsFlag(parser, hidden=False):
  help_text = """\
  For any annotation with child annotations, also list assets that are
  annotated by those child annotations."""
  parser.add_argument(
      '--match-child-annotations',
      help=help_text,
      action='store_false',
      hidden=hidden)


def AddShowOnlyAnnotatableFlag(parser, hidden=False):
  help_text = 'Display only assets that are annotatable.'
  parser.add_argument(
      '--show-only-annotatable',
      action='store_false',
      hidden=hidden,
      help=help_text)


def AddQueryFilterFlag(parser):
  """Adds query filter string as a CLI argument."""
  help_text = """\
  Query string in the search language described below (if not given, shows all
  assets that this user can read).

  Language Qualifiers:

  * `name:x` Matches x as a substring on the name of the entity.

  * `desc:y` Matches y as a substring on the description of an entity.

  * `project_id:bar` Matches entities associated with Cloud project ID
    containing bar as a substring.

  * `project_number:bar` Matches entities associated with Cloud project number
    bar.

  * `org_id:bar` Matches entities whose org ID is bar, e.g.: org_id:11111.

  * `create_time:2017-01-01` Matches entries whose underlying file's create time
    is on 2017-01-01.

  * `create_time:2009...2010-02-10` Matches entries whose underlying file's
    create time is within [2009-01-01T00:00:00, 2010-02-10T00:00:00).

  * `create_time < 2017-02` Matches entries whose underlying file's create time
    is before 2017-02-01T00:00:00.

  * `create_time > 2011-05-16T073000` Matches entries whose underlying file's
    create time is after 2011-05-16T07:30:00.

  * `last_modify_time:2017-01-01` Matches entries whose last modified timestamp
    is on 2017-01-01.

  * `last_modify_time:2009...2010-02-10` Matches entries whose
    last_modify_time is within [2009-01-01T00:00:00, 2010-02-10T00:00:00).

  * `last_modify_time < 2017-02` Matches entries whose last_modify_time is
    before 2017-02-01T00:00:00.

  * `last_modify_time > 2011-05-16T073000` Matches entries whose
    last_modify_time is after 2011-05-16T07:30:00.

  You can also use `=` instead of `:` to express equality instead of
  fuzzy matching. For example, `name=x` matches entities where one of
  the names is exactly `x`.

  The search language also supports logical operators `OR` and
  `AND` to join predicates together. By default if no operator is
  specified, then logical AND is implied.

  You can also negate a predicate by prefixing it with -. For example,
  -name:foo returns all entities whose names does not match the
  predicate foo. Alternatively, you can use NOT instead of - for
  negation.

  ## EXAMPLES:

  Search for all assets created from Jan 1st 2018 to Jan 1st 2019:

    $ gcloud alpha category-manager assets search "create_time > 2018-01-01 AND create_time < 2019-01-01"

  Search for all assets with the name 'foo' or contain 'bar' in their
  description:

      $ gcloud alpha category-manager assets search "name=foo OR desc:bar"

  Search for all assets part of the organization with id 123 and the
  project id company.com:abc-456 modified after Dec 2018:

      $ gcloud alpha category-manager assets search "org_id=123 project_id=company.com:abc-456 last_modify_time>2018-12"
  """
  parser.add_argument('query', help=help_text, default='', nargs='?')
