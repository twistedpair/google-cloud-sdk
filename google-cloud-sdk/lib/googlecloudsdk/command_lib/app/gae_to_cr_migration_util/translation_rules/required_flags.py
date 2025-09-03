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

"""Add required flags to output gcloud run deploy command."""

from collections.abc import Mapping, Sequence


def translate_add_required_flags(
    input_data: Mapping[str, any],
) -> Sequence[str]:
  """Add required flags to gcloud run deploy command."""
  return [
      '--allow-unauthenticated',
      f'--labels={_get_labels()}',
      f'--base-image={input_data["runtime"]}'
      if 'runtime' in input_data
      else '',
  ]


def _get_labels() -> str:
  """Get labels for gcloud run deploy command."""
  return ','.join([
      'migrated-from',
      'gcloud-gae2cr-version=1',
  ])
