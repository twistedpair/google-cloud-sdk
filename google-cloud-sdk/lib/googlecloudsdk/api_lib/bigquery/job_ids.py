# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Defines the JobIdProvider class.
"""

import abc
import hashlib
import random
import sys
import time

from googlecloudsdk.calliope import exceptions


def GenerateJobRandomId():
  return random.SystemRandom().randint(0, sys.maxint)


def GenerateJobTimeInMs():
  return int(time.time() * 1000)


class JobIdGenerator(object):
  """Base class for job id generators."""
  __metaclass__ = abc.ABCMeta

  def Generate(self, job_configuration):
    return self._DoGenerate(job_configuration)

  @abc.abstractmethod
  def _DoGenerate(self, job_configuration):
    """Generates a job_id to use for job_configuration."""


class JobIdGeneratorRandom(JobIdGenerator):
  """Generates random job ids."""

  def _DoGenerate(self, unused_config):
    return 'bqjob_r{0:08x}_{1:016x}'.format(
        GenerateJobRandomId(),
        GenerateJobTimeInMs())


class JobIdGeneratorFingerprint(JobIdGenerator):
  """Generates job ids that uniquely match the job config."""

  def _Hash(self, config, sha1):
    """Computes the sha1 hash of a dict."""
    keys = config.keys()
    # Python dict enumeration ordering is random. Sort the keys
    # so that we will visit them in a stable order.
    keys.sort()
    for key in keys:
      sha1.update('{0}'.format(key))
      v = config[key]
      if isinstance(v, dict):
        self._Hash(v, sha1)
      elif isinstance(v, list):
        for inner_v in v:
          self._Hash(inner_v, sha1)
      else:
        sha1.update('{0}'.format(v))

  def _DoGenerate(self, config):
    s1 = hashlib.sha1()
    self._Hash(config, s1)
    job_id = 'bqjob_c{0}'.format(s1.hexdigest())
    return job_id


class JobIdGeneratorIncrementing(JobIdGenerator):
  """Generates job ids that increment each time we're asked."""

  def __init__(self, inner):
    self._inner = inner
    self._retry = 0

  def _DoGenerate(self, config):
    self._retry += 1
    return '{0}_{1:d}'.format(self._inner.Generate(config), self._retry)


class JobIdProvider(object):
  """Defines a method providing user-specified or randomly generated job IDs.
  """

  def GetJobId(self, job_id_flag, fingerprint_job_id_flag):
    """Returns the job id or job generator from the flags."""
    if fingerprint_job_id_flag and job_id_flag:
      raise exceptions.InvalidArgumentException(
          'The --fingerprint-job-id flag ',
          'cannot be specified with the --job-id flag')
    if fingerprint_job_id_flag:
      return JobIdGeneratorFingerprint()
    elif job_id_flag is None:
      return JobIdGeneratorIncrementing(JobIdGeneratorRandom())
    elif job_id_flag:
      return job_id_flag
    else:
      # User specified a job id, but it was empty. Let the
      # server come up with a job id.
      return None
