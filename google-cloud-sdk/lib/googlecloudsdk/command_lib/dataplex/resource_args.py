# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Shared resource args for the Dataplex surface."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties


GENERATE_ID = '@%!#DATAPLEX_GENERATE_UUID@%!#'


def GetProjectSpec():
  """Gets Project spec."""
  return concepts.ResourceSpec(
      'dataplex.projects',
      resource_name='projects',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def GetLakeResourceSpec():
  """Gets Lake resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.lakes',
      resource_name='lakes',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      lakesId=LakeAttributeConfig(),
  )


def GetZoneResourceSpec():
  """Gets Zone resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.lakes.zones',
      resource_name='zones',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      lakesId=LakeAttributeConfig(),
      zonesId=ZoneAttributeConfig(),
  )


def GetAssetResourceSpec():
  """Gets Asset resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.lakes.zones.assets',
      resource_name='assets',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      lakesId=LakeAttributeConfig(),
      zonesId=ZoneAttributeConfig(),
      assetsId=AssetAttributeConfig(),
  )


def GetContentitemResourceSpec():
  """Gets Content resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.lakes.contentitems',
      resource_name='content',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      lakesId=LakeAttributeConfig(),
      contentitemsId=ContentAttributeConfig(),
  )


def GetTaskResourceSpec():
  """Gets Task resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.lakes.tasks',
      resource_name='tasks',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      lakesId=LakeAttributeConfig(),
      tasksId=TaskAttributeConfig(),
  )


def GetEnvironmentResourceSpec():
  """Gets Environment resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.lakes.environments',
      resource_name='environments',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      lakesId=LakeAttributeConfig(),
      environmentsId=EnvironmentAttributeConfig(),
  )


def GetDatascanResourceSpec():
  """Gets Datascan resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.dataScans',
      resource_name='datascan',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      dataScansId=DatascanAttributeConfig(),
  )


def GetDataTaxonomyResourceSpec():
  """Gets DataTaxonomy resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.dataTaxonomies',
      resource_name='data taxonomy',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      dataTaxonomiesId=DataTaxonomyAttributeConfig(),
  )


def GetDataAttributeBindingResourceSpec():
  """Gets DataAttributeBinding resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.dataAttributeBindings',
      resource_name='data attribute binding',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      dataAttributeBindingsId=DataAttributeBindingAttributeConfig(),
  )


def GetDataAttributeResourceSpec():
  """Gets Data Attribute resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.dataTaxonomies.attributes',
      resource_name='data attribute',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      dataTaxonomiesId=DataTaxonomyAttributeConfig(),
      attributesId=DataAttributeConfig(),
  )


def GetDataplexEntryGroupResourceSpec():
  """Gets Entry Group resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.entryGroups',
      resource_name='entry group',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      entryGroupsId=EntryGroupAttributeConfig(),
  )


def GetDataplexAspectTypeResourceSpec():
  """Gets Aspect Type resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.aspectTypes',
      resource_name='aspect type',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      aspectTypesId=AspectTypeAttributeConfig(),
  )


def GetDataplexEntryTypeResourceSpec():
  """Gets Entry Type resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.entryTypes',
      resource_name='entry type',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      entryTypesId=EntryTypeAttributeConfig(),
  )


def GetEntryTypeResourceSpec():
  """Gets EntryType resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.entryTypes',
      resource_name='entry type',
      projectsId=EntryTypeProjectAttributeConfig(),
      locationsId=EntryTypeLocationAttributeConfig(),
      entryTypesId=EntryTypeConfig(),
  )


def GetDataplexEntryLinkResourceSpec():
  """Gets Entry Link resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.entryGroups.entryLinks',
      resource_name='entry link',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      entryGroupsId=EntryGroupAttributeConfig(),
      entryLinksId=EntryLinkAttributeConfig(),
  )


def GetGovernanceRuleResourceSpec():
  """Gets GovernanceRule resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.governanceRules',
      resource_name='governance rule',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      governanceRulesId=GovernanceRuleAttributeConfig(),
  )


