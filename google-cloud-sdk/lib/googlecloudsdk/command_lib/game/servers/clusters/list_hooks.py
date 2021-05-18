# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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

"""List hooks for Cloud Game Servers Cluster."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def ConvertListResponseToViewDataMap(gsc_list, args):
  """Converts the list response to a single-entry map as GameServerClusterView to list of GameServerCluster.

  Args:
    gsc_list: The reference to the list of GameServerCluster.
    args: The parsed args namespace.

  Returns:
    View based table data map.
  """
  view = args.view if hasattr(args, 'view') and args.view else 'basic'
  return {view: gsc_list}
