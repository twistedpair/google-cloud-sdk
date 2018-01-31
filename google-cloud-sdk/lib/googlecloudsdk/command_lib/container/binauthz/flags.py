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

import textwrap
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers


def ProviderAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='project',
      help_text='The Container Analysis provider project for the {resource}.',
  )


def NoteAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='note',
      help_text='The Container Analysis Note ID for the {resource}.',
  )


def GetNoteResourceSpec():
  return concepts.ResourceSpec(
      'containeranalysis.providers.notes',
      resource_name='note',
      providersId=ProviderAttributeConfig(),
      notesId=NoteAttributeConfig(),
  )


def GetAttestationAuthorityNoteConceptParser(group_help, required=True):

  return concept_parsers.ConceptParser.ForResource(
      name='--attestation-authority-note',
      resource_spec=GetNoteResourceSpec(),
      group_help=group_help,
      required=required,
      flag_name_overrides={
          'project': '--attestation-authority-note-project',
      },
  )


def AddArtifactUrlFlag(parser, required=True):
  parser.add_argument(
      '--artifact-url',
      required=required,
      type=str,
      help=('Container URL.  May be in the '
            '`*.gcr.io/repository/image` format, or may '
            'optionally contain the `http` or `https` scheme'))


def AddListFlags(parser):
  AddArtifactUrlFlag(parser, required=False)
  GetAttestationAuthorityNoteConceptParser(
      required=False,
      group_help=textwrap.dedent("""\
        The Container Analysis ATTESTATION_AUTHORITY Note that will be queried
        for attestations.  When this option is passed, only occurrences with
        kind ATTESTATION_AUTHORITY will be returned.  The occurrences might be
        from any project, not just the project where the note lives.  Note that
        the caller must have the `containeranalysis.notes.listOccurrences`
        permission on the note being queried.""")).AddToParser(parser)


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

  attestation_types_group = parser.add_group(
      mutex=True, help='Attestation parameters.')

  v1_attestation_group = attestation_types_group.add_group(
      help='v1 (BUILD_DETAILS) attestation parameters.')
  v1_attestation_group.add_argument(
      '--public-key-file',
      type=str,
      required=True,
      help='Path to file containing the public key to store.')

  v2_attestation_group = attestation_types_group.add_group(
      help='v2 (ATTESTATION_AUTHORITY) attestation parameters.')

  GetAttestationAuthorityNoteConceptParser(
      group_help=textwrap.dedent("""\
        The Container Analysis ATTESTATION_AUTHORITY Note that the created
        attestation will be bound to.  This note must exist and the active
        gcloud account (core/account) must have the
        `containeranalysis.notes.attachOccurrence` permission for the note
        resource (usually via the `containeranalysis.notes.attacher` role).""")
  ).AddToParser(v2_attestation_group)

  v2_attestation_group.add_argument(
      '--pgp-key-fingerprint',
      type=str,
      required=True,
      help=textwrap.dedent("""\
        The cryptographic ID of the key used to generate the signature.  For
        Binary Authorization, this must be the version 4, full 160-bit
        fingerprint, expressed as a 40 character hexidecimal string.  See
        https://tools.ietf.org/html/rfc4880#section-12.2 for details.  When
        using this argument, --attestation-authority-note must also be
        passed, while --public-key-file must not be passed."""))
