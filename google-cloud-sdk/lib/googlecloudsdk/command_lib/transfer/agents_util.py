# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Utility classes and functions for STS transfer agents."""

import enum


class ContainerManager(enum.Enum):
  """Container manager to use for the agent."""

  DOCKER = 'docker'
  PODMAN = 'podman'

  @classmethod
  def from_args(cls, args, flag_name='container_manager'):
    """Returns the container manager attribute from the args."""
    container_manager_arg = getattr(args, flag_name, cls.DOCKER.value)
    return ContainerManager(container_manager_arg)
