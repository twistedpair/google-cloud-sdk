# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Contains utilities to support the `gcloud init` command."""
from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.calliope import usage_text
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io


_ENTER_PROJECT_ID_MESSAGE = """\
Enter a Project ID. Note that a Project ID CANNOT be changed later.
Project IDs must be 6-30 characters (lowercase ASCII, digits, or
hyphens) in length and start with a lowercase letter. \
"""
_CREATE_PROJECT_SENTINEL = object()


def _GetProjectIds():
  """Returns a list of project IDs the current user can list.

  Returns:
    list of str, project IDs, or None (if the command fails).
  """
  try:
    return sorted([project.projectId for project in projects_api.List()])
  except Exception as err:  # pylint: disable=broad-except
    log.warn('Listing available projects failed: %s', str(err))
    return None


def _PromptForProjectId(project_ids):
  """Prompt the user for a project ID, based on the list of available IDs.

  Also allows an option to create a project.

  Args:
    project_ids: list of str or None, the project IDs to prompt for. If this
      value is None, the listing was unsuccessful and we prompt the user
      free-form (and do not validate the input). If it's empty, we offer to
      create a project for the user.

  Returns:
    str, the project ID to use, or _CREATE_PROJECT_SENTINEL (if a project should
      be created), or None
  """
  if project_ids is None:
    return console_io.PromptResponse(
        'Enter project id you would like to use:  ') or None
  elif not project_ids:
    if not console_io.PromptContinue(
        'This account has no projects.',
        prompt_string='Would you like to create one?'):
      return None
    return _CREATE_PROJECT_SENTINEL
  else:
    idx = console_io.PromptChoice(
        project_ids + ['Create a new project'],
        message='Pick cloud project to use: ',
        allow_freeform=True,
        freeform_suggester=usage_text.TextChoiceSuggester())
    if idx is None:
      return None
    elif idx == len(project_ids):
      return _CREATE_PROJECT_SENTINEL
    return project_ids[idx]


def _CreateProject(project_id, project_ids):
  if project_ids and project_id in project_ids:
    raise ValueError('Attempting to create a project that already exists.')

  project_ref = resources.REGISTRY.Create(
      'cloudresourcemanager.projects', projectId=project_id)
  try:
    projects_api.Create(project_ref)
  except Exception as err:  # pylint: disable=broad-except
    log.warn('Project creation failed: {err}\n'
             'Please make sure to create the project [{project}] using\n'
             '    $ gcloud projects create {project}\n'
             'or change to another project using\n'
             '    $ gcloud config set project <PROJECT ID>'.format(
                 err=str(err), project=project_id))


def PickProject(preselected=None):
  """Allows user to select a project.

  Args:
    preselected: str, use this value if not None

  Returns:
    str, project_id or None if was not selected.
  """
  project_ids = _GetProjectIds()

  project_id = preselected or _PromptForProjectId(project_ids)
  if project_ids is None or project_id in project_ids or project_id is None:
    return project_id

  if project_id is _CREATE_PROJECT_SENTINEL:
    project_id = console_io.PromptResponse(_ENTER_PROJECT_ID_MESSAGE)
    if not project_id:
      return None
  else:
    if project_ids:
      message = '[{0}] is not one of your projects [{1}]. '.format(
          project_id, ','.join(project_ids))
    else:
      message = 'This account has no projects.'
    if not console_io.PromptContinue(
        message=message, prompt_string='Would you like to create it?'):
      return None

  _CreateProject(project_id, project_ids)
  return project_id
