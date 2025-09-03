# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Module for user service account mapping API support.

Typical usage (update command):

  # When defining arguments
  user_sa_mapping_util.AddUpdateUserSaMappingFlags(parser)

  # When running the command
  user_sa_mapping_diff = user_sa_mapping_util.Diff.FromUpdateArgs(args)
  if user_sa_mapping_diff.HasUpdates():
    orig_resource = Get(...)  # to prevent unnecessary Get calls
    user_sa_mapping_update = user_sa_mapping_diff.Apply(user_sa_mapping_cls,
    orig_resource.user_sa_mapping)
    if user_sa_mapping_update.needs_update:
      new_resource.user_sa_mapping = user_sa_mapping_update.user_sa_mapping
      field_mask.append('user_sa_mapping')
  Update(..., new_resource)

  # Or alternatively, when running the command
  user_sa_mapping_update = user_sa_mapping_util.ProcessUpdateArgsLazy(
    args, user_sa_mapping_cls, lambda: Get(...).user_sa_mapping)
  if user_sa_mapping_update.needs_update:
    new_resource.user_sa_mapping = user_sa_mapping_update.user_sa_mapping
    field_mask.append('user_sa_mapping')
  Update(..., new_resource)
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from googlecloudsdk.calliope import arg_parsers
import six


def AddUpdateUserSaMappingFlags(parser):
  """Adds update command user service account mapping flags to an argparse parser.

  Args:
    parser: The argparse parser to add the flags to.
  """
  secure_multi_tenancy_group = parser.add_group(mutex=True)
  add_and_remove_user_mapping_group = secure_multi_tenancy_group.add_group()
  add_and_remove_user_mapping_group.add_argument(
      '--add-user-mappings',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      action=arg_parsers.UpdateAction,
      help="""\
                List of user-to-service-account mappings to add to current mappings.
                If a mapping exists, its value is modified; otherwise, the new
                mapping is added.
            """,
  )
  add_and_remove_user_mapping_group.add_argument(
      '--remove-user-mappings',
      metavar='KEY',
      type=arg_parsers.ArgList(),
      action=arg_parsers.UpdateAction,
      help="""\
                List of user-to-service-account mappings to remove from the
                current mappings. If a mapping does not exist, it is ignored.
        """,
  )
  secure_multi_tenancy_group.add_argument(
      '--identity-config-file',
      help="""\
                Path to a YAML (or JSON) file that contains the configuration for [Secure Multi-Tenancy](/dataproc/docs/concepts/iam/sa-multi-tenancy)
                on the cluster. The path can be a Cloud Storage URL (example: 'gs://path/to/file')
                or a local filesystem path. The mappings provided in the file will overwrite existing mappings.

                The YAML file is formatted as follows:

                ```
                  # Mapping header (first line) required.
                  user_service_account_mapping:
                    bob@company.com: service-account-bob@project.iam.gserviceaccount.com
                    alice@company.com: service-account-alice@project.iam.gserviceaccount.com
                ```
            """,
  )


def GetAddUserSaMappingDictFromArgs(args):
  """Returns the add user mapping dict from the parsed args.

  Args:
    args: The parsed args.

  Returns:
    The add user mapping dict from the parsed args.
  """
  return args.add_user_mappings


def GetRemoveUserSaMappingListFromArgs(args):
  """Returns the remove user mapping list from the parsed args.

  Args:
    args: The parsed args.

  Returns:
    The remove user mapping list from the parsed args.
  """
  return args.remove_user_mappings


class UpdateResult(object):
  """Result type for Diff application.

  Attributes:
    needs_update: bool, whether the diff resulted in any changes to the existing
      user service account mapping proto.
    _user_sa_mapping: UserServiceAccountMappingValue, the new populated
      UserServiceAccountMappingValue object. If needs_update is False, this is
      identical to the original UserServiceAccountMappingValue object.
  """

  def __init__(self, needs_update, user_sa_mapping):
    self.needs_update = needs_update
    self._user_sa_mapping = user_sa_mapping

  @property
  def user_sa_mapping(self):
    """Returns the new user service account mapping.

    Raises:
      ValueError: if needs_update is False.
    """
    if not self.needs_update:
      raise ValueError(
          'If no update is needed (self.needs_update == False), '
          'checking user service account mapping is unnecessary.'
      )
    return self._user_sa_mapping

  def GetOrNone(self):
    """Returns the new user service account mapping if an update is needed or None otherwise.

    NOTE: If this function returns None, make sure not to include the user
    service account mapping field in the field mask of the update command.
    Otherwise, it's possible to inadvertently clear the user service account
    mapping on the resource.
    """
    try:
      return self.user_sa_mapping
    except ValueError:
      return None


