# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Shared utilities to access the Google Secret Manager API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iam import iam_util


def GetClient(version=None):
  """Get the default client."""
  return apis.GetClientInstance('secretmanager', version or
                                apis.ResolveVersion('secretmanager'))


def GetMessages(version=None):
  """Get the default messages module."""
  return apis.GetMessagesModule('secretmanager', version or
                                apis.ResolveVersion('secretmanager'))


def _FormatUpdateMask(update_mask):
  return ','.join(update_mask)


def _MakeReplicationMessage(messages, policy, locations, keys):
  """Create a replication message from its components."""
  if not policy:
    return None
  replication = messages.Replication(automatic=messages.Automatic())
  if policy == 'automatic' and keys:
    replication = messages.Replication(
        automatic=messages.Automatic(
            customerManagedEncryption=messages.CustomerManagedEncryption(
                kmsKeyName=keys[0])))
  if policy == 'user-managed':
    replicas = []
    for i, location in enumerate(locations):
      if i < len(keys):
        replicas.append(
            messages.Replica(
                location=location,
                customerManagedEncryption=messages.CustomerManagedEncryption(
                    kmsKeyName=keys[i])))
      else:
        replicas.append(messages.Replica(location=locations[i]))

    replication = messages.Replication(
        userManaged=messages.UserManaged(replicas=replicas))
  return replication


class Client(object):
  """Base class for all clients."""

  def __init__(self, client=None, messages=None, api_version=None):
    self.client = client or GetClient(version=api_version)
    self.messages = messages or self.client.MESSAGES_MODULE


class Locations(Client):
  """High-level client for locations."""

  def __init__(self, client=None, messages=None, api_version=None):
    super(Locations, self).__init__(client, messages, api_version)
    self.service = self.client.projects_locations

  def Get(self, location_ref):
    """Get the location with the given name."""
    return self.service.Get(
        self.messages.SecretmanagerProjectsLocationsGetRequest(
            name=location_ref.RelativeName()))

  def ListWithPager(self, project_ref, limit):
    """List secrets returning a pager object."""
    request = self.messages.SecretmanagerProjectsLocationsListRequest(
        name=project_ref.RelativeName())

    return list_pager.YieldFromList(
        service=self.service,
        request=request,
        field='locations',
        limit=limit,
        batch_size_attribute='pageSize')


