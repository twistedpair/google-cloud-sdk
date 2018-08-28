# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Flags for workflow templates related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.projects import resource_args as project_resource_args
from googlecloudsdk.command_lib.util import completers
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties


def AddZoneFlag(parser):
  parser.add_argument(
      '--zone',
      '-z',
      help="""
          The compute zone (e.g. us-central1-a) for the cluster. If empty,
          and --region is set to a value other than 'global', the server will
          pick a zone in the region.
          """,
      action=actions.StoreProperty(properties.VALUES.compute.zone))


def AddVersionFlag(parser):
  parser.add_argument(
      '--version', type=int, help='The version of the workflow template.')


def AddFileFlag(parser, input_type, action):
  # Examples: workflow template to run/export/import, cluster to create.
  parser.add_argument(
      '--file',
      help='The YAML file containing the {0} to {1}'.format(input_type, action),
      required=True)


def AddTemplateSourceFlag(parser):
  parser.add_argument(
      '--source',
      help="""The path to a YAML file containing a Dataproc WorkflowTemplate
      resource. The provided YAML file must not contain id, version, or any
      output-only fields.
      Alternatively, you may omit this flag to read from the standard input.
      For more information, see:
      https://cloud.google.com/dataproc/docs/reference/rest/v1beta2/projects.locations.workflowTemplates#WorkflowTemplate
      """,
      # Allow reading from stdin.
      required=False)


def AddTemplateDestinationFlag(parser):
  parser.add_argument(
      '--destination',
      help=
      """The path to a YAML file to which the Dataproc WorkflowTemplate resource
      will be exported. The exported template will not contain id, version, or
      any output-only fields.
      Alternatively, you may omit this flag to write to the standard output.
      For more information, see:
      https://cloud.google.com/dataproc/docs/reference/rest/v1beta2/projects.locations.workflowTemplates#WorkflowTemplate
      """,
      # Allow writing to stdout.
      required=False)


def AddJobFlag(parser, action):
  parser.add_argument(
      'job', help='The ID of the job to {0}.'.format(action))


def AddOperationFlag(parser, action):
  parser.add_argument(
      'operation', help='The ID of the operation to {0}.'.format(action))


def AddTimeoutFlag(parser, default='10m'):
  # This may be made visible or passed to the server in future.
  parser.add_argument(
      '--timeout',
      type=arg_parsers.Duration(),
      default=default,
      help=('Client side timeout on how long to wait for Datproc operations. '
            'See $ gcloud topic datetimes for information on duration '
            'formats.'),
      hidden=True)


def AddParametersFlag(parser):
  parser.add_argument(
      '--parameters',
      metavar='PARAM=VALUE',
      type=arg_parsers.ArgDict(),
      help="""
          A map from parameter names to values that should be used for those
          parameters. A value must be provided for every configured parameter.
          Parameters can be configured when creating or updating a workflow
          template.
          """,
      dest='parameters')


def AddMinCpuPlatformArgs(parser, track):
  """Add mininum CPU platform flags for both master and worker instances."""
  help_text = """\
      When specified, the VM will be scheduled on host with specified CPU
      architecture or a newer one. To list available CPU platforms in given
      zone, run:

          $ gcloud {}compute zones describe ZONE

      CPU platform selection is available only in selected zones; zones that
      allow CPU platform selection will have an `availableCpuPlatforms` field
      that contains the list of available CPU platforms for that zone.

      You can find more information online:
      https://cloud.google.com/compute/docs/instances/specify-min-cpu-platform
      """.format(track.prefix + ' ' if track.prefix else '')
  parser.add_argument(
      '--master-min-cpu-platform',
      metavar='PLATFORM',
      required=False,
      help=help_text)
  parser.add_argument(
      '--worker-min-cpu-platform',
      metavar='PLATFORM',
      required=False,
      help=help_text)


def AddComponentFlag(parser):
  """Add optional components flag."""
  help_text = """\
      List of optional components to be installed on cluster machines.

      The following page documents the optional components that can be
      installed.
      https://cloud.google.com/dataproc/docs/concepts/configuring-clusters/optional-components.
      """
  parser.add_argument(
      '--optional-components',
      metavar='COMPONENT',
      type=arg_parsers.ArgList(element_type=lambda val: val.upper()),
      dest='components',
      hidden=True,
      help=help_text)


class RegionsCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(RegionsCompleter, self).__init__(
        collection='dataproc.projects.regions',
        list_command='alpha dataproc regions list --uri',
        **kwargs)


def TemplateAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='template',
      help_text='The workflow template name.',
  )


def RegionAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='region',
      help_text=(
          'The Cloud DataProc region for the {resource}. Each Cloud Dataproc '
          'region constitutes an independent resource namespace constrained to '
          'deploying instances into Google Compute Engine zones inside the '
          'region. The default value of "global" is a special multi-region '
          'namespace which is capable of deploying instances into all Google '
          'Compute Engine zones globally, and is disjoint from other Cloud '
          'Dataproc regions. Overrides the default `dataproc/region` property '
          'value for this command invocation.'),
      completer=RegionsCompleter,
      fallthroughs=[
          deps.PropertyFallthrough(properties.VALUES.dataproc.region),
      ],
  )


def GetTemplateResourceSpec():
  return concepts.ResourceSpec(
      'dataproc.projects.regions.workflowTemplates',
      api_version='v1beta2',
      resource_name='template',
      disable_auto_completers=False,
      projectsId=project_resource_args.PROJECT_ATTRIBUTE_CONFIG,
      regionsId=RegionAttributeConfig(),
      workflowTemplatesId=TemplateAttributeConfig(),
  )


def AddTemplateResourceArg(parser, verb, positional=True):
  """Adds a workflow template resource argument.

  Args:
    parser: the argparse parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    positional: bool, if True, means that the instance ID is a positional rather
      than a flag.
  """
  name = 'TEMPLATE' if positional else '--template'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetTemplateResourceSpec(),
      'The name of the workflow template to {}.'.format(verb),
      required=True).AddToParser(parser)
