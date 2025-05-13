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
"""Wrapper for Cloud Run InstanceSplits messages in spec and status."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import dataclasses
from typing import List, Mapping, Optional

from googlecloudsdk.api_lib.run import instance_split
from googlecloudsdk.generated_clients.apis.run.v1 import run_v1_messages as messages
import six


# Human readable indicator for a missing split percentage.
_MISSING_PERCENT = '-'


def _FormatPercentage(percent):
  if percent == _MISSING_PERCENT:
    return _MISSING_PERCENT
  else:
    return '{}%'.format(percent)


def _SumPercent(splits):
  """Sums the percents of the given splits."""
  return sum(i.percent for i in splits if i.percent)


@dataclasses.dataclass(frozen=True)
class InstanceSplitPair(object):
  """Holder for InstanceSplit status information.

  The representation of the status of instance splits for a worker pool
  includes:
    o User requested assignments (spec.instanceSplits)
    o Actual assignments (status.instanceSplits)

  Each of spec.instanceSplits and status.instanceSplits may contain multiple
  instance splits that reference the same revision, either directly by name or
  indirectly by referencing the latest ready revision.

  The spec and status instance splits for a revision may differ after a failed
  split update or during a successful one. A InstanceSplitPair holds all
  spec and status InstanceSplits that reference the same revision by name or
  reference the latest ready revision. Both the spec and status instance splits
  can be empty.

  The latest revision can be included in the spec instance splits
  two ways
    o by revisionName
    o by setting latestRevision to True.

  Managed cloud run provides a single combined status instance split
  for both spec entries with:
    o revisionName set to the latest revision's name
    o percent set to combined percentage for both spec entries
    o latestRevision not set

  In this case both spec targets are paired with the combined status
  target and a status_percent_override value is used to allocate the
  combined instance split.

  Attributes:
    spec_splits: The spec instance splits for the referenced revision.
    status_splits: The status instance splits for the referenced revision.
    revision_name: The name of the referenced revision.
    latest: Boolean indicating if the instance splits reference the latest ready
      revision.
    status_percent_override: The percent of splits allocated to the referenced
      revision in the worker pool's status.
  """

  # This class has lower camel case public attribute names to implement our
  # desired style for json and yaml property names in structured output.
  #
  # This class gets passed to gcloud's printer to produce the output of
  # `gcloud run worker-pools describe`. When users specify --format=yaml or
  # --format=json, the public attributes of this class get automatically
  # converted to fields in the resulting json or yaml output, with names
  # determined by this class's attribute names. We want the json and yaml output
  # to have lower camel case property names.

  spec_splits: List[messages.InstanceSplit]
  status_splits: List[messages.InstanceSplit]
  revision_name: str
  latest: bool
  status_percent_override: Optional[int] = None

  @property
  def key(self):
    """Returns the key for the instance split pair."""
    return (
        instance_split.LATEST_REVISION_KEY
        if self.latestRevision
        else instance_split.GetKey(self)
    )

  @property
  def latestRevision(self):  # pylint: disable=invalid-name
    """Returns true if the instance splits reference the latest revision."""
    return self.latest

  @property
  def revisionName(self):  # pylint: disable=invalid-name
    """Returns the name of the referenced revision."""
    return self.revision_name

  @property
  def specPercent(self):  # pylint: disable=invalid-name
    """Returns the sum of the spec instance split percentages."""
    if self.spec_splits:
      return six.text_type(_SumPercent(self.spec_splits))
    else:
      return _MISSING_PERCENT

  @property
  def statusPercent(self):  # pylint: disable=invalid-name
    """Returns the sum of the status instance split percentages."""
    if self.status_percent_override is not None:
      return six.text_type(self.status_percent_override)
    elif self.status_splits:
      return six.text_type(_SumPercent(self.status_splits))
    else:
      return _MISSING_PERCENT

  @property
  def displayPercent(self):  # pylint: disable=invalid-name
    """Returns human readable revision percent."""
    if self.statusPercent == self.specPercent:
      return _FormatPercentage(self.statusPercent)
    else:
      return '{:4} (currently {})'.format(
          _FormatPercentage(self.specPercent),
          _FormatPercentage(self.statusPercent),
      )

  @property
  def displayRevisionId(self):  # pylint: disable=invalid-name
    """Returns human readable revision identifier."""
    if self.latestRevision:
      return '%s (currently %s)' % (
          instance_split.GetKey(self),
          self.revisionName,
      )
    else:
      return self.revisionName


def _SplitManagedLatestStatusSplits(
    spec_dict: Mapping[str, List[messages.InstanceSplit]],
    status_dict: Mapping[str, List[messages.InstanceSplit]],
    latest_ready_revision_name: str,
):
  """Splits the fully-managed latest status target.

  For managed the status target for the latest revision is
  included by revisionName only and may hold the combined splits
  percent for both latestRevisionName and latestRevision spec splits.
  Here we adjust keys in status_dict to match with spec_dict.

  Args:
    spec_dict: Dictionary mapping revision name or 'LATEST' to the spec instance
      split referencing that revision.
    status_dict: Dictionary mapping revision name or 'LATEST' to the status
      instance split referencing that revision. Modified by this function.
    latest_ready_revision_name: The name of the latest ready revision.

  Returns:
    Optionally, the id of the list of status splits containing the combined
    instance splits referencing the latest ready revision by name and by latest.
  """
  combined_status_splits_id = None
  if (
      instance_split.LATEST_REVISION_KEY in spec_dict
      and instance_split.LATEST_REVISION_KEY not in status_dict
      and latest_ready_revision_name in status_dict
  ):
    latest_status_splits = status_dict[latest_ready_revision_name]
    status_dict[instance_split.LATEST_REVISION_KEY] = latest_status_splits
    if latest_ready_revision_name in spec_dict:
      combined_status_splits_id = id(latest_status_splits)
    else:
      del status_dict[latest_ready_revision_name]
  return combined_status_splits_id


def _PercentOverride(key, spec_dict, status_splits, combined_status_splits_id):
  """Computes the optional override percent to apply to the status percent."""
  percent_override = None
  if id(status_splits) == combined_status_splits_id:
    spec_by_latest_percent = _SumPercent(
        spec_dict[instance_split.LATEST_REVISION_KEY]
    )
    status_percent = _SumPercent(status_splits)
    status_by_latest_percent = min(spec_by_latest_percent, status_percent)
    if key == instance_split.LATEST_REVISION_KEY:
      percent_override = status_by_latest_percent
    else:
      percent_override = status_percent - status_by_latest_percent
  return percent_override


def GetInstanceSplitPairs(
    spec_split: instance_split.InstanceSplits,
    status_split: instance_split.InstanceSplits,
    latest_ready_revision_name: str,
):
  """Returns a list of InstanceSplitPairs for a WorkerPool.

  Given the spec and status instance splits wrapped in a InstanceSplits instance
  for a sevice, this function pairs up all spec and status instance splits that
  reference the same revision (either by name or the latest ready revision) into
  InstanceSplitPairs. This allows the caller to easily see any differences
  between the spec and status split.

  For fully-managed Cloud Run, the status target for the latest revision is
  included by revisionName only and may hold the combined split
  percent for both latestRevisionName and latestRevision spec targets. This
  function splits the fully-managed status target for the latest revision into
  a target for the percent allocated to the latest revision by name and a target
  for the percent allocated to the latest revision because it is latest.

  Args:
    spec_split: A instance_split.InstanceSplits instance wrapping the spec
      split.
    status_split: A instance_split.InstanceSplits instance wrapping the status
      split.
    latest_ready_revision_name: The name of the worker pool's latest ready
      revision.

  Returns:
    A list of InstanceSplitPairs representing the current state of the worker
    pool's
    instance split assignments. The InstanceSplitPairs are sorted by revision
    name,
    with targets referencing the latest ready revision at the end.
  """
  # Copy spec and status split to dictionaries to allow mapping
  # instance_split.LATEST_REVISION_KEY to the same targets as
  # latest_ready_revision_name without modifying the underlying protos during
  # a read-only operation. These dictionaries map revision name (or "LATEST"
  # for the latest ready revision) to a list of InstanceSplit protos.
  spec_dict = dict(spec_split)
  status_dict = dict(status_split)

  combined_status_splits_id = _SplitManagedLatestStatusSplits(
      spec_dict, status_dict, latest_ready_revision_name
  )
  result = []
  for k in set(spec_dict).union(status_dict):
    spec_splits = spec_dict.get(k, [])
    status_splits = status_dict.get(k, [])
    percent_override = _PercentOverride(
        k, spec_dict, status_splits, combined_status_splits_id
    )
    if k == instance_split.LATEST_REVISION_KEY:
      revision_name = latest_ready_revision_name
      latest = True
    else:
      revision_name = k
      latest = False

    result.append(
        InstanceSplitPair(
            spec_splits, status_splits, revision_name, latest, percent_override
        )
    )
  return sorted(result, key=instance_split.SortKeyFromSplit)