class Secrets(Client):
  """High-level client for secrets."""

  def __init__(self, client=None, messages=None, api_version=None):
    client = client or GetClient(version=api_version)
    super(Secrets, self).__init__(client, messages)
    self.service = self.client.projects_secrets

  def Create(
      self,
      secret_ref,
      policy,
      locations,
      labels,
      expire_time=None,
      ttl=None,
      keys=None,
      next_rotation_time=None,
      rotation_period=None,
      topics=None,
      annotations=None,
      regional_kms_key_name=None,
      version_destroy_ttl=None,
      secret_location=None,
  ):
    """Create a secret."""
    keys = keys or []
    replication = _MakeReplicationMessage(self.messages, policy, locations,
                                          keys)
    topics_message_list = []
    if topics:
      for topic in topics:
        topics_message_list.append(self.messages.Topic(name=topic))
    new_annotations = self.messages.Secret.AnnotationsValue(
        additionalProperties=[])
    if annotations:
      for annotation_pair in annotations:
        new_annotations.additionalProperties.append(annotation_pair)

    rotation = None
    if next_rotation_time or rotation_period:
      rotation = self.messages.Rotation(
          nextRotationTime=next_rotation_time, rotationPeriod=rotation_period
      )

    customer_managed_encryption = None
    if regional_kms_key_name:
      customer_managed_encryption = self.messages.CustomerManagedEncryption(
          kmsKeyName=regional_kms_key_name
      )

      # For regional requests, replication should not be there.
      replication = None
    return self.service.Create(
        self.messages.SecretmanagerProjectsSecretsCreateRequest(
            parent=GetParentRelativeNameForSecret(secret_ref, secret_location),
            secretId=secret_ref.Name(),
            secret=self.messages.Secret(
                labels=labels,
                replication=replication,
                expireTime=expire_time,
                ttl=ttl,
                topics=topics_message_list,
                annotations=new_annotations,
                rotation=rotation,
                customerManagedEncryption=customer_managed_encryption,
                versionDestroyTtl=version_destroy_ttl,
            ),
        )
    )

  def Delete(self, secret_ref, etag=None, secret_location=None):
    """Delete a secret."""
    return self.service.Delete(
        self.messages.SecretmanagerProjectsSecretsDeleteRequest(
            etag=etag, name=GetRelativeName(secret_ref, secret_location)
        )
    )

  def Get(self, secret_ref, secret_location=None):
    """Get the secret with the given name."""
    return self.service.Get(
        self.messages.SecretmanagerProjectsSecretsGetRequest(
            name=GetRelativeName(secret_ref, secret_location)
        )
    )

  def GetOrNone(self, secret_ref, secret_location=None):
    """Attempt to get the secret, returning None if the secret does not exist."""
    try:
      return self.Get(secret_ref=secret_ref, secret_location=secret_location)
    except apitools_exceptions.HttpNotFoundError:
      return None

  def ListWithPager(self, project_ref, limit, request_filter=None):
    """List secrets returning a pager object."""
    request = self.messages.SecretmanagerProjectsSecretsListRequest(
        parent=project_ref.RelativeName(), filter=request_filter)

    return list_pager.YieldFromList(
        service=self.service,
        request=request,
        field='secrets',
        limit=limit,
        batch_size_attribute='pageSize')

  def AddVersion(self, secret_ref, data, data_crc32c, secret_location=None):
    """Adds a new version of an existing secret."""
    request = self.messages.SecretmanagerProjectsSecretsAddVersionRequest(
        parent=GetRelativeName(secret_ref, secret_location),
        addSecretVersionRequest=self.messages.AddSecretVersionRequest(
            payload=self.messages.SecretPayload(
                data=data, dataCrc32c=data_crc32c
            )
        ),
    )
    return self.service.AddVersion(request)

  def Update(
      self,
      secret_ref,
      labels,
      update_mask,
      etag=None,
      expire_time=None,
      ttl=None,
      topics=None,
      version_aliases=None,
      annotations=None,
      next_rotation_time=None,
      rotation_period=None,
      version_destroy_ttl=None,
      secret_location=None,
      regional_kms_key_name=None,
  ):
    """Update a secret."""

    rotation = None
    if next_rotation_time or rotation_period:
      rotation = self.messages.Rotation(
          nextRotationTime=next_rotation_time, rotationPeriod=rotation_period)

    topics_message_list = []

    if topics:
      for topic in topics:
        topics_message_list.append(self.messages.Topic(name=topic))
    new_version_aliases = self.messages.Secret.VersionAliasesValue(
        additionalProperties=[])
    if version_aliases:
      for version_alias_pair in version_aliases:
        new_version_aliases.additionalProperties.append(version_alias_pair)
    new_annotations = self.messages.Secret.AnnotationsValue(
        additionalProperties=[])
    if annotations:
      for annotation_pair in annotations:
        new_annotations.additionalProperties.append(annotation_pair)

    customer_managed_encryption = None
    if regional_kms_key_name:
      customer_managed_encryption = self.messages.CustomerManagedEncryption(
          kmsKeyName=regional_kms_key_name
      )
    return self.service.Patch(
        self.messages.SecretmanagerProjectsSecretsPatchRequest(
            name=GetRelativeName(secret_ref, secret_location),
            secret=self.messages.Secret(
                labels=labels,
                versionAliases=new_version_aliases,
                annotations=new_annotations,
                etag=etag,
                expireTime=expire_time,
                ttl=ttl,
                topics=topics_message_list,
                rotation=rotation,
                versionDestroyTtl=version_destroy_ttl,
                customerManagedEncryption=customer_managed_encryption,
            ),
            updateMask=_FormatUpdateMask(update_mask),
        )
    )

  def SetReplication(self, secret_ref, policy, locations, keys):
    """Set the replication policy on an existing secret.."""
    replication = _MakeReplicationMessage(
        self.messages, policy, locations, keys
    )
    return self.service.Patch(
        self.messages.SecretmanagerProjectsSecretsPatchRequest(
            name=secret_ref.RelativeName(),
            secret=self.messages.Secret(replication=replication),
            updateMask=_FormatUpdateMask(['replication']),
        )
    )

  def GetIamPolicy(self, resource_ref, secret_location=None):
    """Get iam policy request.

    Args:
      resource_ref: Multitype resource (regional or global secret resource)
      secret_location: location of the secret, None if global

    Returns:
      Operation response
    """
    # check the secret type
    if secret_location:
      self.service = self.client.projects_locations_secrets
      req = self.messages.SecretmanagerProjectsLocationsSecretsGetIamPolicyRequest(
          resource=GetRelativeName(resource_ref, secret_location),
          options_requestedPolicyVersion=iam_util.MAX_LIBRARY_IAM_SUPPORTED_VERSION,
      )
    else:
      self.service = self.client.projects_secrets
      req = self.messages.SecretmanagerProjectsSecretsGetIamPolicyRequest(
          options_requestedPolicyVersion=iam_util.MAX_LIBRARY_IAM_SUPPORTED_VERSION,
          resource=GetRelativeName(resource_ref, secret_location),
      )
    return self.service.GetIamPolicy(req)

  def SetIamPolicy(
      self, secret_ref, policy, update_mask=None, secret_location=None
  ):
    """Set iam policy request.

    Args:
      secret_ref: secret resource
      policy: policy to be set
      update_mask: update mask
      secret_location: location of the secret, None if global

    Returns:
      Operation response
    """
    # check the secret type
    if secret_location:
      self.service = self.client.projects_locations_secrets
      req = self.messages.SecretmanagerProjectsLocationsSecretsSetIamPolicyRequest(
          resource=GetRelativeName(secret_ref, secret_location),
          setIamPolicyRequest=self.messages.SetIamPolicyRequest(
              policy=policy, updateMask=update_mask
          ),
      )
    else:
      self.service = self.client.projects_secrets
      req = self.messages.SecretmanagerProjectsSecretsSetIamPolicyRequest(
          resource=GetRelativeName(secret_ref, secret_location),
          setIamPolicyRequest=self.messages.SetIamPolicyRequest(
              policy=policy, updateMask=update_mask
          ),
      )
    return self.service.SetIamPolicy(req)

  def AddIamPolicyBinding(
      self, resorce_ref, member, role, condition=None, secret_location=None
  ):
    """Add iam policy binding request."""
    policy = self.GetIamPolicy(resorce_ref, secret_location=secret_location)
    policy.version = iam_util.MAX_LIBRARY_IAM_SUPPORTED_VERSION
    iam_util.AddBindingToIamPolicyWithCondition(
        self.messages.Binding,
        self.messages.Expr,
        policy,
        member,
        role,
        condition=condition,
    )
    return self.SetIamPolicy(
        resorce_ref, policy, secret_location=secret_location
    )

  def RemoveIamPolicyBinding(
      self, resorce_ref, member, role, condition=None, secret_location=None
  ):
    """Remove iam policy binding request."""
    policy = self.GetIamPolicy(resorce_ref, secret_location=secret_location)
    policy.version = iam_util.MAX_LIBRARY_IAM_SUPPORTED_VERSION
    iam_util.RemoveBindingFromIamPolicyWithCondition(
        policy,
        member,
        role,
        condition=condition,
    )
    return self.SetIamPolicy(
        resorce_ref, policy, secret_location=secret_location
    )


