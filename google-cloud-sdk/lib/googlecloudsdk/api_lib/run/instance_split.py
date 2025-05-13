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
"""Wrapper for Cloud Run InstanceSplit messages."""
from __future__ import absolute_import
from __future__ import annotations
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections

from googlecloudsdk.core import exceptions
from googlecloudsdk.generated_clients.apis.run.v1 import run_v1_messages

try:
  # Python 3.3 and above.
  collections_abc = collections.abc
except AttributeError:
  collections_abc = collections


class InvalidInstanceSplitSpecificationError(exceptions.Error):
  """Error to indicate an invalid instance split specification."""

  pass


# Designated key value for latest.
# Revisions' names may not be uppercase, so this is distinct.
LATEST_REVISION_KEY = 'LATEST'


def NewInstanceSplit(messages, key: str, percent=None):
  """Creates a new InstanceSplit.

  Args:
    messages: The message module that defines InstanceSplit.
    key: The key for the instance split assignment in the InstanceSplits
      mapping.
    percent: Optional percent of instance split to assign.

  Returns:
    The newly created InstanceSplit.
  """
  if key == LATEST_REVISION_KEY:
    result = messages.InstanceSplit(latestRevision=True, percent=percent)
  else:
    result = messages.InstanceSplit(revisionName=key, percent=percent)
  return result


def GetKey(split: run_v1_messages.InstanceSplit):
  """Returns the key for a InstanceSplit.

  Args:
    split: InstanceSplit, the InstanceSplit to check

  Returns:
    LATEST_REVISION_KEY if split is for the latest revison or
    split.revisionName if not.
  """
  return LATEST_REVISION_KEY if split.latestRevision else split.revisionName


def SortKeyFromKey(key: str):
  """Sorted key function to order InstanceSplit keys.

  InstanceSplits keys are one of:
  o revisionName
  o LATEST_REVISION_KEY

  Note LATEST_REVISION_KEY is not a str so its ordering with respect
  to revisionName keys is hard to predict.

  Args:
    key: Key for a InstanceSplits dictionary.

  Returns:
    A value that sorts by revisionName with LATEST_REVISION_KEY
    last.
  """
  if key == LATEST_REVISION_KEY:
    result = (2, key)
  else:
    result = (1, key)
  return result


def SortKeyFromSplit(split: run_v1_messages.InstanceSplit):
  """Sorted key function to order InstanceSplit objects by key.

  Args:
    split: A InstanceSplit.

  Returns:
    A value that sorts by revisionName with LATEST_REVISION_KEY
    last.
  """
  key = GetKey(split)
  return SortKeyFromKey(key)


def _GetItemSortKey(split: run_v1_messages.InstanceSplit):
  """Key function for sorting InstanceSplit objects during __getitem__."""
  # The list of InstanceSplits returned by InstanceSplits.__getitem__ needs to
  # be sorted for comparisons on InstanceSplits instances to work correctly. The
  # order of the list of instance split assignments for a given key should not
  # affect equality. InstanceSplit is not hashable so a set is not an option.
  percent = split.percent if split.percent else 0
  return percent


class InstanceSplits(collections_abc.MutableMapping):
  """Wraps a repeated InstanceSplit message and provides dict-like access.

  The dictionary key is one of
     LATEST_REVISION_KEY for the latest revision
     InstanceSplit.revisionName for InstanceSplits with a revision name.

  The dictionary value is a list of all instance split assignments referencing
  the same revision, either by name or the latest revision.
  """

  def __init__(self, messages_module, to_wrap):
    """Constructs a new InstanceSplits instance.

    The InstanceSplits instance wraps the to_wrap argument, which is a repeated
    proto message. Operations that mutate to_wrap will usually occur through
    this class, but that is not a requirement. Callers can directly mutate
    to_wrap by accessing the proto directly.

    Args:
      messages_module: The message module that defines InstanceSplit.
      to_wrap: The instance split assignments to wrap.
    """
    self._messages = messages_module
    self._m = to_wrap
    self._instance_split_cls = self._messages.InstanceSplit

  def __getitem__(self, key):
    """Gets a sorted list of instance split assignments associated with the given key.

    Allows accessing instance split assignments based on the revision they
    reference
    (either directly by name or the latest ready revision by specifying
    "LATEST" as the key).

    Returns a sorted list of instance split assignments to support comparison
    operations on
    InstanceSplits objects which should be independent of the order of the
    instance split assignments for a given key.

    Args:
      key: A revision name or "LATEST" to get the instance split assignments
        for.

    Returns:
      A sorted list of instance split assignments associated with the given key.

    Raises:
      KeyError: If this object does not contain the given key.
    """
    result = sorted(
        (i for i in self._m if GetKey(i) == key), key=_GetItemSortKey
    )
    if not result:
      raise KeyError(key)
    return result

  def __delitem__(self, key):
    """Not implemented for now."""
    raise NotImplementedError()

  def __setitem__(self, key, new_splits):
    """Not implemented for now."""
    raise NotImplementedError()

  def __contains__(self, key):
    """Implements evaluation of `item in self`."""
    for split in self._m:
      if key == GetKey(split):
        return True
    return False

  @property
  def _key_set(self):
    """A set containing the mapping's keys."""
    return set(GetKey(i) for i in self._m)

  def __len__(self):
    """Implements evaluation of `len(self)`."""
    return len(self._key_set)

  def __iter__(self):
    """Returns an iterator over the instance split assignment keys."""
    return iter(self._key_set)

  def MakeSerializable(self):
    return self._m

  def __repr__(self):
    content = ', '.join('{}: {}'.format(k, v) for k, v in self.items())
    return '[%s]' % content
