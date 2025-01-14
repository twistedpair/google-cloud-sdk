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
"""Operations on WorkerPool V2 API instance splits."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from typing import List, Dict, Union

from googlecloudsdk.core import exceptions
from googlecloudsdk.generated_clients.gapic_clients.run_v2.types import instance_split


# Designated key value for latest.
# Revisions' names may not be uppercase, so this is distinct.
LATEST_REVISION_KEY = 'LATEST'


class InvalidInstanceSplitSpecificationError(exceptions.Error):
  """Error to indicate an invalid instance split specification."""

  pass


def _GetCurrentSplitsMap(
    splits: List[instance_split.InstanceSplit],
) -> Dict[str, int]:
  """Returns the current instance split percentages into a map."""
  current_splits = {}
  for split in splits:
    if (
        split.type_
        == instance_split.InstanceSplitAllocationType.INSTANCE_SPLIT_ALLOCATION_TYPE_LATEST
    ):
      current_splits[LATEST_REVISION_KEY] = split.percent
    elif (
        split.type_
        == instance_split.InstanceSplitAllocationType.INSTANCE_SPLIT_ALLOCATION_TYPE_REVISION
    ):
      current_splits[split.revision] = split.percent
  return current_splits


def _GetUnspecifiedSplits(
    new_percentages: Dict[str, int],
    current_splits: Dict[str, int],
) -> Dict[str, int]:
  """Returns the instance splits that are in the current splits but not specified in new_percentages."""
  result = {}
  for target, percent in current_splits.items():
    if target not in new_percentages:
      result[target] = percent
  return result


def _ValidateNewSplits(
    new_splits: Dict[str, int], unspecified_targets: Dict[str, int]
):
  """Validates the new instance split percentages."""
  if sum(new_splits.values()) > 100:
    raise InvalidInstanceSplitSpecificationError(
        'The sum of instance split specifications exceeds 100.'
    )

  for target, percent in new_splits.items():
    if percent < 0 or percent > 100:
      raise InvalidInstanceSplitSpecificationError(
          'Instance split specification for {} is {}%, not between 0 and 100'
          .format(target, percent)
      )

  if not unspecified_targets and sum(new_splits.values()) < 100:
    raise InvalidInstanceSplitSpecificationError(
        'Every target with instance split is updated but 100% of total split'
        ' has not been specified.'
    )


def _ValidateCurrentSplits(current_splits: Dict[str, int]):
  """Validates the current instance split percentages."""
  total_percent = 0
  for target, percent in current_splits.items():
    if percent < 0 or percent > 100:
      raise ValueError(
          'Current instance split allocation for {} is {}%, not between 0 and'
          ' 100'.format(target, percent)
      )
    total_percent += percent
  if total_percent != 100:
    raise ValueError(
        'Current instance split allocation of {} is not 100 percent'.format(
            total_percent
        )
    )


def _ModifyUnspecifiedSplits(
    new_splits: Dict[str, int], unspecified_splits: Dict[str, int]
):
  """Modifies the unspecified splits by assigning the remaining split percent proportionally to the original splits."""
  percent_to_assign = 100 - sum(new_splits.values())
  if percent_to_assign == 0:
    return {}

  original_splits_percent = sum(unspecified_splits.values())
  reduction_ratio = float(percent_to_assign) / original_splits_percent
  #
  # We assign instance split to unassigned targets (were seving and
  # have not explicit new percentage assignment). The assignment
  # is proportional to the original split for the each target.
  #
  # reduction_ratio = percent_to_assign / original_splits_percent
  #
  # percent_to_assign
  #    == percent_to_assign_from * reduction_ratio
  #    == sum(unspecified_splits[k] * reduction_ratio)
  #    == sum(unspecified_splits[k] * reduction_ratio)
  modified_splits = {}
  for target, percent in unspecified_splits.items():
    modified_splits[target] = percent * reduction_ratio
  return modified_splits


def _SortKeyFromInstanceSplit(split: instance_split.InstanceSplit):
  """Sorted key function to order InstanceSplit objects by key.

  Args:
    split: A InstanceSplit.

  Returns:
    A value that sorts by revisionName with LATEST_REVISION_KEY
    last.
  """
  if (
      split.type
      == instance_split.InstanceSplitAllocationType.INSTANCE_SPLIT_ALLOCATION_TYPE_LATEST
  ):
    key = LATEST_REVISION_KEY
  else:
    key = split.revision
  return _SortKeyFromKey(key)


def _SortKeyFromKey(key):
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


def _NewRoundingCorrectionPrecedence(key_and_percent):
  """Returns object that sorts in the order we correct split rounding errors.

  The caller specifies explicit split percentages for some revisions and
  this module scales instance split for remaining revisions that are already
  serving instance split up or down to assure that 100% of instance split is
  assigned.
  This scaling can result in non integer percentages that Cloud Run
  does not supprt. We correct by:
    - Trimming the decimal part of float_percent, int(float_percent)
    - Adding an extra 1 percent instance split to enough revisions that have
      had their instance split reduced to get us to 100%

  The returned value sorts in the order we correct revisions:
    1) Revisions with a bigger loss due are corrected before revisions with
       a smaller loss. Since 0 <= loss < 1 we sort by the value:  1 - loss.
    2) In the case of ties revisions with less instance split are corrected
    before
       revisions with more instance split.
    3) In case of a tie revisions with a smaller key are corrected before
       revisions with a larger key.

  Args:
    key_and_percent: tuple with (key, float_percent)

  Returns:
    A value that sorts with respect to values returned for
    other revisions in the order we correct for rounding
    errors.
  """
  key, float_percent = key_and_percent
  return [
      1 - (float_percent - int(float_percent)),
      float_percent,
      _SortKeyFromKey(key),
  ]


def _IntPercentages(float_percentages: Dict[str, int]):
  """Returns rounded integer percentages."""
  rounded_percentages = {
      k: int(float_percentages[k]) for k in float_percentages
  }
  loss = int(round(sum(float_percentages.values()))) - sum(
      rounded_percentages.values()
  )
  correction_precedence = sorted(
      float_percentages.items(), key=_NewRoundingCorrectionPrecedence
  )
  for key, _ in correction_precedence[:loss]:
    rounded_percentages[key] += 1
  return rounded_percentages


def GetUpdatedSplits(
    current_splits: List[instance_split.InstanceSplit],
    new_splits: Dict[str, Union[int, float]],
) -> List[instance_split.InstanceSplit]:
  """Returns the updated instance splits."""
  # Current split status.
  current_splits_map = _GetCurrentSplitsMap(current_splits)
  _ValidateCurrentSplits(current_splits_map)
  # Current split that is not specified in new splits.
  unspecified_splits = _GetUnspecifiedSplits(new_splits, current_splits_map)
  _ValidateNewSplits(new_splits, unspecified_splits)
  # Modify the unspecified splits by proprotinally assigning the remaining
  # split percent to the original splits.
  unspecified_splits_modified = _ModifyUnspecifiedSplits(
      new_splits, unspecified_splits
  )
  new_splits.update(unspecified_splits_modified)
  # Do the detailed correction of rounding up/down the float percentages.
  int_percent_splits = _IntPercentages(new_splits)
  return sorted(
      [
          instance_split.InstanceSplit(
              type_=instance_split.InstanceSplitAllocationType.INSTANCE_SPLIT_ALLOCATION_TYPE_LATEST
              if key == LATEST_REVISION_KEY
              else instance_split.InstanceSplitAllocationType.INSTANCE_SPLIT_ALLOCATION_TYPE_REVISION,
              revision=key if key != LATEST_REVISION_KEY else None,
              percent=percent,
          )
          for key, percent in int_percent_splits.items()
          if percent > 0
      ],
      key=_SortKeyFromInstanceSplit,
  )
