# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""This file provides util to decorate output of functions command."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools
from apitools.base.py import encoding


def DecorateV1FunctionWithUpgradeInfo(v1_func, upgrade_info):
  """Decorate gen1 function in v1 format with given upgrade info.

  Args:
    v1_func: A gen1 function retrieved from v1 API.
    upgrade_info: An object containing a function's eligibility for gen1 to gen2
      migration and current state of migration for function undergoing
      migration. See http://shortn/_wrB4FUk8nE.

  Returns:
    Gen1 function with upgrade info decorated.
  """
  v1_dict = encoding.MessageToDict(v1_func)
  v1_dict["upgradeInfo"] = upgrade_info
  return v1_dict


def DecorateV1GeneratorWithUpgradeInfo(v1_generator, v2_generator):
  """Decorate upgrade info for 1st gen functions given the results from v2 API.

  Args:
    v1_generator: Generator, generating gen1 function retrieved from v1 API.
    v2_generator: Generator, generating gen1 function retrieved from v2 API.

  Yields:
    Gen1 function with upgrade info decorated.
  """
  gen1_generator = sorted(
      itertools.chain(v1_generator, v2_generator), key=lambda f: f.name
  )
  for _, func_gen in itertools.groupby(gen1_generator, key=lambda f: f.name):
    func_list = list(func_gen)
    if len(func_list) < 2:
      # If this is v2 function, upgrade info should have been included.
      # No decoration needed. Yield directly.
      # If this is v1 function, no corresponding v2 function is found,
      # so there is no upgrade info we have use to decorate. Yield directly.
      yield func_list[0]
    else:
      v1_func, v2_func = func_list
      yield DecorateV1FunctionWithUpgradeInfo(v1_func, v2_func.upgradeInfo)
