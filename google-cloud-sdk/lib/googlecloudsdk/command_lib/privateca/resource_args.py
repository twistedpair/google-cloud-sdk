# Lint as: python3
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
"""Helpers for parsing resource arguments."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def ReusableConfigAttributeConfig():
  # ReusableConfig is always an anchor attribute so help_text is unused.
  return concepts.ResourceParameterAttributeConfig(name='reusableConfig')


def CertificateAttributeConfig():
  # Certificate is always an anchor attribute so help_text is unused.
  return concepts.ResourceParameterAttributeConfig(name='certificate')


def CertificateAuthorityAttributeConfig(arg_name='certificate-authority'):
  return concepts.ResourceParameterAttributeConfig(
      name=arg_name,
      help_text='The issuing certificate authority of the {resource}')


def LocationAttributeConfig(arg_name='location'):
  return concepts.ResourceParameterAttributeConfig(
      name=arg_name, help_text='The location of the {resource}.')


def CreateReusableConfigResourceSpec(arg_name):
  return concepts.ResourceSpec(
      'privateca.projects.locations.reusableConfigs',
      # This will be formatted and used as {resource} in the help text.
      resource_name=arg_name,
      resourceConfigsId=ReusableConfigAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)


def CreateCertificateAuthorityResourceSpec(arg_name):
  return concepts.ResourceSpec(
      'privateca.projects.locations.certificateAuthorities',
      # This will be formatted and used as {resource} in the help text.
      resource_name=arg_name,
      certificateAuthoritiesId=CertificateAuthorityAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)


def CreateCertificateResourceSpec(arg_name):
  return concepts.ResourceSpec(
      'privateca.projects.locations.certificateAuthorities.certificates',
      # This will be formatted and used as {resource} in the help text.
      resource_name=arg_name,
      certificatesId=CertificateAttributeConfig(),
      certificateAuthoritiesId=CertificateAuthorityAttributeConfig('issuer'),
      locationsId=LocationAttributeConfig('issuer-location'),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)


def AddCertificateAuthorityPositionalResourceArg(parser, verb):
  """Add a positional resource argument for a Certificate Authority.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  arg_name = 'CERTIFICATE_AUTHORITY'
  concept_parsers.ConceptParser.ForResource(
      arg_name,
      CreateCertificateAuthorityResourceSpec(arg_name),
      'The certificate authority {}.'.format(verb),
      required=True).AddToParser(parser)


def AddCertificatePositionalResourceArg(parser, verb):
  """Add a positional resource argument for a Certificate.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  arg_name = 'CERTIFICATE'
  concept_parsers.ConceptParser.ForResource(
      arg_name,
      CreateCertificateResourceSpec(arg_name),
      'The certificate {}.'.format(verb),
      required=True).AddToParser(parser)
