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

"""Base classes for checks."""

import abc


class Checker(object):
  """Base class for a single check."""

  __metaclass__ = abc.ABCMeta

  @abc.abstractproperty
  def issue(self):
    """The aspect of the user's machine that is being checked."""

  @abc.abstractmethod
  def Check(self):
    """Runs a single check and returns the result and an optional fix.

    A tuple in which the first element is expected to behave like a
    check_base.CheckResult object and the second is a function that can be
    used to fix any error. The second element may optionally be None, if the
    check passed or if there is no applicable fix. If there is a fix
    function it is assumed that it will return True if there are changes
    made that warrant running a check again.
    """


class CheckResult(object):
  """Holds information about the result of a single check."""

  def __init__(self, passed, message='', failures=None):
    self.passed = passed
    self.message = message
    self.failures = failures or []


class Failure(object):

  def __init__(self, message='', exception=None):
    self.message = message
    self.exception = exception
