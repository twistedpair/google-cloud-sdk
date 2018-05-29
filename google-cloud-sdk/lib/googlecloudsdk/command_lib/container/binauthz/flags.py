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
"""Flags for binauthz command group."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import textwrap

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties


def _GetNoteResourceSpec():
  return concepts.ResourceSpec(
      'containeranalysis.projects.notes',
      resource_name='note',
      projectsId=concepts.ResourceParameterAttributeConfig(
          name='project',
          help_text=(
              'The Container Analysis project for the {resource}.'),
      ),
      notesId=concepts.ResourceParameterAttributeConfig(
          name='note',
          help_text='The Container Analysis Note ID for the {resource}.',
      )
  )


def _FormatArgName(base_name, positional):
  if positional:
    return base_name.replace('-', '_').upper()
  else:
    return '--' + base_name.replace('_', '-').lower()


def GetAuthorityNotePresentationSpec(base_name,
                                     group_help,
                                     required=True,
                                     positional=True):
  return concept_parsers.ResourcePresentationSpec(
      name=_FormatArgName(base_name, positional),
      concept_spec=_GetNoteResourceSpec(),
      group_help=group_help,
      required=required,
      flag_name_overrides={
          'project': _FormatArgName('{}-project'.format(base_name), positional),
      },
  )


def _GetAuthorityResourceSpec():
  return concepts.ResourceSpec(
      'binaryauthorization.projects.attestationAuthorities',
      resource_name='authority',
      projectsId=concepts.ResourceParameterAttributeConfig(
          name='project',
          help_text='The project of the {resource}.',
          fallthroughs=[
              deps.PropertyFallthrough(properties.VALUES.core.project)],
      ),
      attestationAuthoritiesId=concepts.ResourceParameterAttributeConfig(
          name='name',
          help_text='The ID of the {resource}.',
      )
  )


def GetAuthorityPresentationSpec(group_help,
                                 required=True,
                                 positional=True):
  return concept_parsers.ResourcePresentationSpec(
      name=_FormatArgName('authority', positional),
      concept_spec=_GetAuthorityResourceSpec(),
      group_help=group_help,
      required=required,
  )


def AddConcepts(parser, *presentation_specs):
  concept_parsers.ConceptParser(presentation_specs).AddToParser(parser)


def AddArtifactUrlFlag(parser, required=True):
  parser.add_argument(
      '--artifact-url',
      required=required,
      type=str,
      help=('Container URL.  May be in the '
            '`*.gcr.io/repository/image` format, or may '
            'optionally contain the `http` or `https` scheme'))


def AddListAttestationsFlags(parser):
  AddArtifactUrlFlag(parser, required=False)
  AddConcepts(
      parser,
      GetAuthorityNotePresentationSpec(
          base_name='attestation-authority-note',
          required=False,
          positional=False,
          group_help=textwrap.dedent("""\
            The Container Analysis ATTESTATION_AUTHORITY Note that will be
            queried for attestations.  When this option is passed, only
            occurrences with kind ATTESTATION_AUTHORITY will be returned.  The
            occurrences might be from any project, not just the project where
            the note lives.  Note that the caller must have the
            `containeranalysis.notes.listOccurrences` permission on the note
            being queried.""")
      )
  )


def AddCreateAttestationFlags(parser):
  """Flags for Binary Authorization signature management."""

  AddArtifactUrlFlag(parser)
  parser.add_argument(
      '--signature-file',
      required=True,
      type=str,
      help=textwrap.dedent("""\
        Path to file containing the signature to store, or `-` to read signature
        from stdin."""))

  AddConcepts(
      parser,
      GetAuthorityNotePresentationSpec(
          base_name='attestation-authority-note',
          positional=False,
          group_help=textwrap.dedent("""\
            The Container Analysis ATTESTATION_AUTHORITY Note that the created
            attestation will be bound to.  This note must exist and the active
            gcloud account (core/account) must have the
            `containeranalysis.notes.attachOccurrence` permission for the note
            resource (usually via the `containeranalysis.notes.attacher`
            role).""")
      )
  )

  parser.add_argument(
      '--pgp-key-fingerprint',
      type=str,
      required=True,
      help=textwrap.dedent("""\
        The cryptographic ID of the key used to generate the signature.  For
        Binary Authorization, this must be the version 4, full 160-bit
        fingerprint, expressed as a 40 character hexidecimal string.  See
        https://tools.ietf.org/html/rfc4880#section-12.2 for details."""))
