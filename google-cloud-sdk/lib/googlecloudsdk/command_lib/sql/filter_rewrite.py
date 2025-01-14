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

"""Cloud SQL resource filter expression rewrite backend."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core.resource import resource_expr_rewrite
from googlecloudsdk.core.util import times
import six


# If _STRING_FIELDS and _TIME_FIELDS are out of sync with the API then --filter
# expressions will still work, but parts may be done client side, degrading
# performance.

_STRING_FIELDS = frozenset([
    'location',
    'instance',
    'type',
])

_TIME_FIELDS = frozenset([
    'backupInterval.startTime',
    'instanceDeletionTime',
])


class Backend(resource_expr_rewrite.Backend):
  """Cloud Build resource filter expression rewrite backend."""

  def _RewriteStrings(self, key, op, operand):
    """Rewrites <key op operand>."""
    terms = []
    for arg in operand if isinstance(operand, list) else [operand]:
      terms.append('{key}{op}{arg}'.format(key=key, op=op,
                                           arg=self.Quote(arg, always=True)))
    if len(terms) > 1:
      return '{terms}'.format(terms=' OR '.join(terms))
    return terms[0]

  def _RewriteTimes(self, key, op, operand):
    """Rewrites <*Time op operand>."""
    try:
      dt = times.ParseDateTime(operand)
    except ValueError as e:
      raise ValueError(
          '{operand}: date-time value expected for {key}: {error}'.format(
              operand=operand, key=key, error=six.text_type(e)
          )
      )
    dt_string = times.FormatDateTime(dt, '%Y-%m-%dT%H:%M:%S.%3f%Ez', times.UTC)
    return '{key}{op}{dt_string}'.format(
        key=key, op=op, dt_string=self.Quote(dt_string, always=True)
    )

  def RewriteTerm(self, key, op, operand, key_type):
    """Rewrites <key op operand>."""
    del key_type  # unused in RewriteTerm

    if op not in ['<', '<=', '=', '!=', '>=', '>', ':']:
      return None
    name = key
    if name in _STRING_FIELDS:
      if op not in ['=', '!=']:
        return None
      return self._RewriteStrings(name, op, operand)
    elif name in _TIME_FIELDS:
      if op not in ['<', '<=', '=', '!=', '>=', '>']:
        return None
      return self._RewriteTimes(name, op, operand)
    return None
