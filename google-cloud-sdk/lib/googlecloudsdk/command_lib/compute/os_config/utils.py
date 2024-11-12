# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Utility functions for GCE OS Config commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from enum import Enum

from apitools.base.py import encoding
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.util.args import common_args
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
import six


class InstanceDetailsStates(Enum):
  """Indicates instance progress during a patch job execution."""
  NOTIFIED = 1
  PATCHING = 2
  FINISHED = 3


INSTANCE_DETAILS_KEY_MAP = {
    # Alpha mapping
    'instancesAcked': InstanceDetailsStates.NOTIFIED,
    'instancesApplyingPatches': InstanceDetailsStates.PATCHING,
    'instancesDownloadingPatches': InstanceDetailsStates.PATCHING,
    'instancesFailed': InstanceDetailsStates.FINISHED,
    'instancesInactive': InstanceDetailsStates.FINISHED,
    'instancesNotified': InstanceDetailsStates.NOTIFIED,
    'instancesPending': InstanceDetailsStates.NOTIFIED,
    'instancesRebooting': InstanceDetailsStates.PATCHING,
    'instancesStarted': InstanceDetailsStates.PATCHING,
    'instancesSucceeded': InstanceDetailsStates.FINISHED,
    'instancesSucceededRebootRequired': InstanceDetailsStates.FINISHED,
    'instancesTimedOut': InstanceDetailsStates.FINISHED,
    'instancesRunningPrePatchStep': InstanceDetailsStates.PATCHING,
    'instancesRunningPostPatchStep': InstanceDetailsStates.PATCHING,
    'instancesNoAgentDetected': InstanceDetailsStates.FINISHED,

    # Beta mapping
    'ackedInstanceCount': InstanceDetailsStates.NOTIFIED,
    'applyingPatchesInstanceCount': InstanceDetailsStates.PATCHING,
    'downloadingPatchesInstanceCount': InstanceDetailsStates.PATCHING,
    'failedInstanceCount': InstanceDetailsStates.FINISHED,
    'inactiveInstanceCount': InstanceDetailsStates.FINISHED,
    'notifiedInstanceCount': InstanceDetailsStates.NOTIFIED,
    'pendingInstanceCount': InstanceDetailsStates.NOTIFIED,
    'rebootingInstanceCount': InstanceDetailsStates.PATCHING,
    'startedInstanceCount': InstanceDetailsStates.PATCHING,
    'succeededInstanceCount': InstanceDetailsStates.FINISHED,
    'succeededRebootRequiredInstanceCount': InstanceDetailsStates.FINISHED,
    'timedOutInstanceCount': InstanceDetailsStates.FINISHED,
    'prePatchStepInstanceCount': InstanceDetailsStates.PATCHING,
    'postPatchStepInstanceCount': InstanceDetailsStates.PATCHING,
    'noAgentDetectedInstanceCount': InstanceDetailsStates.FINISHED,
}

_GCS_PREFIXES = ('gs://', 'https://www.googleapis.com/storage/v1/',
                 'https://storage.googleapis.com/')

_MAX_LIST_BATCH_SIZE = 100


def GetListBatchSize(args):
  """Returns the batch size for listing resources."""
  if args.page_size:
    return args.page_size
  elif args.limit:
    return min(args.limit, _MAX_LIST_BATCH_SIZE)
  else:
    return None


def GetParentUriPath(parent_name, parent_id):
  """Returns the URI path of a GCP parent resource."""
  return '/'.join([parent_name, parent_id])


def GetProjectUriPath(project):
  """Returns the URI path of a GCP project."""
  return GetParentUriPath('projects', project)


def GetProjectLocationUriPath(project, location):
  """Returns the URI path of projects/*/locations/*."""
  return GetParentUriPath(
      GetParentUriPath('projects', project),
      GetParentUriPath('locations', location))


def GetFolderUriPath(folder):
  """Returns the URI path of a GCP folder."""
  return GetParentUriPath('folders', folder)


def GetOrganizationUriPath(organization):
  """Returns the URI path of a GCP organization."""
  return GetParentUriPath('organizations', organization)


def GetPatchJobUriPath(project, patch_job):
  """Returns the URI path of an osconfig patch job."""
  return '/'.join(['projects', project, 'patchJobs', patch_job])


def GetResourceName(uri):
  """Returns the name of a GCP resource from its URI."""
  return uri.split('/')[3]


