# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Utilities for dealing with service resources."""


class Service(object):
  """Value class representing a service resource."""

  _RESOURCE_PATH_PARTS = 2  # project/service

  def __init__(self, project, id_, split):
    self.project = project
    self.id = id_
    self.split = split

  def __eq__(self, other):
    return (type(other) is Service and
            self.project == other.project and self.id == other.id)

  def __ne__(self, other):
    return not self == other

  # TODO(b/25662075): convert to use functools.total_ordering
  def __lt__(self, other):
    return (self.project, self.id) < (other.project, other.id)

  def __le__(self, other):
    return (self.project, self.id) <= (other.project, other.id)

  def __gt__(self, other):
    return (self.project, self.id) > (other.project, other.id)

  def __ge__(self, other):
    return (self.project, self.id) >= (other.project, other.id)

  def __repr__(self):
    return '{0}/{1}'.format(self.project, self.id)
