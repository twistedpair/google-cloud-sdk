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

"""API helpers for interacting with attestation authorities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.binauthz import apis
from googlecloudsdk.api_lib.container.binauthz import util
from googlecloudsdk.command_lib.container.binauthz import exceptions


class Client(object):
  """A client for interacting with authorities."""

  def __init__(self, client=None, messages=None):
    self.client = client or apis.GetClientInstance()
    self.messages = messages or apis.GetMessagesModule()

  def Get(self, authority_ref):
    """Get the specified attestation authority."""
    return self.client.projects_attestationAuthorities.Get(
        self.messages.BinaryauthorizationProjectsAttestationAuthoritiesGetRequest(  # pylint: disable=line-too-long
            name=authority_ref.RelativeName(),
        ))

  def List(self, project_ref, limit=None, batch_size=500):
    """List the attestation authorities associated with the current project."""
    return list_pager.YieldFromList(
        self.client.projects_attestationAuthorities,
        self.messages.BinaryauthorizationProjectsAttestationAuthoritiesListRequest(  # pylint: disable=line-too-long
            parent=project_ref.RelativeName(),
        ),
        batch_size=batch_size,
        limit=limit,
        field='attestationAuthorities',
        batch_size_attribute='pageSize')

  def Create(self, authority_ref, note_ref):
    """Create an attestation authorities associated with the current project."""
    project_ref = authority_ref.Parent(util.PROJECTS_COLLECTION)
    return self.client.projects_attestationAuthorities.Create(
        self.messages.BinaryauthorizationProjectsAttestationAuthoritiesCreateRequest(  # pylint: disable=line-too-long
            attestationAuthority=self.messages.AttestationAuthority(
                name=authority_ref.RelativeName(),
                userOwnedDrydockNote=self.messages.UserOwnedDrydockNote(
                    noteReference=note_ref.RelativeName(),
                ),
            ),
            attestationAuthorityId=authority_ref.Name(),
            parent=project_ref.RelativeName(),
        ))

  def AddKey(self, authority_ref, key_content, comment=None):
    """Add a key to an attestation authority.

    Args:
      authority_ref: ResourceSpec, The authority to be updated.
      key_content: The contents of the public key file.
      comment: The comment on the public key.

    Returns:
      The added public key.

    Raises:
      AlreadyExistsError: If a public key with the same key content was found on
          the authority.
    """
    authority = self.Get(authority_ref)

    existing_pub_keys = set(
        public_key.asciiArmoredPgpPublicKey
        for public_key in authority.userOwnedDrydockNote.publicKeys)
    if key_content in existing_pub_keys:
      raise exceptions.AlreadyExistsError(
          'Provided public key already present on authority [{}]'.format(
              authority.name))

    authority.userOwnedDrydockNote.publicKeys.append(
        self.messages.AttestationAuthorityPublicKey(
            asciiArmoredPgpPublicKey=key_content,
            comment=comment))

    updated_authority = (
        self.client.projects_attestationAuthorities.Update(authority))
    return next(
        public_key
        for public_key in updated_authority.userOwnedDrydockNote.publicKeys
        if public_key.asciiArmoredPgpPublicKey == key_content)

  def RemoveKey(self, authority_ref, fingerprint_to_remove):
    """Remove a key on an attestation authority.

    Args:
      authority_ref: ResourceSpec, The authority to be updated.
      fingerprint_to_remove: The fingerprint of the key to remove.

    Raises:
      NotFoundError: If an expected public key could not be located by
          fingerprint.
    """
    authority = self.Get(authority_ref)

    existing_ids = set(
        public_key.id
        for public_key in authority.userOwnedDrydockNote.publicKeys)
    if fingerprint_to_remove not in existing_ids:
      raise exceptions.NotFoundError(
          'No matching public key found on authority [{}]'.format(
              authority.name))

    authority.userOwnedDrydockNote.publicKeys = [
        public_key for public_key in authority.userOwnedDrydockNote.publicKeys
        if public_key.id != fingerprint_to_remove]

    self.client.projects_attestationAuthorities.Update(authority)

  def UpdateKey(
      self, authority_ref, fingerprint, key_content=None, comment=None):
    """Update a key on an attestation authority.

    Args:
      authority_ref: ResourceSpec, The authority to be updated.
      fingerprint: The fingerprint of the key to update.
      key_content: The contents of the public key file.
      comment: The comment on the public key.

    Returns:
      The updated public key.

    Raises:
      NotFoundError: If an expected public key could not be located by
          fingerprint.
      InvalidStateError: If multiple public keys matched the provided
          fingerprint.
    """
    authority = self.Get(authority_ref)

    existing_keys = [
        public_key
        for public_key in authority.userOwnedDrydockNote.publicKeys
        if public_key.id == fingerprint]

    if not existing_keys:
      raise exceptions.NotFoundError(
          'No matching public key found on authority [{}]'.format(
              authority.name))
    if len(existing_keys) > 1:
      raise exceptions.InvalidStateError(
          'Multiple matching public keys found on authority [{}]'.format(
              authority.name))

    existing_key = existing_keys[0]
    if key_content is not None:
      existing_key.asciiArmoredPgpPublicKey = key_content
    if comment is not None:
      existing_key.comment = comment

    updated_authority = (
        self.client.projects_attestationAuthorities.Update(authority))
    return next(
        public_key
        for public_key in updated_authority.userOwnedDrydockNote.publicKeys
        if public_key.id == fingerprint)

  def Update(self, authority_ref):
    """Update an attestation authorities associated with the current project.

    Args:
      authority_ref: ResourceSpec, The authority to be updated.

    Returns:
      The updated authority.
    """
    authority = self.Get(authority_ref)

    # TODO(b/74193183): Add a comment option.

    return self.client.projects_attestationAuthorities.Update(authority)

  def Delete(self, authority_ref):
    """Delete the specified attestation authority."""
    self.client.projects_attestationAuthorities.Delete(
        self.messages.BinaryauthorizationProjectsAttestationAuthoritiesDeleteRequest(  # pylint: disable=line-too-long
            name=authority_ref.RelativeName(),
        ))