def GetGuestPolicyRelativePath(parent, guest_policy):
  """Returns the relative path of an osconfig guest policy."""
  return '/'.join([parent, 'guestPolicies', guest_policy])


def GetOsPolicyAssignmentRelativePath(parent, os_policy_assignment):
  """Returns the relative path of an osconfig os policy assignment."""
  return '/'.join([parent, 'osPolicyAssignments', os_policy_assignment])


def GetApiMessage(api_version):
  """Returns the messages module with the given api_version."""
  return apis.GetMessagesModule('osconfig', api_version)


def GetApiVersion(args):
  """Return api version for the corresponding release track."""
  release_track = args.calliope_command.ReleaseTrack()

  if release_track == base.ReleaseTrack.ALPHA:
    return 'v1alpha'
  elif release_track == base.ReleaseTrack.BETA:
    return 'v1beta'
  elif release_track == base.ReleaseTrack.GA:
    return 'v1'
  else:
    raise core_exceptions.UnsupportedReleaseTrackError(release_track)


def GetApiVersionV2(args):
  """Return v2 api version for the corresponding release track."""
  release_track = args.calliope_command.ReleaseTrack()

  if release_track == base.ReleaseTrack.ALPHA:
    return 'v2alpha'
  elif release_track == base.ReleaseTrack.BETA:
    return 'v2beta'
  elif release_track == base.ReleaseTrack.GA:
    return 'v2'
  else:
    raise core_exceptions.UnsupportedReleaseTrackError(release_track)


def GetOperationDescribeCommandFormat(args):
  """Returns api version for the corresponding release track."""
  release_track = args.calliope_command.ReleaseTrack()

  if release_track == base.ReleaseTrack.ALPHA:
    return ('To check operation status, run: gcloud alpha compute os-config '
            'os-policy-assignments operations describe {}')
  elif release_track == base.ReleaseTrack.GA:
    return (
        'To check operation status, run: gcloud compute os-config '
        'os-policy-assignments operations describe {}')
  else:
    raise core_exceptions.UnsupportedReleaseTrackError(release_track)


def AddResourceParentArgs(parser, noun, verb):
  """Adds project, folder, and organization flags to the parser."""
  parent_resource_group = parser.add_group(
      help="""\
      The scope of the {}. If a scope is not specified, the current project is
      used as the default.""".format(noun),
      mutex=True,
  )
  common_args.ProjectArgument(
      help_text_to_prepend='The project of the {} {}.'.format(noun, verb),
      help_text_to_overwrite="""\
      The project name to use. If a project name is not specified, then the
      current project is used. The current project can be listed using gcloud
      config list --format='text(core.project)' and can be set using gcloud
      config set project PROJECTID.

      `--project` and its fallback `{core_project}` property play two roles. It
      specifies the project of the resource to operate on, and also specifies
      the project for API enablement check, quota, and billing. To specify a
      different project for quota and billing, use `--billing-project` or
      `{billing_project}` property.
      """.format(
          core_project=properties.VALUES.core.project,
          billing_project=properties.VALUES.billing.quota_project)).AddToParser(
              parent_resource_group)
  parent_resource_group.add_argument(
      '--folder',
      metavar='FOLDER_ID',
      type=str,
      help='The folder of the {} {}.'.format(noun, verb),
  )
  parent_resource_group.add_argument(
      '--organization',
      metavar='ORGANIZATION_ID',
      type=str,
      help='The organization of the {} {}.'.format(noun, verb),
  )


def GetPatchDeploymentUriPath(project, patch_deployment):
  """Returns the URI path of an osconfig patch deployment."""
  return '/'.join(['projects', project, 'patchDeployments', patch_deployment])


def GetGuestPolicyUriPath(parent_type, parent_name, policy_id):
  """Returns the URI path of an osconfig guest policy."""
  return '/'.join([parent_type, parent_name, 'guestPolicies', policy_id])


