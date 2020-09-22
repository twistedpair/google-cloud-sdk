# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Helper for JSON-based Kubernetes object wrappers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


class MapObject(object):
  """Base class to wrap dict-like structures and support attributes for keys.

  TODO(b/168654418): Remove this class and add any necessary properties to
  other objects as necessary.
  """

  def __init__(self, props):
    self._props = props

  def __getattr__(self, name):
    if name in ('__iter__', 'next', '__next__', 'items'):
      raise AttributeError
    return self._props.get(name)
