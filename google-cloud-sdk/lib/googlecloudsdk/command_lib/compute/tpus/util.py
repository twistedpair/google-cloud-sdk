# -*- coding: utf-8 -*- #
# Copyright 2017 Google LLC. All Rights Reserved.
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
"""CLI Utilities for cloud tpu commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def ListTopologiesResponseHook(response, args):
  """Reformat to extract topologies and sort by acceleratorType."""
  del args
  results = []
  for accelerator_type in response:
    for accelerator_config in accelerator_type.acceleratorConfigs:
      results += [{
          'topology': accelerator_config.topology,
          'type': accelerator_config.type,
          'acceleratorType': accelerator_type.type
      }]
  results.sort(key=lambda x: (int(x['acceleratorType'].split('-')[1])))
  return results