def GetResourceAndUpdateFieldsFromFile(file_path, resource_message_type):
  """Returns the resource message and update fields in file."""
  try:
    resource_to_parse = yaml.load_path(file_path)
  except yaml.YAMLParseError as e:
    raise exceptions.BadFileException(
        'Policy config file [{0}] cannot be parsed. {1}'.format(
            file_path, six.text_type(e)))
  except yaml.FileLoadError as e:
    raise exceptions.BadFileException(
        'Policy config file [{0}] cannot be opened or read. {1}'.format(
            file_path, six.text_type(e)))

  if not isinstance(resource_to_parse, dict):
    raise exceptions.BadFileException(
        'Policy config file [{0}] is not a properly formatted YAML or JSON '
        'file.'.format(file_path))

  update_fields = list(resource_to_parse.keys())

  try:
    resource = encoding.PyValueToMessage(resource_message_type,
                                         resource_to_parse)
  except (AttributeError) as e:
    raise exceptions.BadFileException(
        'Policy config file [{0}] is not a properly formatted YAML or JSON '
        'file. {1}'.format(file_path, six.text_type(e)))

  return (resource, update_fields)


def GetGcsParams(arg_name, path):
  """Returns information for a Google Cloud Storage object.

  Args:
      arg_name: The name of the argument whose value may be a GCS object path.
      path: A string whose value may be a GCS object path.
  """
  obj_ref = None
  for prefix in _GCS_PREFIXES:
    if path.startswith(prefix):
      obj_ref = resources.REGISTRY.Parse(path)
      break

  if not obj_ref:
    return None

  if not hasattr(obj_ref, 'bucket') or not hasattr(obj_ref, 'object'):
    raise exceptions.InvalidArgumentException(
        arg_name,
        'The provided Google Cloud Storage path [{}] is invalid.'.format(path))

  obj_str = obj_ref.object.split('#')
  if len(obj_str) != 2 or not obj_str[1].isdigit():
    raise exceptions.InvalidArgumentException(
        arg_name,
        'The provided Google Cloud Storage path [{}] does not contain a valid '
        'generation number.'.format(path))

  return {
      'bucket': obj_ref.bucket,
      'object': obj_str[0],
      'generationNumber': int(obj_str[1]),
  }


def ParseOSConfigAssignmentFile(ref, args, req):
  """Returns modified request with parsed OS policy assignment and update mask."""
  del ref
  api_version = GetApiVersion(args)
  messages = GetApiMessage(api_version)
  (policy_assignment_config,
   update_fields) = GetResourceAndUpdateFieldsFromFile(
       args.file, messages.OSPolicyAssignment)
  req.oSPolicyAssignment = policy_assignment_config
  update_fields.sort()
  if 'update' in args.command_path:
    req.updateMask = ','.join(update_fields)
  return req


def GetOrchestrationScopeMessage(messages, api_version):
  """Returns the orchestration scope message for the given API version."""
  if api_version == 'v2alpha':
    return messages.GoogleCloudOsconfigV2alphaOrchestrationScope()
  elif api_version == 'v2beta':
    return messages.GoogleCloudOsconfigV2betaOrchestrationScope()
  elif api_version == 'v2':
    return messages.GoogleCloudOsconfigV2OrchestrationScope()
  else:
    raise core_exceptions.UnsupportedReleaseTrackError(api_version)


def GetOrchestrationScopeSelectorMessage(messages, api_version):
  """Returns the orchestration scope selector message for the given API version."""
  if api_version == 'v2alpha':
    return messages.GoogleCloudOsconfigV2alphaOrchestrationScopeSelector()
  elif api_version == 'v2beta':
    return messages.GoogleCloudOsconfigV2betaOrchestrationScopeSelector()
  elif api_version == 'v2':
    return messages.GoogleCloudOsconfigV2OrchestrationScopeSelector()
  else:
    raise core_exceptions.UnsupportedReleaseTrackError(api_version)


def GetResourceHierarchySelectorMessage(messages, api_version):
  """Returns the resource hierarchy selector message for the given API version."""
  if api_version == 'v2alpha':
    return (
        messages.GoogleCloudOsconfigV2alphaOrchestrationScopeResourceHierarchySelector()
    )
  elif api_version == 'v2beta':
    return (
        messages.GoogleCloudOsconfigV2betaOrchestrationScopeResourceHierarchySelector()
    )
  elif api_version == 'v2':
    return (
        messages.GoogleCloudOsconfigV2OrchestrationScopeResourceHierarchySelector()
    )
  else:
    raise core_exceptions.UnsupportedReleaseTrackError(api_version)


