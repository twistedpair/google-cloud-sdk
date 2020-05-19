# Lint as: python3 # -*- coding: utf-8 -*- #
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
"""Generic implementations of Apigee Management APIs."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.apigee import request


class BaseClient(object):
  """Base class for Apigee Management API clients."""
  _entity_path = None

  @classmethod
  def List(cls, identifiers=None):
    if cls._entity_path is None:
      raise NotImplementedError("%s class must provide an entity path." % cls)
    return request.ResponseToApiRequest(identifiers or {},
                                        cls._entity_path[:-1],
                                        cls._entity_path[-1])

  @classmethod
  def Describe(cls, identifiers=None):
    if cls._entity_path is None:
      raise NotImplementedError("%s class must provide an entity path." % cls)
    return request.ResponseToApiRequest(identifiers or {}, cls._entity_path)
