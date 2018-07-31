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

"""Common flags for Kubernetes Managed Namespace commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.projects import resource_args as project_resource_args
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties


def GetKubernetesName():
  return base.Argument(
      'kubernetes_name',
      help='A human friendly name, unique per environment, that will be the '
           'name of the namespace created in each of the clusters.')


def GetProjectResourceName():
  project_id = properties.VALUES.core.project.GetOrFail()
  return 'projects/{0}'.format(project_id)


def NamespaceAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='namespace',
      help_text='The namespace id for the {resource}.')


def GetNamespaceResourceSpec():
  return concepts.ResourceSpec(
      'kubernetespolicy.projects.namespaces',
      resource_name='namespace',
      namespacesId=NamespaceAttributeConfig(),
      projectsId=project_resource_args.PROJECT_ATTRIBUTE_CONFIG)


def AddNamespaceResourceArg(parser, verb):
  """Add a resource argument for a Kubernetes Managed Namespace.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to create'.
  """
  concept_parsers.ConceptParser.ForResource(
      'namespace',
      GetNamespaceResourceSpec(),
      'The namespace {}.'.format(verb),
      required=True,
      prefixes=False).AddToParser(parser)