def GetLocationSelectorMessage(messages, api_version):
  """Returns the location selector message for the given API version."""
  if api_version == 'v2alpha':
    return (
        messages.GoogleCloudOsconfigV2alphaOrchestrationScopeLocationSelector()
    )
  elif api_version == 'v2beta':
    return (
        messages.GoogleCloudOsconfigV2betaOrchestrationScopeLocationSelector()
    )
  elif api_version == 'v2':
    return messages.GoogleCloudOsconfigV2OrchestrationScopeLocationSelector()
  else:
    raise core_exceptions.UnsupportedReleaseTrackError(api_version)


def ModifyOrchestratorPolicySetSelectors(
    args, req, messages, api_version, orchestrator, use_clear=False
):
  """Sets selectors inside policy orchestrator.

  Args:
    args: args to the command
    req: request
    messages: messages for selected v2 API version
    api_version: api version
    orchestrator: orchestrator to set selectors in
    use_clear: if true, clear_projects flag is used to clear selectors
    (optional)

  Returns:
    modified request, boolean  indicating if selectors were set
  """
  selectors_set = (
      args.include_projects
      or (use_clear and args.clear_projects)
      or args.include_folders
      or (use_clear and args.clear_folders)
      or args.include_locations
      or (use_clear and args.clear_locations)
  )
  if not selectors_set:
    return req, False

  # TODO(b/315289440): add validations for selectors.
  included_projects = None
  included_folders = None
  included_locations = None

  # If clear_projects is set, we have to clear included projects from selectors.
  if use_clear and args.clear_projects:
    included_projects = []

  # If clear_folders is set, we have to clear included folders from selectors.
  if use_clear and args.clear_folders:
    included_folders = []

  # If clear_locations is set, we have to clear included locations from
  # selectors.
  if use_clear and args.clear_locations:
    included_locations = []

  if args.include_projects:
    included_projects = []
    for project_id in args.include_projects.split(','):
      included_projects.append('projects/' + project_id)

  if args.include_folders:
    included_folders = []
    for folder_id in args.include_folders.split(','):
      included_folders.append('folders/' + folder_id)

  if args.include_locations:
    included_locations = []
    for location in args.include_locations.split(','):
      included_locations.append(location)

  if not orchestrator.orchestrationScope:
    orchestrator.orchestrationScope = (
        GetOrchestrationScopeMessage(messages, api_version)
    )

  # If selectors are not set in the orchestrator, we have to create them.
  hierarchy_selector = None
  location_selector = None
  if orchestrator.orchestrationScope.selectors:
    for selector in orchestrator.orchestrationScope.selectors:
      if selector.resourceHierarchySelector:
        hierarchy_selector = selector
      elif selector.locationSelector:
        location_selector = selector
  if not hierarchy_selector:
    hierarchy_selector = GetOrchestrationScopeSelectorMessage(
        messages, api_version)
  if not location_selector:
    location_selector = GetOrchestrationScopeSelectorMessage(
        messages, api_version)

  orchestrator.orchestrationScope.selectors = [
      hierarchy_selector,
      location_selector
  ]

  if not hierarchy_selector.resourceHierarchySelector:
    hierarchy_selector.resourceHierarchySelector = (
        GetResourceHierarchySelectorMessage(messages, api_version)
    )

  if not location_selector.locationSelector:
    location_selector.locationSelector = (
        GetLocationSelectorMessage(messages, api_version)
    )

  # Nit: we have to set included projects/folders/locations if they're [] to
  # clear the selectors.
  if included_projects is not None:
    hierarchy_selector.resourceHierarchySelector.includedProjects = (
        included_projects
    )
  if included_folders is not None:
    hierarchy_selector.resourceHierarchySelector.includedFolders = (
        included_folders
    )
  if included_locations is not None:
    location_selector.locationSelector.includedLocations = included_locations

  return req, True


