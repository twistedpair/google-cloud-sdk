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

"""Common utility functions for all projects commands."""

import datetime
import re
from googlecloudsdk.core import resources


PROJECTS_COLLECTION = 'cloudresourcemanager.projects'
PROJECTS_API_VERSION = 'v1'
_CLOUD_CONSOLE_LAUNCH_DATE = datetime.datetime(2012, 10, 11)
LIST_FORMAT = """
    table(
      projectId:sort=1,
      name,
      projectNumber
    )
"""


def ParseProject(project_id):
  # Override the default API map version so we can increment API versions on a
  # API interface basis.
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName('cloudresourcemanager', PROJECTS_API_VERSION)
  return registry.Parse(project_id, collection=PROJECTS_COLLECTION)


def ProjectsUriFunc(resource):
  ref = ParseProject(resource.projectId)
  return ref.SelfLink()


def IdFromName(project_name):
  """Returns a candidate id for a new project with the given name.

  Args:
    project_name: Human-readable name of the project.

  Returns:
    A candidate project id, or 'None' if no reasonable candidate is found.
  """

  def SimplifyName(name):
    name = name.lower()
    name = re.sub(r'[^a-z0-9\s/._-]', '', name, flags=re.U)
    name = re.sub(r'[\s/._-]+', '-', name, flags=re.U)
    name = name.lstrip('-0123456789').rstrip('-')
    return name

  def CloudConsoleNowString():
    now = datetime.datetime.utcnow()
    return '{}{:02}'.format((now - _CLOUD_CONSOLE_LAUNCH_DATE).days, now.hour)

  def GenIds(name):
    base = SimplifyName(name)
    # Cloud Console generates the two following candidates in the opposite
    # order, but they are validating uniqueness and we're not, so we put the
    # "more unique" suggestion first.
    yield base + '-' + CloudConsoleNowString()
    yield base
    # Cloud Console has an four-tier "allocate an unused id" architecture for
    # coining ids *not* based on the project name. This might be sensible for
    # an interface where ids are expected to be auto-generated, but seems like
    # major overkill (and a shift in paradigm from "assistant" to "wizard") for
    # gcloud. -shearer@ 2016-11

  def IsValidId(i):
    # TODO(b/32950431) could check availability of id
    return 6 <= len(i) <= 30

  for i in GenIds(project_name):
    if IsValidId(i):
      return i
  return None