class SecretsLatest(Client):
  """High-level client for latest secrets."""

  def __init__(self, client=None, messages=None, api_versions=None):
    super(SecretsLatest, self).__init__(client, messages, api_versions)
    self.service = self.client.projects_secrets_latest

  def Access(self, secret_ref, secret_location=None):
    """Access the latest version of a secret."""
    return self.service.Access(
        self.messages.SecretmanagerProjectsSecretsLatestAccessRequest(
            name=GetRelativeName(secret_ref, secret_location)
        )
    )


class Versions(Client):
  """High-level client for secret versions."""

  def __init__(self, client=None, messages=None, api_version=None):
    super(Versions, self).__init__(client, messages, api_version)
    self.service = self.client.projects_secrets_versions

  def Access(self, version_ref, secret_location=None):
    """Access a specific version of a secret."""
    return self.service.Access(
        self.messages.SecretmanagerProjectsSecretsVersionsAccessRequest(
            name=GetRelativeName(version_ref, secret_location)
        )
    )

  def Destroy(self, version_ref, etag=None, secret_location=None):
    """Destroy a secret version."""
    destroy_secret_version_request = self.messages.DestroySecretVersionRequest(
        etag=etag)
    return self.service.Destroy(
        self.messages.SecretmanagerProjectsSecretsVersionsDestroyRequest(
            destroySecretVersionRequest=destroy_secret_version_request,
            name=GetRelativeName(version_ref, secret_location),
        )
    )

  def Disable(self, version_ref, etag=None, secret_location=None):
    """Disable a secret version."""
    disable_secret_version_request = self.messages.DisableSecretVersionRequest(
        etag=etag)
    return self.service.Disable(
        self.messages.SecretmanagerProjectsSecretsVersionsDisableRequest(
            disableSecretVersionRequest=disable_secret_version_request,
            name=GetRelativeName(version_ref, secret_location),
        )
    )

  def Enable(self, version_ref, etag=None, secret_location=None):
    """Enable a secret version."""
    enable_secret_version_request = self.messages.EnableSecretVersionRequest(
        etag=etag)
    return self.service.Enable(
        self.messages.SecretmanagerProjectsSecretsVersionsEnableRequest(
            enableSecretVersionRequest=enable_secret_version_request,
            name=GetRelativeName(version_ref, secret_location),
        )
    )

  def Get(self, version_ref, secret_location=None):
    """Get the secret version with the given name."""
    return self.service.Get(
        self.messages.SecretmanagerProjectsSecretsVersionsGetRequest(
            name=GetRelativeName(version_ref, secret_location)
        )
    )

  def List(self, secret_ref, limit, secret_location=None):
    """List secrets and return an array."""
    request = self.messages.SecretmanagerProjectsSecretsVersionsListRequest(
        parent=GetRelativeName(secret_ref, secret_location), pageSize=limit
    )
    return self.service.List(request)

  def ListWithPager(
      self, secret_ref, limit, request_filter=None, secret_location=None
  ):
    """List secrets returning a pager object."""
    request = self.messages.SecretmanagerProjectsSecretsVersionsListRequest(
        parent=GetRelativeName(secret_ref, secret_location),
        filter=request_filter,
        pageSize=0,
    )
    return list_pager.YieldFromList(
        service=self.service,
        request=request,
        field='versions',
        limit=limit,
        batch_size=0,
        batch_size_attribute='pageSize')


def GetApiFromTrack(track):
  """Returns api version based on the track."""
  if track == base.ReleaseTrack.BETA:
    return 'v1beta2'
  elif track == base.ReleaseTrack.GA:
    return 'v1'


def GetRelativeName(resource, location):
  if location:
    resource_uri = resource.RelativeName()
    split = resource_uri.split('/')
    return '/'.join(split[:2]) + f'/locations/{location}/' + '/'.join(split[2:])
  return resource.RelativeName()


def GetParentRelativeNameForSecret(resource, location):
  if location:
    resource_uri = resource.Parent().RelativeName()
    return resource_uri + f'/locations/{location}'
  return resource.Parent().RelativeName()