def ModifyOrchestrorPolicyCreateRequest(ref, args, req):
  """Returns modified request with parsed orchestartor's policy assignment."""

  # Settings PolicyOrchestrator payload.
  api_version = GetApiVersionV2(args)
  messages = GetApiMessage(api_version)

  # For DELETE action we still have to specify empty payload.
  policy_assignment_config = messages.OSPolicyAssignment()
  if args.action == 'upsert':
    (policy_assignment_config, _) = GetResourceAndUpdateFieldsFromFile(
        args.policy_file, messages.OSPolicyAssignment
    )

  req_orchestrator = None
  if api_version == 'v2alpha':
    req_orchestrator = messages.GoogleCloudOsconfigV2alphaPolicyOrchestrator()
    req_orchestrator.orchestratedResource = (
        messages.GoogleCloudOsconfigV2alphaOrchestratedResource()
    )
    req.googleCloudOsconfigV2alphaPolicyOrchestrator = req_orchestrator
  elif api_version == 'v2beta':
    req_orchestrator = messages.GoogleCloudOsconfigV2betaPolicyOrchestrator()
    req_orchestrator.orchestratedResource = (
        messages.GoogleCloudOsconfigV2betaOrchestratedResource()
    )
    req.googleCloudOsconfigV2betaPolicyOrchestrator = req_orchestrator
  elif api_version == 'v2':
    req_orchestrator = messages.GoogleCloudOsconfigV2PolicyOrchestrator()
    req_orchestrator.orchestratedResource = (
        messages.GoogleCloudOsconfigV2OrchestratedResource()
    )
    req.googleCloudOsconfigV2PolicyOrchestrator = req_orchestrator

  req_orchestrator.orchestratedResource.osPolicyAssignmentV1Payload = (
      policy_assignment_config
  )

  if args.policy_id:
    req_orchestrator.orchestratedResource.id = args.policy_id

  req_orchestrator.action = args.action.upper()
  req_orchestrator.state = args.state.upper()
  req, _ = ModifyOrchestratorPolicySetSelectors(
      args, req, messages, api_version, req_orchestrator
  )

  # Setting request-level fields.
  req.policyOrchestratorId = ref.Name()
  # req.parent contains full resource path, we have to shorten it.
  req.parent = '/'.join(req.parent.split('/')[:-2])
  return req


def ModifyOrchestrorPolicyUpdateRequest(unused_ref, args, req):
  """Returns modified request with parsed orchestartor's policy assignment."""

  # Settings PolicyOrchestrator payload.
  api_version = GetApiVersionV2(args)
  messages = GetApiMessage(api_version)
  # PolicyOrchestrator is already set in the request as the result of
  # read_modify_update flag (i.e. it forces 'get' on the current version of the
  # resource before the update). We have to retrive the proper version first.
  req_orchestrator = None

  if api_version == 'v2alpha':
    req_orchestrator = req.googleCloudOsconfigV2alphaPolicyOrchestrator
  elif api_version == 'v2beta':
    req_orchestrator = req.googleCloudOsconfigV2betaPolicyOrchestrator
  elif api_version == 'v2':
    req_orchestrator = req.googleCloudOsconfigV2PolicyOrchestrator

  update_mask = []

  if args.action:
    req_orchestrator.action = args.action.upper()
    update_mask.append('action')

  if args.policy_file:
    (policy_assignment_config, _) = GetResourceAndUpdateFieldsFromFile(
        args.policy_file, messages.OSPolicyAssignment
    )
    req_orchestrator.orchestratedResource.osPolicyAssignmentV1Payload = (
        policy_assignment_config
    )
    update_mask.append(
        'orchestrated_resource.os_policy_assignment_v1_payload'
    )

  if args.policy_id:
    req_orchestrator.orchestratedResource.id = args.policy_id
    update_mask.append('orchestrated_resource.id')

  if args.state:
    req_orchestrator.state = args.state.upper()
    update_mask.append('state')

  req, modified = ModifyOrchestratorPolicySetSelectors(
      args, req, messages, api_version, req_orchestrator, use_clear=True
  )
  if modified:
    update_mask.append('orchestration_scope.selectors')

  req.updateMask = ','.join(update_mask)

  return req


def ModifyOrchestrorPolicyListRequest(unused_ref, unused_args, req):
  """Extends request with global location part."""

  req.parent += '/locations/global'
  return req


def LogOutOperationCommandForAsyncResponse(response, args):
  """Reminds user of the command to check operation status.

  Args:
    response: Response from CreateOsPolicyAssignment
    args: gcloud args

  Returns:
    The original response
  """
  if args.async_:
    log.out.Print(
        GetOperationDescribeCommandFormat(args).format(response.name))
  return response


# TODO(b/261183749): Remove modify_request_hook when singleton resource args
# are enabled in declarative.
def UpdateProjectFeatureSettingsResource(unused_ref, unused_args, req):
  req.name = req.name + '/projectFeatureSettings'
  return req
