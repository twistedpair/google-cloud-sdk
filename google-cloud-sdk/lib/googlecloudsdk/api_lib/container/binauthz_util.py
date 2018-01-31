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
"""Utilities to access containeranalysis for binary authorization."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis


DEFAULT_CONTAINERANALYSIS_API_VERSION = 'v1alpha1'
DEFAULT_CONTAINERANALYSIS_API_NAME = 'containeranalysis'


class ContainerAnalysisClient(object):
  """A client to access containeranalysis for binauthz purposes.

  This client only deals with v2 attestations, which are Notes and
  Occurrences with kind ATTESTATION_AUTHORITY.
  """

  def __init__(self, client=None, messages=None):
    """Creates a ContainerAnalysisClient.

    If client or messages are unspecified, then the default instances are used.

    Args:
      client: containeranalyisis client
      messages: containeranalysis messages
    """
    self.client = (
        client or apis.GetClientInstance(
            DEFAULT_CONTAINERANALYSIS_API_NAME,
            DEFAULT_CONTAINERANALYSIS_API_VERSION,
        ))
    self.messages = (
        messages or apis.GetMessagesModule(
            DEFAULT_CONTAINERANALYSIS_API_NAME,
            DEFAULT_CONTAINERANALYSIS_API_VERSION,
        ))

    self.simple_signing_json = (
        self.messages.PgpSignedAttestation.ContentTypeValueValuesEnum.
        SIMPLE_SIGNING_JSON)
    self.attestation_authority = (
        self.messages.Occurrence.KindValueValuesEnum.ATTESTATION_AUTHORITY)

  def _YieldNoteOccurrences(self, note_ref, artifact_url=None):
    """Yields occurrences associated with given AA Note.

    Args:
      note_ref: The Note reference that will be queried for attached
        occurrences. (containeranalysis.providers.notes Resource)
      artifact_url: URL of the artifact for which to fetch occurrences.
        If None, then all occurrences attached to the AA Note are returned.

    Yields:
      Occurrences bound to `note_ref` with matching `artifact_url` (if passed).
    """
    ListNoteOccurrencesRequest = (  # pylint: disable=invalid-name
        self.messages.ContaineranalysisProjectsNotesOccurrencesListRequest)
    occurrence_iter = list_pager.YieldFromList(
        self.client.projects_notes_occurrences,
        request=ListNoteOccurrencesRequest(name=note_ref.RelativeName()),
        field='occurrences',
        batch_size=100,
        batch_size_attribute='pageSize',
    )

    # TODO(b/69380601): This should be handled by the filter parameter to
    # ListNoteOccurrences, but filtering isn't implemented yet for the fields
    # we care about.
    def MatchesFilter(occurrence):
      if occurrence.kind != self.attestation_authority:
        return False
      if artifact_url and occurrence.resourceUrl != artifact_url:
        return False
      return True

    for occurrence in occurrence_iter:
      if MatchesFilter(occurrence):
        yield occurrence

  def YieldPgpKeyFingerprintsAndSignatures(self, note_ref, artifact_url):
    """Yields signatures for given artifact.

    Args:
      note_ref: The Note reference that will be queried for attached
        occurrences. (containeranalysis.providers.notes Resource)
      artifact_url: URL of artifact to which the signatures are associated

    Yields:
      Generator of pairs of (pgp_key_fingerprint, signature).  (pairs of
      strings)
    """
    occurrences_iter = self._YieldNoteOccurrences(
        note_ref=note_ref,
        artifact_url=artifact_url,
    )
    for occurrence in occurrences_iter:
      signed_attestation = occurrence.attestation.pgpSignedAttestation
      yield (signed_attestation.pgpKeyId, signed_attestation.signature)

  def YieldUrlsWithOccurrences(self, note_ref):
    """Yields Urls that have any associated occurrences.

    Args:
      note_ref: The Note reference that will be queried for attached
        occurrences. (containeranalysis.providers.notes Resource)

    Yields:
      Generator of URLs (strings).
    """
    occurrences = self._YieldNoteOccurrences(note_ref)
    urls_seen = set()
    for occurrence in occurrences:
      url = occurrence.resourceUrl
      if url not in urls_seen:
        urls_seen.add(url)
        yield url

  def CreateAttestationOccurrence(self, note_ref, project_ref, artifact_url,
                                  pgp_key_fingerprint, signature):
    """Creates Occurrence referencing given URL and Note.

    Args:
      note_ref: The Note reference that the created Occurrence will be
        bound to. (containeranalysis.providers.notes Resource)
      project_ref: The project ref where the Occurrence will be
        created. (cloudresourcemanager.projects Resource)
      artifact_url: URL of artifact to which the signature is associated
        (string)
      pgp_key_fingerprint: The ID of the public key that will be used to verify
        the signature.  This is usually generated by running
        `gpg --list-keys attesting_user@example.com` or equivalent.
        Note that this must match the public key inside the policy (managed
        separately) for the role being verified. (string)
      signature: The content artifact's signature, in the gpg
        clearsigned, ASCII-armored format.  Normally this is generated by
        running
        `gpg --local-user attesting_user@example.com --armor --sign <infile>`
        over the output of `CreateSignaturePayload`. (string)

    Returns:
      Created Occurrence.
    """
    attestation = self.messages.Attestation(
        pgpSignedAttestation=self.messages.PgpSignedAttestation(
            contentType=self.simple_signing_json,
            signature=signature,
            pgpKeyId=pgp_key_fingerprint,
        ))
    occurrence = self.messages.Occurrence(
        kind=self.attestation_authority,
        resourceUrl=artifact_url,
        noteName=note_ref.RelativeName(),
        attestation=attestation,
    )
    request = self.messages.ContaineranalysisProjectsOccurrencesCreateRequest(
        parent=project_ref.RelativeName(),
        occurrence=occurrence,
    )
    return self.client.projects_occurrences.Create(request)


class ContainerAnalysisLegacyClient(object):
  """A client to access containeranalysis for binauthz purposes.

  This client is only for legacy attestations, which have the BUILD_DETAILS
  kind.  It will be removed before BinAuthz exits alpha, and all attestations
  will instead use the ATTESTATION_AUTHORITY kind.
  """

  def __init__(self, client=None, messages=None):
    """Creates a ContainerAnalysisClient.

    If client or messages are unspecified, then the default instances are used.

    Args:
      client: containeranalyisis client
      messages: containeranalysis messages
    """
    self.client = (
        client or apis.GetClientInstance(
            DEFAULT_CONTAINERANALYSIS_API_NAME,
            DEFAULT_CONTAINERANALYSIS_API_VERSION,
        ))
    self.messages = (
        messages or apis.GetMessagesModule(
            DEFAULT_CONTAINERANALYSIS_API_NAME,
            DEFAULT_CONTAINERANALYSIS_API_VERSION,
        ))

  def _YieldOccurrences(self, project_ref, artifact_url=None):
    """Returns occurrences associated with given artifact URL.

    Args:
      project_ref: project where to look for Occurrences
        (cloudresourcemanager.projects Resource)
      artifact_url: URL of the artifact for which to fetch occurrences.
        If None, then all occurrences within project are returned.

    Returns:
      Generator of Occurrences matching specified criterion.
    """
    query_filter = None
    if artifact_url:
      query_filter = 'resourceUrl="{}" AND kind="BUILD_DETAILS"'.format(
          artifact_url)
    return list_pager.YieldFromList(
        self.client.projects_occurrences,
        request=self.messages.ContaineranalysisProjectsOccurrencesListRequest(
            parent=project_ref.RelativeName(), filter=query_filter),
        field='occurrences',
        batch_size=100,
        batch_size_attribute='pageSize')

  def _YieldNotes(self, project_ref, artifact_url):
    """Yields notes associated with given artifact URL.

    Args:
      project_ref: project where to look for Notes and Occurrences
        (cloudresourcemanager.projects Resource)
      artifact_url: URL of the artifact for which to fetch occurrences/notes

    Yields:
      Generator of Notes matching specified criterion.
    """
    occurrences = self._YieldOccurrences(project_ref, artifact_url)
    for occurrence in occurrences:
      if occurrence.noteName:
        # NOTE: GetNotes actually returns a single note, despite the name.
        yield self.client.projects_occurrences.GetNotes(
            self.messages.ContaineranalysisProjectsOccurrencesGetNotesRequest(
                name=occurrence.name))

  def _CreateNote(self, provider_ref, note_id, public_key, signature):
    """Creates Note containing a signature.

    Args:
      provider_ref: provider project for created Note
        (containeranalysis.providers Resource)
      note_id: ID of the Note to create.  Usually created with
        `googlecloudsdk.command_lib.container.binauthz.binauthz_util.NoteId`.
        (string)
      public_key: The content of the public key that will be used to verify
        the signature.  This is usually generated by running
        `gpg --armor --export attesting_user@example.com` or equivalent.
        Note that this must match the public key inside the policy (managed
        separately) for the role being verified.  Within the policy, this
        lives under `/projects/*policy/signingRoles/*/publicKeys/*`. (string)
      signature: The content artifact's signature, in the gpg
        clearsigned, ASCII-armored format.  Normally this is generated by
        running
        `gpg -u attesting_user@example.com --armor --clearsign`
        over the output of `CreateSignaturePayload`. (string)

    Returns:
      Created Note.
    """
    note = self.messages.Note(
        kind=self.messages.Note.KindValueValuesEnum.BUILD_DETAILS,
        shortDescription='signature attesting an artifact',
        buildType=self.messages.BuildType(
            signature=self.messages.BuildSignature(
                publicKey=public_key, signature=signature)))
    request = self.messages.ContaineranalysisProvidersNotesCreateRequest(
        name=provider_ref.RelativeName(), noteId=note_id, note=note)
    return self.client.providers_notes.Create(request)

  def _CreateOccurrence(self, note_ref, project_ref, artifact_url):
    """Creates Occurrence referencing given URL and Note.

    Args:
      note_ref: Note which to reference
        (containeranalysis.providers.notes Resource)
      project_ref: Project where to create Occurrence
        (cloudresourcemanager.projects Resource)
      artifact_url: URL of artifact to which the signature is associated
        (string)

    Returns:
      Created Occurrence.
    """
    occurrence = self.messages.Occurrence(
        kind=self.messages.Occurrence.KindValueValuesEnum.BUILD_DETAILS,
        resourceUrl=artifact_url,
        noteName=note_ref.RelativeName(),
        buildDetails=self.messages.BuildDetails())
    request = self.messages.ContaineranalysisProjectsOccurrencesCreateRequest(
        parent=project_ref.RelativeName(), occurrence=occurrence)
    return self.client.projects_occurrences.Create(request)

  def PutSignature(self, occurrence_project_ref, provider_ref,
                   provider_note_ref, note_id, artifact_url, public_key,
                   signature):
    """Create Note-Occurrence pair representing signature over artifact.

    This method is not atomic.  It has to first create a Note to bind the
    returned occurrence to.  It is therefore possible to create a Note and then
    encounter an error when creating the occurrence, leaving behind a Note.

    Args:
      occurrence_project_ref: The project ref where the Occurrence will be
        created. (cloudresourcemanager.projects Resource)
      provider_ref: The Note provider reference.  This is where the Note will
        be created. (containeranalysis.providers Resource)
      provider_note_ref: The Note reference that the created Occurrence will be
        bound to. (containeranalysis.providers.notes Resource)
      note_id: ID of the Note to create.  Usually created with
        `googlecloudsdk.command_lib.container.binauthz.binauthz_util.NoteId`.
        (string)
      artifact_url: URL of artifact to which the signature is associated
        (string)
      public_key: The content of the public key that will be used to verify
        the signature.  This is usually generated by running
        `gpg --armor --export attesting_user@example.com` or equivalent.
        Note that this must match the public key inside the policy (managed
        separately) for the role being verified.  Within the policy, this
        lives under `/projects/*policy/signingRoles/*/publicKeys/*`. (string)
      signature: The content artifact's signature, in the gpg
        clearsigned, ASCII-armored format.  Normally this is generated by
        running
        `gpg -u attesting_user@example.com --armor --clearsign`
        over the output of `CreateSignaturePayload`. (string)

    Returns:
      Pair of created Occurrence, Note.
    """
    # TODO(b/63455650): Clean up in case of partial failure.  Unfortunately
    # deleting the note is not an option (see bug).  It might be worthwhile
    # to check if the Note and Occurrence already exist before attempting
    # to create and attach them.
    note = self._CreateNote(
        provider_ref=provider_ref,
        note_id=note_id,
        public_key=public_key,
        signature=signature)
    occurrence = self._CreateOccurrence(
        note_ref=provider_note_ref,
        project_ref=occurrence_project_ref,
        artifact_url=artifact_url)
    return occurrence, note

  def YieldSignatures(self, project_ref, artifact_url):
    """Yields signatures for given artifact.

    Args:
      project_ref: project where to look for Notes and Occurrences
        (cloudresourcemanager.projects Resource)
      artifact_url: URL of artifact to which the signatures are associated

    Yields:
      Generator of pairs of (public_key, signature).  (pairs of strings)
    """
    notes_iter = self._YieldNotes(project_ref, artifact_url)
    for note in notes_iter:
      public_key = note.buildType.signature.publicKey
      signature = note.buildType.signature.signature
      yield (public_key, signature)

  def YieldUrlsWithOccurrences(self, project_ref):
    """Yields Urls that have any associated occurrences.

    Args:
      project_ref: project where to look for Occurrences
        (cloudresourcemanager.projects Resource)

    Yields:
      Generator of URLs (strings).
    """
    occurrences = self._YieldOccurrences(project_ref)
    for occurrence in occurrences:
      yield occurrence.resourceUrl