def GetGlossaryResourceSpec():
  """Gets Glossary resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.glossaries',
      resource_name='glossary',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      glossariesId=GlossaryAttributeConfig(),
  )


def GetGlossaryCategoryResourceSpec():
  """Gets Glossary Category resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.glossaries.categories',
      resource_name='glossary category',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      glossariesId=GlossaryAttributeConfig(),
      categoriesId=GlossaryCategoryAttributeConfig(),
  )


def GetGlossaryTermResourceSpec():
  """Gets Glossary Term resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.glossaries.terms',
      resource_name='glossary term',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      glossariesId=GlossaryAttributeConfig(),
      termsId=GlossaryTermAttributeConfig(),
  )


def GetMetadataJobResourceSpec():
  """Gets Metadata Job resource spec."""
  return concepts.ResourceSpec(
      'dataplex.projects.locations.metadataJobs',
      resource_name='metadata job',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=LocationAttributeConfig(),
      metadataJobsId=MetadataJobAttributeConfig(),
  )


def GetEncryptionConfigResourceSpec():
  """Gets EncryptionConfig resource spec."""
  return concepts.ResourceSpec(
      'dataplex.organizations.locations.encryptionConfigs',
      resource_name='encryption config',
      organizationsId=OrganizationAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      encryptionConfigsId=EncryptionConfigAttributeConfig(),
  )


def EntryTypeProjectAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='entry-type-project',
      help_text='The project of the EntryType resource.',
  )


def EntryTypeLocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='entry-type-location',
      help_text='The location of the EntryType resource.',
  )


def LocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      fallthroughs=[
          deps.PropertyFallthrough(properties.FromString('dataplex/location'))
      ],
      help_text='The location of the Dataplex resource.',
  )


def LakeAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='lake', help_text='The identifier of the Dataplex lake resource.'
  )


def ZoneAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='zone', help_text='The identifier of the Dataplex zone resource.'
  )


def AssetAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='asset', help_text='The identifier of the Dataplex asset resource.'
  )


def ContentAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='content', help_text='The name of the {resource} to use.'
  )


def EnvironmentAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='environment', help_text='The name of {resource} to use.'
  )


def DataTaxonomyAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='data_taxonomy', help_text='The name of {resource} to use.'
  )


def DataAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='data_attribute', help_text='The name of {resource} to use.'
  )


def DataAttributeBindingAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='data_attribute_binding', help_text='The name of {resource} to use.'
  )


def EntryGroupAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='entry-group', help_text='The name of {resource} to use.'
  )


def AspectTypeAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='aspect_type', help_text='The name of {resource} to use.'
  )


def EntryTypeAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='entry_type', help_text='The name of {resource} to use.'
  )


def EntryLinkAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='entry-link', help_text='The name of {resource} to use.'
  )


def DatascanAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='dataScans', help_text='The name of {resource} to use.'
  )


def EntryTypeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='entry_type', help_text='The name of {resource} to use.'
  )


def GovernanceRuleAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='governance_rule', help_text='The name of {resource} to use.'
  )


def GlossaryAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='glossary', help_text='The name of {resource} to use.'
  )


def GlossaryCategoryAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='glossary_category', help_text='The name of {resource} to use.'
  )


def GlossaryTermAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='glossary_term', help_text='The name of {resource} to use.'
  )


def MetadataJobAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='metadata_job',
      # Adding invalid job_id to keep job resource in the right format,
      # this invalid value will be removed if no job_id is specified from
      # the input and the underlaying client would generate a valid one.
      fallthroughs=[
          deps.ValueFallthrough(
              GENERATE_ID,
              hint='job ID is optional and will be generated if not specified',
          )
      ],
      help_text='The name of {resource} to use.',
  )


def EncryptionConfigAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='encryption_config', help_text='The name of {resource} to use.'
  )


def OrganizationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='organization', help_text='The name of {resource} to use.'
  )


def AddDatascanResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Datascan."""
  name = 'datascan' if positional else '--datascan'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetDatascanResourceSpec(),
      'Arguments and flags that define the Dataplex datascan you want {}'
      .format(verb),
      required=True,
  ).AddToParser(parser)


