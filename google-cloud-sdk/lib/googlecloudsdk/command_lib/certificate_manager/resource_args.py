# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Shared resource flags for Certificate Manager commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def CertificateMapAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='certificate map',
      help_text='The certificate map for the {resource}.')


def CertificateAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='certificate', help_text='The certificate for the {resource}.')


def LocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='The Cloud location for the {resource}.',
      fallthroughs=[
          deps.Fallthrough(lambda: 'global', 'location is always global')
      ])


def OperationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='operation',
      help_text='Certificate Manager operation for the {resource}.')


def GetCertificateMapResourceSpec():
  return concepts.ResourceSpec(
      'certificatemanager.projects.locations.certificateMaps',
      resource_name='certificate map',
      certificateMapsId=CertificateMapAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)


def GetCertificateResourceSpec():
  return concepts.ResourceSpec(
      'certificatemanager.projects.locations.certificates',
      resource_name='certificate',
      certificatesId=CertificateAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)


def GetLocationResourceSpec():
  return concepts.ResourceSpec(
      'certificatemanager.projects.locations',
      resource_name='location',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)


def GetOperationResourceSpec():
  return concepts.ResourceSpec(
      'certificatemanager.projects.locations.operations',
      resource_name='operation',
      operationsId=OperationAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)


def AddCertificateMapResourceArg(parser, verb, noun=None, positional=True):
  """Add a resource argument for a Certificate Manager certificate map.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    noun: str, the resource; default: 'The certificate map'.
    positional: bool, if True, means that the map ID is a positional
      arg rather than a flag.
  """
  noun = noun or 'The certificate map'
  concept_parsers.ConceptParser.ForResource(
      'map' if positional else '--map',
      GetCertificateMapResourceSpec(),
      '{} {}.'.format(noun, verb),
      required=True,
      flag_name_overrides={
          'location': ''  # location is always global so don't create a flag.
      }).AddToParser(parser)


def AddCertificateResourceArg(parser, verb, noun=None, positional=True):
  """Add a resource argument for a Certificate Manager certificate.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    noun: str, the resource; default: 'The certificate'.
    positional: bool, if True, means that the certificate ID is a positional arg
      rather than a flag.
  """
  noun = noun or 'The certificate'
  concept_parsers.ConceptParser.ForResource(
      'certificate' if positional else '--certificate',
      GetCertificateResourceSpec(),
      '{} {}.'.format(noun, verb),
      required=True,
      flag_name_overrides={
          'location': ''  # location is always global so don't create a flag.
      }).AddToParser(parser)


def AddLocationResourceArg(parser, verb=''):
  """Add a resource argument for a cloud location.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  concept_parsers.ConceptParser.ForResource(
      '--location',
      GetLocationResourceSpec(),
      'The Cloud location {}.'.format(verb),
      required=True,
      flag_name_overrides={
          'location': ''  # location is always global so don't create a flag.
      }).AddToParser(parser)
