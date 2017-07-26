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
"""Provides ValueMixin.

ValueMixin provides comparison (including equality) methods and hashing
based on the values of fields.
"""


class ValueMixin(object):
  def __cmp__(self, other):
    # Compare this object to the other one based on the names and values of
    # the fields of both classes. If other is not a class instance then it
    # won't have a __dict__ attribute. We can't establish a proper order then,
    # since we might not have x < y => y > x, but we arbitrarily declare
    # our instances greater than non-instance objects so at least they are not
    # equal.
    if hasattr(other, '__dict__'):
      return self.__dict__.__cmp__(other.__dict__)
    else:
      return 1

  def __hash__(self):
    return hash(frozenset(self.__dict__.items()))

  def __repr__(self):
    # Return a string representation like "MyClass(foo=23, bar='skidoo')".
    d = self.__dict__
    attrs = ['%s=%r' % (key, d[key]) for key in sorted(d)]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(attrs))