class Diff(object):
  """Class for diffing user service account mapping."""

  def __init__(self, add_user_mapping=None, remove_user_mapping=None):
    """Initialize a Diff.

    Args:
      add_user_mapping: {str: str}, any user-to-service-account mapping to be
        added
      remove_user_mapping: List[str], any user-to-service-account mappings to be
        removed

    Returns:
      Diff.
    """
    self._add_user_mapping = add_user_mapping
    self._remove_user_mapping = remove_user_mapping

  def _AddUserSaMapping(self, new_user_sa_mapping):
    new_user_sa_mapping = new_user_sa_mapping.copy()
    new_user_sa_mapping.update(self._add_user_mapping)
    return new_user_sa_mapping

  def _RemoveUserSaMapping(self, new_user_sa_mapping):
    new_user_sa_mapping = new_user_sa_mapping.copy()
    for key in self._remove_user_mapping:
      new_user_sa_mapping.pop(key, None)
    return new_user_sa_mapping

  def _GetExistingUserSaMappingDict(self, user_sa_mapping):
    if not user_sa_mapping:
      return {}
    return {l.key: l.value for l in user_sa_mapping.additionalProperties}

  def _PackageUserSaMapping(self, user_sa_mapping_cls, user_sa_mapping):
    """Converts a dictionary representing a user service account mapping into an instance of a specified class.

    Args:
      user_sa_mapping_cls: The class to instantiate, which should have an
        `AdditionalProperty` inner class and an `additionalProperties`
        attribute.
      user_sa_mapping: A dictionary where keys are user identifiers and values
        are service account identifiers.

    Returns:
      An instance of `user_sa_mapping_cls` populated with the key-value pairs
      from `user_sa_mapping`.
    """
    # Sorted for test stability
    return user_sa_mapping_cls(
        additionalProperties=[
            user_sa_mapping_cls.AdditionalProperty(key=key, value=value)
            for key, value in sorted(six.iteritems(user_sa_mapping))
        ]
    )

  def HasUpdates(self):
    """Returns true iff the diff is non-empty which means user service account mapping has been updated."""
    return any([self._add_user_mapping, self._remove_user_mapping])

  def Apply(self, user_sa_mapping_cls, existing_user_sa_mapping=None):
    """Apply this Diff to the existing user service account mapping.

    Args:
      user_sa_mapping_cls: type, the UserServiceAccountMappingValue class for
        the resource.
      existing_user_sa_mapping: UserServiceAccountMappingValue, the existing
        UserServiceAccountMappingValue object for the original resource (or
        None, which is treated the same as empty user service account mapping)

    Returns:
      UpdateResult, the result of applying the diff.
    """
    existing_user_sa_mapping_dict = self._GetExistingUserSaMappingDict(
        existing_user_sa_mapping
    )
    new_user_sa_mapping_dict = existing_user_sa_mapping_dict.copy()

    if self._add_user_mapping:
      new_user_sa_mapping_dict = self._AddUserSaMapping(
          new_user_sa_mapping_dict
      )
    if self._remove_user_mapping:
      new_user_sa_mapping_dict = self._RemoveUserSaMapping(
          new_user_sa_mapping_dict
      )

    needs_update = new_user_sa_mapping_dict != existing_user_sa_mapping_dict
    return UpdateResult(
        needs_update,
        self._PackageUserSaMapping(
            user_sa_mapping_cls, new_user_sa_mapping_dict
        ),
    )

  @classmethod
  def FromUpdateArgs(cls, args):
    return cls(args.add_user_mappings, args.remove_user_mappings)


def ProcessUpdateArgsLazy(
    args, user_sa_mapping_cls, orig_user_sa_mapping_thunk
):
  """Returns the result of applying the diff constructed from args.

  Lazily fetches the original user service account mapping value if needed.

  Args:
    args: argparse.Namespace, the parsed arguments with add_user_mapping and
      remove_user_mapping
    user_sa_mapping_cls: type, the UserSaMappingValue class for the new user
      service account mapping.
    orig_user_sa_mapping_thunk: callable, a thunk which will return the original
      user_service_account_mapping object when evaluated.

  Returns:
    UpdateResult: the result of applying the diff.
  """
  diff = Diff.FromUpdateArgs(args)
  orig_user_sa_mapping = (
      orig_user_sa_mapping_thunk() if diff.HasUpdates() else None
  )
  return diff.Apply(user_sa_mapping_cls, orig_user_sa_mapping)
