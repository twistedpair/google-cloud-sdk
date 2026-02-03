# -*- coding: utf-8 -*- #
# Copyright 2015 Google LLC. All Rights Reserved.
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

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import enum
import re

from apitools.base.py import list_pager
from apitools.base.py.exceptions import HttpForbiddenError
from googlecloudsdk.api_lib.cloudresourcemanager import organizations
from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.api_lib.cloudresourcemanager import projects_util
from googlecloudsdk.api_lib.iam import policies
from googlecloudsdk.api_lib.resource_manager import folders
from googlecloudsdk.api_lib.resource_manager import tags
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.projects import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources

PROJECTS_COLLECTION = 'cloudresourcemanager.projects'
PROJECTS_API_VERSION = projects_util.DEFAULT_API_VERSION
_CLOUD_CONSOLE_LAUNCH_DATE = datetime.datetime(2012, 10, 11)
LIST_FORMAT = """
    table(
      projectId:sort=1,
      name,
      projectNumber,
      tags.environment:label='ENVIRONMENT'
    )
"""

_VALID_PROJECT_REGEX = re.compile(
    r'^'
    # An optional domain-like component, ending with a colon, e.g.,
    # google.com:
    r'(?:(?:[-a-z0-9]{1,63}\.)*(?:[a-z](?:[-a-z0-9]{0,61}[a-z0-9])?):)?'
    # Followed by a required identifier-like component, for example:
    #   waffle-house    match
    #   -foozle        no match
    #   Foozle         no match
    # We specifically disallow project number, even though some GCP backends
    # could accept them.
    # We also allow a leading digit as some legacy project ids can have
    # a leading digit.
    r'(?:(?:[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?))'
    r'$')


@enum.unique
class Environment(enum.Enum):
  PRODUCTION = 'Production'
  DEVELOPMENT = 'Development'
  TEST = 'Test'
  STAGING = 'Staging'


_ENV_STANDARD_TO_VARIANT_VALUE_MAPPING = {
    # Production
    Environment.PRODUCTION: {'Prod', 'prod', 'Production', 'production'},
    # Development
    Environment.DEVELOPMENT: {'Dev', 'dev', 'Development', 'development'},
    # Test
    Environment.TEST: {
        'Test',
        'test',
        'Testing',
        'testing QA',
        'qa',
        'Quality assurance',
        'quality assurance',
    },
    # Staging
    Environment.STAGING: {'Staging', 'staging', 'Stage', 'stage'},
}

_ENV_VARIANT_TO_STANDARD_VALUE_MAPPING = {}
for (
    standard_value,
    variant_values,
) in _ENV_STANDARD_TO_VARIANT_VALUE_MAPPING.items():
  for variant_value in variant_values:
    _ENV_VARIANT_TO_STANDARD_VALUE_MAPPING[variant_value] = standard_value


def ValidateProjectIdentifier(project):
  """Checks to see if the project string is valid project name or number."""
  if not isinstance(project, str):
    return False

  if project.isdigit() or _VALID_PROJECT_REGEX.match(project):
    return True

  return False


def GetProjectNumber(project_id):
  return projects_api.Get(ParseProject(project_id)).projectNumber


def ParseProject(project_id, api_version=PROJECTS_API_VERSION):
  # Override the default API map version so we can increment API versions on a
  # API interface basis.
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName('cloudresourcemanager', api_version)
  return registry.Parse(
      None, params={'projectId': project_id}, collection=PROJECTS_COLLECTION)


def ProjectsUriFunc(resource, api_version=PROJECTS_API_VERSION):
  project_id = (
      resource.get('projectId', None)
      if isinstance(resource, dict) else resource.projectId)
  ref = ParseProject(project_id, api_version)
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
    base_ = SimplifyName(name)
    # Cloud Console generates the two following candidates in the opposite
    # order, but they are validating uniqueness and we're not, so we put the
    # "more unique" suggestion first.
    yield base_ + '-' + CloudConsoleNowString()
    yield base_
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


def GetDetailedHelpForRemoveIamPolicyBinding():
  """Returns detailed_help for a remove-iam-policy-binding command."""
  detailed_help = iam_util.GetDetailedHelpForRemoveIamPolicyBinding(
      'project', 'example-project-id-1', condition=True
  )
  detailed_help[
      'DESCRIPTION'
  ] += ' One binding consists of a member, a role and an optional condition.'
  detailed_help['API REFERENCE'] = (
      'This command uses the cloudresourcemanager/v1 API. The full'
      ' documentation for this API can be found at:'
      ' https://cloud.google.com/resource-manager'
  )
  return detailed_help


def SetIamPolicyFromFileHook(ref, args, request):
  """Hook to perserve SetIAMPolicy behavior for declarative surface."""
  del ref
  del args
  update_mask = request.setIamPolicyRequest.updateMask
  if update_mask:
    # To preserve the existing set-iam-policy behavior of always overwriting
    # bindings and etag, add bindings and etag to update_mask.
    mask_fields = update_mask.split(',')
    if 'bindings' not in mask_fields:
      mask_fields.append('bindings')

    if 'etag' not in update_mask:
      mask_fields.append('etag')
    request.setIamPolicyRequest.updateMask = ','.join(mask_fields)
  return request