def AddProjectArg(parser, verb, positional=True):
  """Adds a resource argument for a project."""
  name = 'project' if positional else '--project'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetProjectSpec(),
      'Arguments and flags that define the project you want {}'.format(verb),
      required=True,
  ).AddToParser(parser)


def TaskAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='task', help_text='The identifier of the Dataplex task resource.'
  )


def AddLakeResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Lake."""
  name = 'lake' if positional else '--lake'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetLakeResourceSpec(),
      'Arguments and flags that define the Dataplex lake you want {}'.format(
          verb
      ),
      required=True,
  ).AddToParser(parser)


def AddZoneResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Zone."""
  name = 'zone' if positional else '--zone'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetZoneResourceSpec(),
      'Arguments and flags that define the Dataplex zone you want {}'.format(
          verb
      ),
      required=True,
  ).AddToParser(parser)


def AddAssetResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Asset."""
  name = 'asset' if positional else '--asset'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetAssetResourceSpec(),
      'Arguments and flags that define the Dataplex asset you want {}'.format(
          verb
      ),
      required=True,
  ).AddToParser(parser)


def AddContentitemResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Content."""
  name = 'content' if positional else '--content'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetContentitemResourceSpec(),
      'The Content {}'.format(verb),
      required=True,
  ).AddToParser(parser)


def AddTaskResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Task."""
  name = 'task' if positional else '--task'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetTaskResourceSpec(),
      'Arguments and flags that define the Dataplex task you want {}'.format(
          verb
      ),
      required=True,
  ).AddToParser(parser)


def AddEnvironmentResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Environment."""
  name = 'environment' if positional else '--environment'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetEnvironmentResourceSpec(),
      'The Environment {}'.format(verb),
      required=True,
  ).AddToParser(parser)


def AddDataTaxonomyResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Data Taxonomy."""
  name = 'data_taxonomy' if positional else '--data_taxonomy'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetDataTaxonomyResourceSpec(),
      'The DataTaxonomy {}'.format(verb),
      required=True,
  ).AddToParser(parser)


def AddAttributeResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Attribute."""
  name = 'data_attribute' if positional else '--data_attribute'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetDataAttributeResourceSpec(),
      'The DataAttribute {}'.format(verb),
      required=True,
  ).AddToParser(parser)


def AddDataAttributeBindingResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex DataAttributeBinding."""
  name = 'data_attribute_binding' if positional else '--data_attribute_binding'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetDataAttributeBindingResourceSpec(),
      'The DataAttributeBinding {}'.format(verb),
      required=True,
  ).AddToParser(parser)


def AddDataplexEntryGroupResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex EntryGroup."""
  name = 'entry_group' if positional else '--entry-group'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetDataplexEntryGroupResourceSpec(),
      'Arguments and flags that define the Dataplex entry group you want {}'
      .format(verb),
      required=True,
  ).AddToParser(parser)


def AddDataplexAspectTypeResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex AspectType."""
  name = 'aspect_type' if positional else '--aspect_type'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetDataplexAspectTypeResourceSpec(),
      'Arguments and flags that define the Dataplex aspect type you want {}'
      .format(verb),
      required=True,
  ).AddToParser(parser)


def AddDataplexEntryTypeResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex EntryType."""
  name = 'entry_type' if positional else '--entry_type'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetDataplexEntryTypeResourceSpec(),
      'Arguments and flags that define the Dataplex entry type you want {}'
      .format(verb),
      required=True,
  ).AddToParser(parser)


