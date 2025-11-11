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

"""A printer for rollouts that sorts fields according to stage assignment."""


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Any

from apitools.base.py import encoding
from googlecloudsdk.core.resource import custom_printer_base
from googlecloudsdk.core.resource import resource_printer

ROLLOUT_PRINTER_FORMAT = 'rollout'


class RolloutPrinter(
    resource_printer.DefaultPrinter,
    custom_printer_base.CustomPrinterBase,
):
  """A printer for rollouts that sorts fields according to stage assignment."""

  def __init__(self, *args, **kwargs):
    custom_printer_base.CustomPrinterBase.__init__(self, *args, **kwargs)
    resource_printer.DefaultPrinter.__init__(self, *args, **kwargs)

  def Transform(self, record):
    rollout = encoding.MessageToDict(record)
    if 'clusterStatus' in rollout:
      rollout['clusterStatus'] = _sort_cluster_status_by_wave(
          rollout['clusterStatus']
      )
    if 'membershipStates' in rollout:
      rollout['membershipStates'] = _sort_membership_states_by_stage(
          rollout['membershipStates']
      )
    return rollout


# TODO: b/418748521 - this method is only provided for backwards compatibility
# and can be removed once the clusterStatus field is removed.
def _sort_cluster_status_by_wave(
    cluster_status: list[dict[str, Any]],
) -> list[dict[str, Any]]:
  """Sorts a list of cluster statuses by wave assignment."""
  try:
    return sorted(cluster_status, key=lambda s: s['waveAssignment'])
  except KeyError:
    return cluster_status


def _sort_membership_states_by_stage(
    membership_states: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
  """Sorts a map of membership states by stage assignment and returns a list."""
  for m, s in membership_states.items():
    s['membership'] = m

  try:
    return sorted(
        membership_states.values(), key=lambda ms: ms['stageAssignment']
    )
  except KeyError:
    return list(membership_states.values())