def GetIamPolicyWithAncestors(project_id, include_deny, release_track):
  """Get IAM policy for given project and its ancestors.

  Args:
    project_id: project id
    include_deny: boolean that represents if we should show the deny policies in
      addition to the grants
    release_track: which release track, include deny is only supported for ALPHA
      or BETA

  Returns:
    IAM policy for given project and its ancestors
  """
  iam_policies = []
  ancestry = projects_api.GetAncestry(project_id)

  try:
    for resource in ancestry.ancestor:
      resource_type = resource.resourceId.type
      resource_id = resource.resourceId.id
      # this is the given project
      if resource_type == 'project':
        project_ref = ParseProject(project_id)
        iam_policies.append({
            'type': 'project',
            'id': project_id,
            'policy': projects_api.GetIamPolicy(project_ref)
        })
        if include_deny:
          deny_policies = policies.ListDenyPolicies(project_id, 'project',
                                                    release_track)
          for deny_policy in deny_policies:
            iam_policies.append({
                'type': 'project',
                'id': project_id,
                'policy': deny_policy
            })
      if resource_type == 'folder':
        iam_policies.append({
            'type': resource_type,
            'id': resource_id,
            'policy': folders.GetIamPolicy(resource_id)
        })
        if include_deny:
          deny_policies = policies.ListDenyPolicies(resource_id, 'folder',
                                                    release_track)
          for deny_policy in deny_policies:
            iam_policies.append({
                'type': 'folder',
                'id': resource_id,
                'policy': deny_policy
            })
      if resource_type == 'organization':
        iam_policies.append({
            'type': resource_type,
            'id': resource_id,
            'policy': organizations.Client().GetIamPolicy(resource_id),
        })
        if include_deny:
          deny_policies = policies.ListDenyPolicies(resource_id, 'organization',
                                                    release_track)
          for deny_policy in deny_policies:
            iam_policies.append({
                'type': 'organization',
                'id': resource_id,
                'policy': deny_policy
            })

    return iam_policies
  except HttpForbiddenError:
    raise exceptions.AncestorsIamPolicyAccessDeniedError(
        'User is not permitted to access IAM policy for one or more of the'
        ' ancestors')


def GetEnvironmentTag(project_id):
  """Returns the environment tag for the project id."""
  messages = tags.TagMessages()
  project_ref = ParseProject(project_id)
  resource_name = '//cloudresourcemanager.googleapis.com/{}'.format(
      project_ref.RelativeName()
  )
  try:
    effective_tags_request = (
        messages.CloudresourcemanagerEffectiveTagsListRequest(
            parent=resource_name
        )
    )
    effective_tags_response = list_pager.YieldFromList(
        tags.EffectiveTagsService(),
        effective_tags_request,
        batch_size_attribute='pageSize',
        field='effectiveTags',
    )

    for effective_tag in effective_tags_response:
      if effective_tag.namespacedTagKey.endswith('/environment'):
        return (
            effective_tag.namespacedTagKey.split('/')[-1],
            effective_tag.namespacedTagValue.split('/')[-1],
        )
  except Exception as e:  # pylint: disable=broad-except
    # Gracefully print a warning message.
    log.info(
        'Unable to get environment tag for project [{0}]: {1}'.format(
            project_id, e
        )
    )
  return (None, None)


def GetStandardEnvironmentValue(value):
  return _ENV_VARIANT_TO_STANDARD_VALUE_MAPPING.get(value, None)


def PrintEnvironmentTagMessage(project_id):
  """Prints environment tag message given project ID."""
  env_tag_key, env_tag_value = GetEnvironmentTag(project_id)
  if not env_tag_key:
    log.status.Print(
        "Project '{0}' lacks an 'environment' tag. Please create or add a tag"
        " with key 'environment' and a value like 'Production',"
        " 'Development', 'Test', or 'Staging'. Add an 'environment' tag using"
        " `gcloud resource-manager tags bindings create`. See"
        " https://cloud.google.com/resource-manager/docs/creating-managing-projects#designate_project_environments_with_tags"
        " for details.".format(project_id)
    )
    return

  env_standard_value = GetStandardEnvironmentValue(
      env_tag_value
  )
  if not env_standard_value:
    log.status.Print(
        "Project '{0}' has an 'environment' tag with an"
        " unrecognized value. Please use a standard value such as"
        " 'Production', 'Development', 'Test', or 'Staging'. You can update"
        " the tag value using `gcloud resource-manager tags bindings"
        " create`. Refer to https://cloud.google.com/resource-manager/docs/"
        "creating-managing-projects#designate_project_environments_with_tags"
        " for more guidance.".format(project_id)
    )
    return

  if env_standard_value == Environment.PRODUCTION:
    log.status.Print(
        "Caution: Project '{0}' is designated as '{2}'(tagged 'environment:"
        " {1}'). Making changes could affect your '{2}' apps."
        ' Learn more at https://cloud.google.com/resource-manager/docs/'
        'creating-managing-projects#designate_project_environments_with_tags'
        .format(
            project_id, env_tag_value, env_standard_value.value
        )
    )
  else:
    log.status.Print(
        "Caution: Project '{0}' is designated as '{2}'(tagged"
        " 'environment: {1}'). Making changes could affect your '{2}'"
        ' apps. If incorrect, you can update it by managing the tag'
        " binding for the 'environment' key using `gcloud"
        " resource-manager tags bindings create`. Learn more at"
        ' https://cloud.google.com/resource-manager/docs/creating-managing-projects#designate_project_environments_with_tags'
        .format(
            project_id, env_tag_value, env_standard_value.value
        )
    )