def AddEntryTypeResourceArg(parser):
  """Adds a resource argument for a Dataplex EntryType."""
  return concept_parsers.ConceptParser.ForResource(
      '--entry-type',
      GetEntryTypeResourceSpec(),
      'Arguments and flags that define the Dataplex EntryType you want to'
      ' reference.',
      required=True,
  ).AddToParser(parser)


def AddEntryResourceArg(parser):
  """Adds a resource argument for a Dataplex Entry."""
  entry_data = yaml_data.ResourceYAMLData.FromPath('dataplex.entry')
  return concept_parsers.ConceptParser.ForResource(
      'entry',
      concepts.ResourceSpec.FromYaml(entry_data.GetData(), is_positional=True),
      'Arguments and flags that define the Dataplex Entry you want to'
      ' reference.',
      required=True,
  ).AddToParser(parser)


def AddDataplexEntryLinkResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex EntryLink."""
  name = 'entry_link' if positional else '--entry-link'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetDataplexEntryLinkResourceSpec(),
      'Arguments and flags that define the Dataplex entry link you want {}'
      .format(verb),
      required=True,
  ).AddToParser(parser)


def AddGovernanceRuleResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex GovernanceRule."""
  name = 'governance_rule' if positional else '--governance_rule'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetGovernanceRuleResourceSpec(),
      'Arguments and flags that define the Dataplex governance rule you want {}'
      .format(verb),
      required=True,
  ).AddToParser(parser)


def AddGlossaryResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Glossary."""
  name = 'glossary' if positional else '--glossary'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetGlossaryResourceSpec(),
      'Arguments and flags that define the Dataplex Glossary you want {}'
      .format(verb),
      required=True,
  ).AddToParser(parser)


def AddGlossaryCategoryResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Glossary Category."""
  name = 'glossary_category' if positional else '--glossary_category'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetGlossaryCategoryResourceSpec(),
      'Arguments and flags that define the Dataplex Glossary Category you'
      ' want {}'.format(verb),
      required=True,
  ).AddToParser(parser)


def AddGlossaryTermResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex Glossary Term."""
  name = 'glossary_term' if positional else '--glossary_term'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetGlossaryTermResourceSpec(),
      'Arguments and flags that define the Dataplex Glossary Term you'
      ' want {}'.format(verb),
      required=True,
  ).AddToParser(parser)


def AddEncryptionConfigResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex EncryptionConfig."""
  name = 'encryption_config' if positional else '--encryption_config'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetEncryptionConfigResourceSpec(),
      'Arguments and flags that define the Dataplex EncryptionConfig you'
      ' want {}'.format(verb),
      required=True,
  ).AddToParser(parser)


def AddParentEntryResourceArg(parser):
  """Adds a resource argument for a Dataplex Entry parent."""
  entry_data = yaml_data.ResourceYAMLData.FromPath('dataplex.entry')
  return concept_parsers.ConceptParser.ForResource(
      '--parent-entry',
      concepts.ResourceSpec.FromYaml(entry_data.GetData()),
      'Arguments and flags that define the parent Entry you want to reference.',
      # Parent Entry has to belong to the same EntryGroup as the Entry,
      # therefore we disable the location and entry_group flags for the parent
      # entry resource and set fallthrougs to use the same location and
      # entry_group as for the Entry.
      command_level_fallthroughs={
          'location': ['--location'],
          'entry_group': ['--entry_group'],
      },
      flag_name_overrides={
          'location': '',
          'entry_group': '',
      },
  ).AddToParser(parser)


def AddMetadataJobResourceArg(parser, verb, positional=True):
  """Adds a resource argument for a Dataplex MetadataJob."""
  name = 'metadata_job' if positional else '--metadata_job'
  return concept_parsers.ConceptParser.ForResource(
      name,
      GetMetadataJobResourceSpec(),
      'Arguments and flags that define the Dataplex metdata job you want {}'
      .format(verb),
      required=True,
  ).AddToParser(parser)
