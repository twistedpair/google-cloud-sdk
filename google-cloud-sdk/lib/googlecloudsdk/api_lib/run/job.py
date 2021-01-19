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
"""Wraps a Cloud Run job message with convenience methods."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum
from googlecloudsdk.api_lib.run import container_resource
from googlecloudsdk.api_lib.run import k8s_object

AUTHOR_ANNOTATION = k8s_object.RUN_GROUP + '/creator'

STARTED_CONDITION = 'Started'
COMPLETED_CONDITION = 'Completed'


class RestartPolicy(enum.Enum):
  NEVER = 'Never'
  ON_FAILRE = 'OnFailure'


class Job(container_resource.ContainerResource):
  """Wraps a Cloud Run job message, making fields more convenient."""

  API_CATEGORY = 'run.googleapis.com'
  KIND = 'Job'
  READY_CONDITION = COMPLETED_CONDITION
  TERMINAL_CONDITIONS = frozenset({STARTED_CONDITION, READY_CONDITION})

  @classmethod
  def New(cls, client, namespace):
    """Produces a new Job object.

    Args:
      client: The Cloud Run API client.
      namespace: str, The serving namespace.

    Returns:
      A new Job object to be deployed.
    """
    ret = super(Job, cls).New(client, namespace)
    ret.instance_spec.containers = [client.MESSAGES_MODULE.Container()]
    return ret

  @property
  def template(self):
    return self.spec.template

  @property
  def author(self):
    return self.annotations.get(AUTHOR_ANNOTATION)

  @property
  def instance_spec(self):
    return self.spec.template.spec

  @property
  def parallelism(self):
    return self.spec.parallelism

  @parallelism.setter
  def parallelism(self, value):
    self.spec.parallelism = value

  @property
  def completions(self):
    return self.spec.completions

  @completions.setter
  def completions(self, value):
    self.spec.completions = value

  @property
  def backoff_limit(self):
    return self.spec.backoffLimit

  @backoff_limit.setter
  def backoff_limit(self, value):
    self.spec.backoffLimit = value

  @property
  def restart_policy(self):
    """Returns the enum version of the restart policy."""
    return RestartPolicy(self.instance_spec.restartPolicy)

  @restart_policy.setter
  def restart_policy(self, enum_value):
    self.instance_spec.restartPolicy = enum_value.value
