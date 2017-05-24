# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Genomics resource filter expression rewrite backend."""

from googlecloudsdk.api_lib.genomics import genomics_util
from googlecloudsdk.core.resource import resource_expr_rewrite
from googlecloudsdk.core.util import times


def _RewriteTimeTerm(key, op, operand):
  """Rewrites <createTime op operand>."""
  if op not in ['<', '<=', '=', ':', '>=', '>']:
    return None
  try:
    dt = times.ParseDateTime(operand)
  except ValueError as e:
    raise ValueError(
        '{operand}: date-time value expected for {key}: {error}'
        .format(operand=operand, key=key, error=str(e)))
  seconds = int(times.GetTimeStampFromDateTime(dt))
  if op == ':':
    op = '='
  elif op == '<':
    op = '<='
    seconds -= 1
  elif op == '>':
    op = '>='
    seconds += 1
  return '{key} {op} {seconds}'.format(key=key, op=op, seconds=seconds)


class Backend(resource_expr_rewrite.BackendBase):
  """Genomics resource filter expression rewrite backend."""

  def Rewrite(self, expr, defaults=None):
    """Add a project id restriction to the backend rewrite."""
    frontend, backend = super(Backend, self).Rewrite(expr, defaults=defaults)

    # Add a project id restriction.
    if backend:
      backend += ' AND '
    else:
      backend = ''
    backend += 'projectId={0}'.format(genomics_util.GetProjectId())

    return frontend, backend

  def RewriteAND(self, left, right):
    """Rewrites <left AND right>."""
    return '{left} AND {right}'.format(left=left, right=right)

  def RewriteTerm(self, key, op, operand):
    """Rewrites <key op operand>."""
    if key == 'createTime':
      return _RewriteTimeTerm(key, op, operand)
    return None
