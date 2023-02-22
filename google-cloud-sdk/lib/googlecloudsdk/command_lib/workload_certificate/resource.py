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
"""Base classes for [enable|disable|describe] commands for Feature resource."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.projects import util as project_util
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def Project(number=False):
  """Simple helper for getting the current project.

  Args:
    number: Boolean, whether to return the project number instead of the ID.

  Returns:
    The project ID or project number, as a string.
  """
  project = properties.VALUES.core.project.GetOrFail()
  if number:
    return project_util.GetProjectNumber(project)
  return project


def LocationResourceName(location='global', use_number=False):
  # Location resource name.
  return resources.REGISTRY.Create(
      'workloadcertificate.projects.locations',
      projectsId=Project(use_number),
      locationsId=location,
  ).RelativeName()


def WorkloadCertificateFeatureResourceName(project):
  # Workload Certificate Feature resource name.
  return resources.REGISTRY.Create(
      'workloadcertificate.projects.locations.workloadCertificateFeature',
      projectsId=project,
  ).RelativeName()


def OperationName(name):
  return resources.REGISTRY.ParseRelativeName(
      name, 'workloadcertificate.projects.locations.operations'
  )


def RegistrationResourceName(project, location, workload_registrations_id):
  # Workload Registration resource name.
  return resources.REGISTRY.Create(
      'workloadcertificate.projects.locations.workloadRegistrations',
      projectsId=project,
      locationsId=location,
      workloadRegistrationsId=workload_registrations_id,
  ).RelativeName()
