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
"""Utility for forming Artifact Registry requests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

# TODO(b/142489773) Required because of thread-safety issue with loading python
# modules in the presence of threads.
import collections
import encodings.idna  # pylint: disable=unused-import
import json
import mimetypes
import os
import re
import time

from apitools.base.py import exceptions as apitools_exceptions
from containerregistry.client import docker_name
from containerregistry.client.v2_2 import docker_http
from containerregistry.client.v2_2 import docker_image
from googlecloudsdk.api_lib import artifacts
from googlecloudsdk.api_lib.artifacts import exceptions as ar_exceptions
from googlecloudsdk.api_lib.container.images import util
from googlecloudsdk.api_lib.util import common_args
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.artifacts import remote_repo_util
from googlecloudsdk.command_lib.artifacts import requests as ar_requests
from googlecloudsdk.command_lib.projects import util as project_util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.resource import resource_printer
from googlecloudsdk.core.util import parallel

_INVALID_REPO_NAME_ERROR = (
    "Names may only contain lowercase letters, numbers, and hyphens, and must "
    "begin with a letter and end with a letter or number.")

_INVALID_REPO_LOCATION_ERROR = ("GCR repository {} can only be created in the "
                                "{} multi-region.")

_INVALID_GCR_REPO_FORMAT_ERROR = "GCR repository {} must be of DOCKER format."

_ALLOWED_GCR_REPO_LOCATION = {
    "gcr.io": "us",
    "us.gcr.io": "us",
    "eu.gcr.io": "europe",
    "asia.gcr.io": "asia",
}

_REPO_REGEX = "^[a-z]([a-z0-9-]*[a-z0-9])?$"

_AR_SERVICE_ACCOUNT = "service-{project_num}@gcp-sa-artifactregistry.iam.gserviceaccount.com"

_GCR_BUCKETS = {
    "us": {
        "bucket": "us.artifacts.{}.appspot.com",
        "repository": "us.gcr.io",
        "location": "us"
    },
    "europe": {
        "bucket": "eu.artifacts.{}.appspot.com",
        "repository": "eu.gcr.io",
        "location": "europe"
    },
    "asia": {
        "bucket": "asia.artifacts.{}.appspot.com",
        "repository": "asia.gcr.io",
        "location": "asia"
    },
    "global": {
        "bucket": "artifacts.{}.appspot.com",
        "repository": "gcr.io",
        "location": "us"
    }
}

_REPO_CREATION_HELP_TEXT = """\
Format of the repository. REPOSITORY_FORMAT must be one of:\n
 apt
    APT package format.
 docker
    Docker image format.
 go
    Go module format.
 kfp
    KFP package format.
 maven
    Maven package format.
 npm
    NPM package format.
 python
    Python package format.
 yum
    YUM package format.
"""

_REPO_CREATION_HELP_TEXT_BETA = """\
Format of the repository. REPOSITORY_FORMAT must be one of:\n
 apt
    APT package format.
 docker
    Docker image format.
 googet
    GooGet package format.
 kfp
    KFP package format.
 maven
    Maven package format.
 npm
    NPM package format.
 python
    Python package format.
 yum
    YUM package format.
"""

_REPO_CREATION_HELP_UPSTREAM_POLICIES = """\
(Virtual Repositories only) is the upstreams for the Virtual Repository.
Example of the file contents:
[
  {
    "id": "test1",
    "repository": "projects/p1/locations/us-central1/repository/repo1",
    "priority": 1
  },
  {
    "id": "test2",
    "repository": "projects/p2/locations/us-west2/repository/repo2",
    "priority": 2
  }
]
"""

_INVALID_UPSTREAM_POLICY = ("Upstream Policies should contain id, repository "
                            "and priority.")


def _GetMessagesForResource(resource_ref):
  return artifacts.Messages(resource_ref.GetCollectionInfo().api_version)


def _GetClientForResource(resource_ref):
  return artifacts.Client(resource_ref.GetCollectionInfo().api_version)


def _IsValidRepoName(repo_name):
  return re.match(_REPO_REGEX, repo_name) is not None


def GetProject(args):
  """Gets project resource from either argument flag or attribute."""
  return args.project or properties.VALUES.core.project.GetOrFail()


def GetRepo(args):
  """Gets repository resource from either argument flag or attribute."""
  return args.repository or properties.VALUES.artifacts.repository.GetOrFail()


def GetLocation(args):
  """Gets location resource from either argument flag or attribute."""
  return args.location or properties.VALUES.artifacts.location.GetOrFail()


def GetLocationList(args):
  return ar_requests.ListLocations(GetProject(args), args.page_size)


def ValidateGcrRepo(repo_name, repo_format, location, docker_format):
  """Validates input for a gcr.io repository."""
  expected_location = _ALLOWED_GCR_REPO_LOCATION.get(repo_name, "")
  if location != expected_location:
    raise ar_exceptions.InvalidInputValueError(
        _INVALID_REPO_LOCATION_ERROR.format(repo_name, expected_location))
  if repo_format != docker_format:
    raise ar_exceptions.InvalidInputValueError(
        _INVALID_GCR_REPO_FORMAT_ERROR.format(repo_name))


def AppendRepoDataToRequest(repo_ref, repo_args, request):
  """Adds repository data to CreateRepositoryRequest."""
  repo_name = repo_ref.repositoriesId
  location = GetLocation(repo_args)
  messages = _GetMessagesForResource(repo_ref)
  docker_format = messages.Repository.FormatValueValuesEnum.DOCKER
  repo_format = messages.Repository.FormatValueValuesEnum(
      repo_args.repository_format.upper())
  if repo_name in _ALLOWED_GCR_REPO_LOCATION:
    ValidateGcrRepo(repo_name, repo_format, location, docker_format)
  elif not _IsValidRepoName(repo_ref.repositoriesId):
    raise ar_exceptions.InvalidInputValueError(_INVALID_REPO_NAME_ERROR)
  if remote_repo_util.IsRemoteRepoRequest(repo_args):
    request = remote_repo_util.AppendRemoteRepoConfigToRequest(
        messages, repo_args, request
    )

  request.repository.name = repo_ref.RelativeName()
  request.repositoryId = repo_ref.repositoriesId
  request.repository.format = repo_format
  return request


def AppendUpstreamPoliciesToRequest(repo_ref, repo_args, request):
  """Adds upstream policies to CreateRepositoryRequest."""
  messages = _GetMessagesForResource(repo_ref)
  if repo_args.upstream_policy_file:
    if isinstance(
        request,
        messages.ArtifactregistryProjectsLocationsRepositoriesPatchRequest,
    ):
      # Clear the updateMask for update request, so AR will replace all old
      # policies with policies from the file.
      request.updateMask = None
    content = console_io.ReadFromFileOrStdin(
        repo_args.upstream_policy_file, binary=False
    )
    policies = json.loads(content)
    request.repository.virtualRepositoryConfig = (
        messages.VirtualRepositoryConfig()
    )
    request.repository.virtualRepositoryConfig.upstreamPolicies = []
    for policy in policies:
      if all(key in policy for key in ("id", "priority", "repository")):
        p = messages.UpstreamPolicy(
            id=policy["id"],
            priority=policy["priority"],
            repository=policy["repository"],
        )
        request.repository.virtualRepositoryConfig.upstreamPolicies.append(p)
      else:
        raise ar_exceptions.InvalidInputValueError(_INVALID_UPSTREAM_POLICY)

  return request


def AddAdditionalArgs():
  """Adds additional flags."""
  return UpstreamsArgs() + RepoFormatArgs() + remote_repo_util.Args()


def UpstreamsArgs():
  """Adds the upstream-policy-file flag."""
  # Is required because the upload operation requires the type conversion that
  # should be done by a function. The "File" metavar is also usually handled by
  # custom functions.
  return [
      base.Argument(
          "--upstream-policy-file",
          metavar="FILE",
          help=_REPO_CREATION_HELP_UPSTREAM_POLICIES)
  ]


def RepoFormatArgs():
  """Adds the repository-format flag."""
  # We need to do this because the declarative framework doesn't support
  # hiding an enum from the help text.
  return [
      base.Argument(
          "--repository-format", required=True, help=_REPO_CREATION_HELP_TEXT)
  ]


def AddRepositoryFormatArgBeta():
  """Adds the repository-format flag."""
  # We need to do this because the declarative framework doesn't support
  # hiding an enum from the help text.
  return [
      base.Argument(
          "--repository-format",
          required=True,
          help=_REPO_CREATION_HELP_TEXT_BETA)
  ]


def CheckServiceAccountPermission(unused_repo_ref, repo_args, request):
  """Checks and grants key encrypt/decrypt permission for service account.

  Checks if Artifact Registry service account has encrypter/decrypter or owner
  role for the given key. If not, prompts users to grant key encrypter/decrypter
  permission to the service account. Operation would fail if users do not grant
  the permission.

  Args:
    unused_repo_ref: Repo reference input.
    repo_args: User input arguments.
    request: Create repository request.

  Returns:
    Create repository request.
  """
  if not repo_args.kms_key:
    return request
  # Best effort to check if AR's service account has permission to use the key;
  # ignore if the caller identity does not have enough permission to check.
  try:
    project_num = project_util.GetProjectNumber(GetProject(repo_args))
    policy = ar_requests.GetCryptoKeyPolicy(repo_args.kms_key)
    service_account = _AR_SERVICE_ACCOUNT.format(project_num=project_num)
    for binding in policy.bindings:
      if "serviceAccount:" + service_account in binding.members and (
          binding.role == "roles/cloudkms.cryptoKeyEncrypterDecrypter" or
          binding.role == "roles/owner"):
        return request
    grant_permission = console_io.PromptContinue(
        prompt_string=(
            "\nGrant the Artifact Registry Service Account "
            "permission to encrypt/decrypt with the selected key [{key_name}]"
            .format(key_name=repo_args.kms_key)))
    if not grant_permission:
      return request
    try:
      ar_requests.AddCryptoKeyPermission(repo_args.kms_key,
                                         "serviceAccount:" + service_account)
      # We have checked the existence of the key when checking IAM bindings
      # So all 400s should be because the service account is problematic.
      # We are moving the permission check to the backend fairly soon anyway.
    except apitools_exceptions.HttpBadRequestError:
      msg = (
          "The Artifact Registry service account might not exist, manually "
          "create the service account.\nLearn more: "
          "https://cloud.google.com/artifact-registry/docs/cmek")
      raise ar_exceptions.ArtifactRegistryError(msg)

    log.status.Print(
        "Added Cloud KMS CryptoKey Encrypter/Decrypter Role to [{key_name}]"
        .format(key_name=repo_args.kms_key))
  except apitools_exceptions.HttpForbiddenError:
    return request
  return request


def DeleteVersionTags(ver_ref, ver_args, request):
  """Deletes tags associate with the specified version."""
  if not ver_args.delete_tags:
    return request
  client = _GetClientForResource(ver_ref)
  messages = _GetMessagesForResource(ver_ref)
  escaped_pkg = ver_ref.packagesId.replace("/", "%2F").replace("+", "%2B")
  escaped_pkg = escaped_pkg.replace("^", "%5E")
  package = resources.REGISTRY.Create(
      "artifactregistry.projects.locations.repositories.packages",
      projectsId=ver_ref.projectsId,
      locationsId=ver_ref.locationsId,
      repositoriesId=ver_ref.repositoriesId,
      packagesId=escaped_pkg)
  tag_list = ar_requests.ListTags(client, messages,
                                  package.RelativeName())
  for tag in tag_list:
    if tag.version != request.name:
      continue
    ar_requests.DeleteTag(client, messages, tag.name)
  return request


def AppendTagDataToRequest(tag_ref, tag_args, request):
  """Adds tag data to CreateTagRequest."""
  parts = request.parent.split("/")
  pkg_path = "/".join(parts[:len(parts) - 2])
  request.parent = pkg_path
  messages = _GetMessagesForResource(tag_ref)
  tag = messages.Tag(
      name=tag_ref.RelativeName(),
      version=pkg_path + "/versions/" + tag_args.version)
  request.tag = tag
  request.tagId = tag_ref.tagsId
  return request


def SetTagUpdateMask(tag_ref, tag_args, request):
  """Sets update mask to UpdateTagRequest."""
  messages = _GetMessagesForResource(tag_ref)
  parts = request.name.split("/")
  pkg_path = "/".join(parts[:len(parts) - 2])
  tag = messages.Tag(
      name=tag_ref.RelativeName(),
      version=pkg_path + "/versions/" + tag_args.version)
  request.tag = tag
  request.updateMask = "version"
  return request


def EscapePackageName(pkg_ref, unused_args, request):
  """Escapes slashes and pluses in package name for ListVersionsRequest."""
  escaped_pkg = pkg_ref.packagesId.replace("/", "%2F").replace("+", "%2B")
  escaped_pkg = escaped_pkg.replace("^", "%5E")
  request.parent = "{}/packages/{}".format(
      pkg_ref.Parent().RelativeName(),
      escaped_pkg)
  return request


def AppendSortingToRequest(unused_ref, ver_args, request):
  """Adds order_by and page_size parameters to the request."""
  order_by = common_args.ParseSortByArg(ver_args.sort_by)
  set_limit = True

  # Multi-ordering is not supported yet on backend.
  if order_by is not None:
    if "," not in order_by:
      request.orderBy = order_by
    else:
      set_limit = False

  if (ver_args.limit is not None and ver_args.filter is None and set_limit):
    request.pageSize = ver_args.limit
    # Otherwise request gets overridden somewhere down the line.
    ver_args.page_size = ver_args.limit

  return request


def UnescapePackageName(response, unused_args):
  """Unescapes slashes and pluses in package name from ListPackagesResponse."""
  ret = []
  for ver in response:
    ver.name = os.path.basename(ver.name)
    ver.name = ver.name.replace("%2F", "/").replace("%2B", "+")
    ver.name = ver.name.replace("%5E", "^")
    ret.append(ver)
  return ret


def AppendParentInfoToListReposResponse(response, args):
  """Adds log to clarify parent resources for ListRepositoriesRequest."""
  log.status.Print("Listing items under project {}, location {}.\n".format(
      GetProject(args), GetLocation(args)))
  return response


def AppendParentInfoToListPackagesResponse(response, args):
  """Adds log to clarify parent resources for ListPackagesRequest."""
  log.status.Print(
      "Listing items under project {}, location {}, repository {}.\n".format(
          GetProject(args), GetLocation(args), GetRepo(args)))
  return response


def AppendParentInfoToListVersionsAndTagsResponse(response, args):
  """Adds log to clarify parent resources for ListVersions or ListTags."""
  log.status.Print(
      "Listing items under project {}, location {}, repository {}, "
      "package {}.\n".format(
          GetProject(args), GetLocation(args), GetRepo(args), args.package))
  return response


def GetGCRRepos(buckets, project):
  """Gets a list of GCR repositories given a list of GCR bucket names."""
  existing_buckets = GetExistingGCRBuckets(buckets, project)

  def RepoMsg(bucket):
    return bucket["repository"]

  return map(RepoMsg, existing_buckets)


def GetExistingGCRBuckets(buckets, project):
  """Gets the list of GCR bucket names that exist in the project."""
  existing_buckets = []

  project_id_for_bucket = project
  if ":" in project:
    domain, project_id = project.split(":")
    project_id_for_bucket = "{}.{}.a".format(project_id, domain)
  for bucket in buckets.values():
    try:
      ar_requests.TestStorageIAMPermission(
          bucket["bucket"].format(project_id_for_bucket), project)
      existing_buckets.append(bucket)
    except apitools_exceptions.HttpNotFoundError:
      continue
  return existing_buckets


def ListRepositories(args):
  """Lists repositories in a given project.

  If no location value is specified, list repositories across all locations.

  Args:
    args: User input arguments.

  Returns:
    List of repositories.
  """
  project = GetProject(args)
  location = args.location or properties.VALUES.artifacts.location.Get()

  loc_paths = []
  if location and location != "all":
    log.status.Print("Listing items under project {}, location {}.\n".format(
        project, location))
    loc_paths.append("projects/{}/locations/{}".format(project, location))
  else:
    location_list = ar_requests.ListLocations(project)
    log.status.Print(
        "Listing items under project {}, across all locations.\n".format(
            project))
    loc_paths.extend([
        "projects/{}/locations/{}".format(project, loc) for loc in location_list
    ])

  pool_size = len(loc_paths) if loc_paths else 1
  pool = parallel.GetPool(pool_size)
  page_size = args.page_size
  try:
    pool.Start()
    results = pool.Map(
        lambda x: ar_requests.ListRepositories(x, page_size=page_size),
        loc_paths)
  except parallel.MultiError as e:
    error_set = set(err.content for err in e.errors)
    msg = "\n".join(error_set)
    raise ar_exceptions.ArtifactRegistryError(msg)
  finally:
    pool.Join()

  repos = []
  for sublist in results:
    repos.extend(sublist)
  repos.sort(key=lambda x: x.name.split("/")[-1])

  return repos


def ListFiles(args):
  """Lists files in a given project.

  Args:
    args: User input arguments.

  Returns:
    List of files.
  """
  client = ar_requests.GetClient()
  messages = ar_requests.GetMessages()
  project = GetProject(args)
  location = args.location or properties.VALUES.artifacts.location.Get()
  repo = GetRepo(args)
  package = args.package
  version = args.version
  tag = args.tag
  page_size = args.page_size
  arg_filters = ""

  if args.filter:
    arg_filters = args.filter
    if package or version or tag:
      raise ar_exceptions.InvalidInputValueError(
          "Cannot specify --filter with --package, --version or --tag.")

  # Parse fully qualified path in package argument
  if package:
    if re.match(r"projects\/.*\/locations\/.*\/repositories\/.*\/packages\/.*",
                package):
      params = package.replace("projects/", "", 1).replace(
          "/locations/", " ", 1).replace("/repositories/", " ",
                                         1).replace("/packages/", " ",
                                                    1).split(" ")
      project, location, repo, package = [params[i] for i in range(len(params))]

  # Escape slashes, pluses and carets in package name
  if package:
    package = package.replace("/", "%2F").replace("+", "%2B")
    package = package.replace("^", "%5E")

  # Retrieve version from tag name
  if version and tag:
    raise ar_exceptions.InvalidInputValueError(
        "Specify either --version or --tag with --package argument.")
  if package and tag:
    tag_path = resources.Resource.RelativeName(
        resources.REGISTRY.Create(
            "artifactregistry.projects.locations.repositories.packages.tags",
            projectsId=project,
            locationsId=location,
            repositoriesId=repo,
            packagesId=package,
            tagsId=tag))
    version = ar_requests.GetVersionFromTag(client, messages, tag_path)

  if package and version:
    version_path = resources.Resource.RelativeName(
        resources.REGISTRY.Create(
            "artifactregistry.projects.locations.repositories.packages.versions",
            projectsId=project,
            locationsId=location,
            repositoriesId=repo,
            packagesId=package,
            versionsId=version))
    arg_filters = 'owner="{}"'.format(version_path)
  elif package:
    package_path = resources.Resource.RelativeName(
        resources.REGISTRY.Create(
            "artifactregistry.projects.locations.repositories.packages",
            projectsId=project,
            locationsId=location,
            repositoriesId=repo,
            packagesId=package))
    arg_filters = 'owner="{}"'.format(package_path)
  elif version or tag:
    raise ar_exceptions.InvalidInputValueError(
        "Package name is required when specifying version or tag.")

  repo_path = resources.Resource.RelativeName(
      resources.REGISTRY.Create(
          "artifactregistry.projects.locations.repositories",
          projectsId=project,
          locationsId=location,
          repositoriesId=repo))
  files = ar_requests.ListFiles(client, messages, repo_path, arg_filters,
                                page_size)

  return files


def AddEncryptionLogToRepositoryInfo(response, unused_args):
  """Adds encryption info log to repository info."""
  if response.kmsKeyName:
    log.status.Print("Encryption: Customer-managed key")
  else:
    log.status.Print("Encryption: Google-managed key")
  return response


def AddRegistryBaseToRepositoryInfo(response, unused_args):
  """Adds the base URL of the repo for registry operations to repository info."""
  repo_name = resources.REGISTRY.ParseRelativeName(
      response.name,
      collection="artifactregistry.projects.locations.repositories",
  )
  log.status.Print(
      "Registry URL: {}-{}.pkg.dev/{}/{}".format(
          repo_name.locationsId,
          str(response.format).lower(),
          repo_name.projectsId.replace(":", "/"),
          repo_name.repositoriesId,
      )
  )
  return response


def ConvertBytesToMB(response, unused_args):
  if response.sizeBytes is not None:
    log.status.Print("Repository Size: {0:.3f}MB".format(response.sizeBytes /
                                                         1e6))
  else:
    log.status.Print("Repository Size: {0:.3f}MB".format(0))
  response.sizeBytes = None
  return response


def EscapePackageNameHook(ref, unused_args, req):
  """Escapes slashes and pluses from request names."""
  escaped_pkg = ref.packagesId.replace("/", "%2F").replace("+", "%2B")
  escaped_pkg = escaped_pkg.replace("^", "%5E")
  package = resources.REGISTRY.Create(
      "artifactregistry.projects.locations.repositories.packages",
      projectsId=ref.projectsId,
      locationsId=ref.locationsId,
      repositoriesId=ref.repositoriesId,
      packagesId=escaped_pkg)
  req.name = package.RelativeName()
  return req


def EscapeTagNameHook(ref, unused_args, req):
  """Escapes slashes and pluses from request names."""
  escaped_pkg = ref.packagesId.replace("/", "%2F").replace("+", "%2B")
  escaped_pkg = escaped_pkg.replace("^", "%5E")
  tag = resources.REGISTRY.Create(
      "artifactregistry.projects.locations.repositories.packages.tags",
      projectsId=ref.projectsId,
      locationsId=ref.locationsId,
      repositoriesId=ref.repositoriesId,
      packagesId=escaped_pkg,
      tagsId=ref.tagsId.replace("/", "%2F").replace("+", "%2B"))
  req.name = tag.RelativeName()
  return req


def EscapeVersionNameHook(ref, unused_args, req):
  """Escapes slashes and pluses from request names."""
  escaped_pkg = ref.packagesId.replace("/", "%2F").replace("+", "%2B")
  escaped_pkg = escaped_pkg.replace("^", "%5E")
  escaped_ver = ref.versionsId.replace("/", "%2F").replace("+", "%2B")
  escaped_ver = escaped_ver.replace("^", "%5E")
  version = resources.REGISTRY.Create(
      "artifactregistry.projects.locations.repositories.packages.versions",
      projectsId=ref.projectsId,
      locationsId=ref.locationsId,
      repositoriesId=ref.repositoriesId,
      packagesId=escaped_pkg,
      versionsId=escaped_ver,
  )
  req.name = version.RelativeName()
  return req


def EscapeFileNameHook(ref, unused_args, req):
  """Escapes slashes from request names."""
  file = resources.REGISTRY.Create(
      "artifactregistry.projects.locations.repositories.files",
      projectsId=ref.projectsId,
      locationsId=ref.locationsId,
      repositoriesId=ref.repositoriesId,
      filesId=ref.filesId.replace("/", "%2F"),
  )
  req.name = file.RelativeName()
  return req

# TODO: b/302727117 - Get from property once CL/602815074 is approved
# gcr_base = getattr(properties.VALUES.artifacts, "gcr_host").Get()
gcr_base = "gcr.io"
host_seperator = "-" if "-" in gcr_base else "."

gcr_repos = [
    {"repository": "gcr.io", "location": "us", "host": f"{gcr_base}"},
    {
        "repository": "us.gcr.io",
        "location": "us",
        "host": f"us{host_seperator}{gcr_base}",
    },
    {
        "repository": "asia.gcr.io",
        "location": "asia",
        "host": f"asia{host_seperator}{gcr_base}",
    },
    {
        "repository": "eu.gcr.io",
        "location": "europe",
        "host": f"eu{host_seperator}{gcr_base}",
    },
]


def GetMultiProjectRedirectionEnablementReport(projects):
  """Prints a redirection enablement report and returns mis-configured repos.

  This checks all the GCR repositories in the supplied project and checks if
  they each have a repository in Artifact Registry create to be the redirection
  target. It prints a report as it validates.

  Args:
    projects: The projects to validate

  Returns:
    A list of the GCR repos that do not have a redirection repo configured in
    Artifact Registry.
  """

  missing_repos = {}
  if not projects:
    return missing_repos
  repo_report = []
  con = console_attr.GetConsoleAttr()

  # For each gcr repo in a location that our environment supports,
  # is there an associated repo in AR?
  for project in projects:
    report_line = [project, 0]
    p_repos = []
    for gcr_repo in gcr_repos:
      ar_repo_name = "projects/{}/locations/{}/repositories/{}".format(
          project, gcr_repo["location"], gcr_repo["repository"]
      )
      try:
        ar_requests.GetRepository(ar_repo_name)
      except apitools_exceptions.HttpNotFoundError:
        report_line[1] += 1
        p_repos.append(gcr_repo)
    repo_report.append(report_line)
    log.status.Print(report_line)
    if p_repos:
      missing_repos[project] = p_repos

  log.status.Print("Project Repository Report:\n")
  printer = resource_printer.Printer("table", out=log.status)
  printer.AddHeading([
      con.Emphasize("Project", bold=True),
      con.Emphasize("Missing Artifact Registry Repos to Create", bold=True),
  ])
  for line in repo_report:
    printer.AddRecord(line)
  printer.Finish()
  log.status.Print()
  return missing_repos


def GetRedirectionEnablementReport(project):
  """Prints a redirection enablement report and returns mis-configured repos.

  This checks all the GCR repositories in the supplied project and checks if
  they each have a repository in Artifact Registry create to be the redirection
  target. It prints a report as it validates.

  Args:
    project: The project to validate

  Returns:
    A list of the GCR repos that do not have a redirection repo configured in
    Artifact Registry.
  """

  missing_repos = []
  repo_report = []
  # report_line = []
  con = console_attr.GetConsoleAttr()
  location = getattr(properties.VALUES.artifacts, "location").Get()

  # For each gcr repo in a location that our environment supports,
  # is there an associated repo in AR?
  for gcr_repo in gcr_repos:
    # For gcr.io, redirection affects every location
    if gcr_base != "gcr.io" and location and location != gcr_repo["location"]:
      continue
    report_line = [gcr_repo["host"], gcr_repo["location"]]
    ar_repo_name = "projects/{}/locations/{}/repositories/{}".format(
        project, gcr_repo["location"], gcr_repo["repository"])
    try:
      ar_repo = ar_requests.GetRepository(ar_repo_name)
      report_line.append(con.Colorize(ar_repo.name, "green"))
    except apitools_exceptions.HttpNotFoundError:
      report_line.append(
          con.Colorize(
              'None Found. Can create repo named "{}"'.format(
                  gcr_repo["repository"]
              ),
              "yellow",
          )
      )
      missing_repos.append(gcr_repo)
    repo_report.append(report_line)

  log.status.Print(f"Repository report for {project}:\n")
  printer = resource_printer.Printer("table", out=log.status)
  printer.AddHeading([
      con.Emphasize("Container Registry Host", bold=True),
      con.Emphasize("Location", bold=True),
      con.Emphasize("Artifact Registry Repository", bold=True)
  ])
  for line in repo_report:
    printer.AddRecord(line)
  printer.Finish()
  log.status.Print()
  return missing_repos


def GetExistingRepos(project):
  """Gets the already created repos for the given project."""
  found_repos = []
  location = getattr(properties.VALUES.artifacts, "location").Get()
  for gcr_repo in gcr_repos:
    if gcr_base != "gcr.io" and location and location != gcr_repo["location"]:
      continue
    ar_repo_name = "projects/{}/locations/{}/repositories/{}".format(
        project, gcr_repo["location"], gcr_repo["repository"]
    )
    try:
      ar_requests.GetRepository(ar_repo_name)
      found_repos.append(gcr_repo)
    except apitools_exceptions.HttpNotFoundError:
      continue
  return found_repos


# TODO(b/261183749): Remove modify_request_hook when singleton resource args
# are enabled in declarative.
def UpdateSettingsResource(unused_ref, unused_args, req):
  req.name = req.name + "/projectSettings"
  return req


def CheckRedirectionPermission(projects):
  """Checks redirection permission for the projects."""
  for project in projects:
    con = console_attr.GetConsoleAttr()
    authorized = ar_requests.TestRedirectionIAMPermission(project)
    if not authorized:
      if len(projects) == 1:
        log.status.Print(
            con.Colorize("FAIL: ", "red")
            + "This operation requires the"
            f" {','.join(ar_requests.REDIRECT_PERMISSIONS)} permission(s) on"
            f" project {project}."
        )
      else:
        log.status.Print(
            con.Colorize("FAIL: ", "red")
            + "This operation requires the"
            f" {','.join(ar_requests.REDIRECT_PERMISSIONS)} permission(s) on"
            f" each project to migrate, including {project}."
        )
      log.status.Print(
          "You can set this permission with the following command:"
          f"\n  gcloud projects add-iam-policy-binding {project} "
          "--member=<account> --role='roles/storage.admin'"
      )
      return False
  return True


def GetVPCSCConfig(unused_ref, args):
  project = GetProject(args)
  location = GetLocation(args)
  return ar_requests.GetVPCSCConfig(project, location)


def AllowVPCSCConfig(unused_ref, args):
  project = GetProject(args)
  location = GetLocation(args)
  return ar_requests.AllowVPCSCConfig(project, location)


def DenyVPCSCConfig(unused_ref, args):
  project = GetProject(args)
  location = GetLocation(args)
  return ar_requests.DenyVPCSCConfig(project, location)


def GetRedirectionStates(projects):
  """Gets the redirection states for the given projects."""
  if not CheckRedirectionPermission(projects):
    return None, False

  env = "prod"
  endpoint_property = getattr(
      properties.VALUES.api_endpoint_overrides, "artifactregistry"
  )
  old_endpoint = endpoint_property.Get()
  if old_endpoint and "staging" in old_endpoint:
    env = "staging"
    # Staging uses prod redirect endpoint
    # gcloud-disable-gdu-domain
    endpoint_property.Set("https://artifactregistry.googleapis.com/")
  redirection_states = {}
  try:
    for project in projects:
      redirection_states[project] = ar_requests.GetProjectSettings(
          project
      ).legacyRedirectionState
  finally:
    if env == "staging":
      endpoint_property.Set(old_endpoint)
  return redirection_states, True


def SetRedirectionStatus(project, status):
  """Sets the redirection status for the given project."""
  endpoint_property = getattr(
      properties.VALUES.api_endpoint_overrides, "artifactregistry"
  )
  old_endpoint = endpoint_property.Get()
  env = "prod"
  try:
    if old_endpoint and "staging" in old_endpoint:
      env = "staging"
      # Staging uses prod redirect endpoint
      # gcloud-disable-gdu-domain
      endpoint_property.Set("https://artifactregistry.googleapis.com/")
    ar_requests.SetUpgradeRedirectionState(project, status)
  except apitools_exceptions.HttpForbiddenError as e:
    con = console_attr.GetConsoleAttr()
    match = re.search("requires (.*) to have storage.objects.", str(e))
    if not match:
      raise
    log.status.Print(
        con.Colorize("\nERROR:", "red")
        + " The Artifact Registry service account doesn't have access to"
        " {project} for copying images\nThe following command will grant the"
        " necessary access (may take a few minutes):\n  gcloud projects"
        " add-iam-policy-binding {project} --member='serviceAccount:{p4sa}'"
        " --role='roles/storage.objectViewer'\n".format(
            p4sa=match[1], project=project
        ),
    )
    return False
  finally:
    if env == "staging":
      endpoint_property.Set(old_endpoint)
  return True


def MigrateToArtifactRegistry(unused_ref, args):
  """Runs the automigrate wizard for the current project."""
  if args.projects:
    projects = args.projects.split(",")
  else:
    projects = [args.project or properties.VALUES.core.project.GetOrFail()]
  recent_images_only = args.recent_images_only
  from_gcr = args.from_gcr
  to_pkg_dev = args.to_pkg_dev
  copy_only = args.copy_only
  if recent_images_only is not None and (
      recent_images_only < 30 or recent_images_only > 90
  ):
    log.status.Print("--recent-images-only must be between 30 and 90 inclusive")
    return None
  if args.projects and (from_gcr or to_pkg_dev):
    log.status.Print(
        "Projects argument may not be used when providing --from-gcr and"
        " --to-pkg-dev"
    )
    return None

  if bool(from_gcr) != bool(to_pkg_dev):
    log.status.Print(
        "--from-gcr and --to-pkg-dev-repo should be provided together"
    )
    return None

  if to_pkg_dev:
    gcr_host = from_gcr.split("/")[0]
    if gcr_host not in _ALLOWED_GCR_REPO_LOCATION.keys():
      log.status.Print(
          "{gcr_host} is not a valid gcr host. Valid hosts: {hosts}".format(
              gcr_host=gcr_host,
              hosts=", ".join(_ALLOWED_GCR_REPO_LOCATION.keys()),
          )
      )
      return None
    location = _ALLOWED_GCR_REPO_LOCATION[gcr_host]
    host = "{}{}-docker.pkg.dev".format(
        properties.VALUES.artifacts.registry_endpoint_prefix.Get(), location
    )
    if not WrappedCopyImagesFromGCR(
        [host],
        to_pkg_dev,
        recent_images_only,
        copy_from=from_gcr,
    ):
      return None

    if not copy_only:
      log.status.Print(
          "\nAny reference to {gcr} will "
          "still need to be updated to reference {ar}".format(
              gcr=from_gcr, ar=host + "/" + to_pkg_dev
          )
      )
    return None

  messages = ar_requests.GetMessages()
  if copy_only:
    copying_projects = projects
    enabled_projects = []
    disabled_projects = []
    invalid_projects = []
  else:
    redirection_state, cont = GetRedirectionStates(projects)
    if not cont:
      return None
    enabled_projects = []
    disabled_projects = []
    copying_projects = []
    invalid_projects = []
    for project, state in redirection_state.items():
      if (
          state
          == messages.ProjectSettings.LegacyRedirectionStateValueValuesEnum.REDIRECTION_FROM_GCR_IO_ENABLED
      ):
        enabled_projects.append(project)
      elif (
          state
          == messages.ProjectSettings.LegacyRedirectionStateValueValuesEnum.REDIRECTION_FROM_GCR_IO_ENABLED_AND_COPYING
      ):
        copying_projects.append(project)
      elif (
          state
          == messages.ProjectSettings.LegacyRedirectionStateValueValuesEnum.REDIRECTION_FROM_GCR_IO_DISABLED
      ):
        disabled_projects.append(project)
      else:
        invalid_projects.append(project)

  if invalid_projects:
    log.status.Print(
        "Skipping migration for projects in unsppoted state: {}".format(
            invalid_projects
        )
    )
    if len(invalid_projects) == len(projects):
      return None

  # Exit early if all projects are migrated
  if len(enabled_projects) == len(projects):
    log.status.Print(
        "Artifact Registry is already handling all requests for *gcr.io repos"
        " for the provided projects"
    )
    return None

  if enabled_projects:
    log.status.Print(
        "Skipping already migrated projects: {}\n".format(enabled_projects)
    )

  # Only do the initial steps for projects where we haven't started redirection
  # yet. Otherwise, we pick up where we left off.
  if disabled_projects:
    if not MaybeCreateMissingRepos(
        disabled_projects, automigrate=True, dry_run=False
    ):
      return None
  # Re-check list of repos because we tried to create some
  # Also get list for copying projects while we're at it, because we'll
  # need them later
  existing_repos = {}
  for project in disabled_projects + copying_projects:
    existing_repos[project] = GetExistingRepos(project)

  projects_to_redirect = []
  dangerous_projects = []
  for project in disabled_projects:
    if not existing_repos[project]:
      log.status.Print(
          "Skipping project {} because it has no Artifact Registry repos to"
          " migrate to".format(project)
      )
    # If we're missing any repos, check if they're repos with GCR buckets
    missing_bucket_repos = []
    if len(existing_repos[project]) < 4:
      repos_with_gcr_buckets = GetGCRRepos(_GCR_BUCKETS, project)
      for g in repos_with_gcr_buckets:
        if g not in [r["repository"] for r in existing_repos[project]]:
          missing_bucket_repos.append(g)

    if missing_bucket_repos:
      dangerous_projects.append(project)
    else:
      projects_to_redirect.append(project)

  if projects_to_redirect:
    for project in dangerous_projects:
      log.status.Print(
          "Skipping project {} because it has a Container Registry"
          " bucket without a corresponding Artifact Registry"
          " repository.".format(project)
      )
  # If all listed projects are dangerous, this may be intentional. Allow it, but
  # warn first
  elif dangerous_projects:
    c = console_attr.GetConsoleAttr()
    cont = console_io.PromptContinue(
        "\n{project_str} has Container Registry buckets without"
        " corresponding Artifact Registry repositories. Existing Container"
        " Registry data will become innacessible.".format(
            project_str="This project"
            if len(dangerous_projects) == 1
            else "Each project"
        ),
        "Do you wish to continue " + c.Colorize("(not recommended)", "red"),
        default=False,
    )
    if not cont:
      return None
    projects_to_redirect = dangerous_projects
  # TODO: b/322822683 - update auth here
  if projects_to_redirect:
    caveat = ""
    if recent_images_only:
      caveat = (
          " that have been pulled or pushed in the last"
          f" {recent_images_only} days"
      )
    log.status.Print(
        "\nIf you continue, all *gcr.io traffic will be sent to Artifact"
        " Registry for the following projects. All Container Registry"
        f" images{caveat} will be copied. During migration, Artifact Registry"
        " will serve *gcr.io requests for images it doesn't have yet"
        " by copying them from Container Registry at request time."
        " Deleting images from *gcr.io repos in the middle of migration might"
        " not be effective.\n"
    )
    update = console_io.PromptContinue(
        "Projects to redirect: {}".format(projects_to_redirect),
        default=False,
    )
    if not update:
      return None

  for project in projects_to_redirect:
    if SetRedirectionStatus(
        project,
        messages.ProjectSettings.LegacyRedirectionStateValueValuesEnum.REDIRECTION_FROM_GCR_IO_ENABLED_AND_COPYING,
    ):
      copying_projects.append(project)
      log.status.Print(
          "*gcr.io traffic is now being served by Artifact Registry for"
          " {project}. Missing images are being copied from Container Registry"
          "\nTo send traffic back to Container Registry, run:"
          "\n  gcloud artifacts settings disable-upgrade-redirection"
          " --project={project}\n".format(project=project)
      )

  if not copying_projects:
    return None

  if copy_only:
    log.status.Print("\nCopying images...\n")
  else:
    log.status.Print("\nCopying remaining images...\n")
    # Redirection has 10-second eventual consistency. If we redirected any
    # projects, wait 10 seconds to avoid race conditions
    if projects_to_redirect:
      time.sleep(10)

  # TODO: b/322823451 - add a threadpool
  # Note that we're already copying automatically at this point. This step
  # just makes sure we've copied all the remaining images before we turn off
  # copying. This could take a while for large repos.
  failed_copies = []
  to_enable = []
  for project in copying_projects:
    gcr_hosts = [r["host"] for r in existing_repos[project]]
    if WrappedCopyImagesFromGCR(gcr_hosts, project, recent_images_only):
      to_enable.append(project)
    else:
      failed_copies.append(project)

  if copy_only:
    return None

  if failed_copies:
    if to_enable:
      log.status.Print("\nOnly completing migration for successful projects")
    else:
      cont = console_io.PromptContinue(
          "\nAll projects had image copy failures. Continuing will disable"
          " further copying and images will be missing.",
          "Continue anyway?",
          default=False,
      )
      if cont:
        to_enable = failed_copies
      if not cont:
        return None

  log.status.Print()
  for project in to_enable:
    if SetRedirectionStatus(
        project,
        messages.ProjectSettings.LegacyRedirectionStateValueValuesEnum.REDIRECTION_FROM_GCR_IO_ENABLED,
    ):
      log.status.Print(
          "*gcr.io traffic is now being fully served by Artifact Registry for"
          " {project}. Images will no longer be copied from Container Registry"
          " for this project.".format(project=project)
      )
      enabled_projects.append(project)
  log.status.Print(
      "\nThe following projects are fully migrated: {}".format(enabled_projects)
  )
  remaining_projects = list(set(projects) - set(enabled_projects))
  if remaining_projects:
    log.status.Print(
        "The following projects still need to finish being migrated: {}".format(
            remaining_projects
        )
    )
    log.status.Print(
        "\nThis script can be re-run to migrate any projects that haven't"
        "finished."
    )


def WrappedCopyImagesFromGCR(
    hosts, project_repo, recent_only, copy_from="same"
):
  """Copies images from GCR for all hosts and handles auth error."""
  try:
    results = collections.defaultdict(int)
    example_failures = []
    for host in hosts:
      host_results = CopyImagesFromGCR(
          host + "/" + project_repo, recent_only, copy_from=copy_from
      )
      results["manifestsCopied"] += host_results["manifestsCopied"]
      results["tagsCopied"] += host_results["tagsCopied"]
      results["manifestsFailed"] += host_results["manifestsFailed"]
      results["tagsFailed"] += host_results["tagsFailed"]
      example_failures += host_results["exampleFailures"]

    log.status.Print(
        "\n{project}: Successfully copied {tags} additional tags and"
        " {manifests} additional manifests. There were {failures} failures."
        .format(
            project=project_repo,
            tags=results["tagsCopied"],
            manifests=results["manifestsCopied"],
            failures=results["tagsFailed"] + results["manifestsFailed"],
        )
    )
    if results["tagsFailed"] + results["manifestsFailed"]:
      log.status.Print("\nExample images that failed to copy:")
      for example_failure in example_failures:
        log.status.Print(example_failure)
      return False
    return True
  except docker_http.V2DiagnosticException as e:
    match = re.search("requires (.*) to have storage.objects.", str(e))
    if not match:
      raise
    con = console_attr.GetConsoleAttr()
    project = project_repo
    if copy_from != "same":
      project = copy_from.split("/")[-1]
    log.status.Print(
        con.Colorize("\nERROR:", "red")
        + " The Artifact Registry service account doesn't have access to"
        " {project} for copying images\nThe following command will grant the"
        " necessary access (may take a few minutes):\n  gcloud projects"
        " add-iam-policy-binding {project} --member='serviceAccount:{p4sa}'"
        " --role='roles/storage.objectViewer'\n".format(
            p4sa=match[1], project=project
        ),
    )
    return False


def CopyImagesFromGCR(repo_path, recent_only, copy_from="same"):
  """Recursively copies images from GCR."""
  if copy_from == "same":
    log.status.Print(f"Copying images for {repo_path}...")
  else:
    log.status.Print(f"Copying images to {repo_path}...")
  http_obj = util.Http()
  repository = docker_name.Repository(repo_path)
  with docker_image.FromRegistry(
      basic_creds=util.CredentialProvider(),
      name=repository,
      transport=http_obj,
  ) as image:
    query = "?CopyFromGCR={}".format(copy_from)
    if recent_only:
      query += "&PullDays={recent_only}"
    tags_payload = json.loads(
        # pylint:disable-next=protected-access
        image._content(f"tags/list{query}").decode("utf8")
    )
  results = {}
  results["manifestsCopied"] = tags_payload.get("manifestsCopied", 0)
  results["tagsCopied"] = tags_payload.get("tagsCopied", 0)
  results["manifestsFailed"] = tags_payload.get("manifestsFailed", 0)
  results["tagsFailed"] = tags_payload.get("tagsFailed", 0)
  results["exampleFailures"] = tags_payload.get("exampleFailures", [])
  for child in tags_payload["child"]:
    child_results = CopyImagesFromGCR(
        repo_path + "/" + child, recent_only, copy_from=copy_from
    )
    results["manifestsCopied"] += child_results["manifestsCopied"]
    results["tagsCopied"] += child_results["tagsCopied"]
    results["manifestsFailed"] += child_results["manifestsFailed"]
    results["tagsFailed"] += child_results["tagsFailed"]
    results["exampleFailures"] += child_results["exampleFailures"]
  if len(results["exampleFailures"]) > 10:
    results["exampleFailures"] = results["exampleFailures"][:10]
  return results


# Returns if we should continue with migration
def MaybeCreateMissingRepos(projects, automigrate, dry_run):
  """Creates missing repos if needed and requested by the user."""
  messages = ar_requests.GetMessages()
  if len(projects) == 1:
    missing_repos = {projects[0]: GetRedirectionEnablementReport(projects[0])}
  else:
    missing_repos = GetMultiProjectRedirectionEnablementReport(projects)

  if dry_run:
    log.status.Print("Dry run enabled, no changes made.")
    return False

  num_missing_repos = sum(len(r) for r in missing_repos.values())
  if num_missing_repos:
    con = console_attr.GetConsoleAttr()
    s = ("s" if num_missing_repos > 1 else "")
    create_repos = console_io.PromptContinue(
        f"\ngcloud can automatically create the {num_missing_repos} missing"
        f" repo{s} in Artifact Registry.\nIf you would like to setup CMEK for"
        " these repos, exit now and create them manually instead.",
        "Create missing repos " + con.Colorize("(recommended)", "green"),
        default=automigrate,
    )
    if not create_repos:
      return True

    op_resources = []
    for project, repos in missing_repos.items():
      for repo in repos:
        repository_message = messages.Repository(
            name="projects/{}/locations/{}/repositories/{}".format(
                project, repo["location"], repo["repository"]
            ),
            description="Created by gcloud",
            format=messages.Repository.FormatValueValuesEnum.DOCKER,
        )
        try:
          op = ar_requests.CreateRepository(
              project, repo["location"], repository_message
          )
          op_resources.append(
              resources.REGISTRY.ParseRelativeName(
                  op.name,
                  collection="artifactregistry.projects.locations.operations",
              )
          )
        except apitools_exceptions.HttpError as e:
          log.status.Print(
              "Failed to create repository %s: %s\n" % (repo["location"]),
              e.message,
          )

    client = ar_requests.GetClient()
    for resource in op_resources:
      waiter.WaitFor(
          waiter.CloudOperationPollerNoResources(
              client.projects_locations_operations
          ),
          resource,
          message="Waiting for repo creation to complete...",
      )
  else:
    con = console_attr.GetConsoleAttr()
    log.status.Print(
        con.Colorize("OK: ", "green")
        + "All Container Registry repositories have equivalent Artifact"
        " Registry "
        "repostories.\n"
    )
  return True


def EnableUpgradeRedirection(unused_ref, args):
  """Enables upgrade redirection for the active project."""
  project = GetProject(args)
  dry_run = args.dry_run

  log.status.Print("Performing redirection enablement checks...\n")
  if not CheckRedirectionPermission([project]):
    return None

  messages = ar_requests.GetMessages()
  settings = ar_requests.GetProjectSettings(project)
  current_status = settings.legacyRedirectionState
  if (
      current_status
      == messages.ProjectSettings.LegacyRedirectionStateValueValuesEnum.REDIRECTION_FROM_GCR_IO_ENABLED
      or current_status == messages.ProjectSettings
  ):
    log.status.Print(
        f"Project {project} is already using Artifact Registry for all *gcr.io"
        " traffic."
    )
  elif (
      current_status
      == messages.ProjectSettings.LegacyRedirectionStateValueValuesEnum.REDIRECTION_FROM_GCR_IO_FINALIZED
  ):
    log.status.Print(
        f"Redirection is already enabled (and finalized) for project {project}."
    )
    return None

  if not MaybeCreateMissingRepos([project], False, dry_run):
    return None

  update = console_io.PromptContinue(
      "\nThis action will redirect all Container Registry traffic to Artifact "
      "Registry for project {}."
      " After enabling redirection, you can route traffic back to Container "
      "Registry if needed."
      .format(project),
      default=False)
  if not update:
    log.status.Print("No changes made.")
    return None

  return ar_requests.EnableUpgradeRedirection(GetProject(args))


def DisableUpgradeRedirection(unused_ref, args):
  """Disables upgrade redirection for the active project."""
  project = GetProject(args)
  messages = ar_requests.GetMessages()
  con = console_attr.GetConsoleAttr()

  log.status.Print("Disabling upgrade redirection...\n")
  if not CheckRedirectionPermission([project]):
    return None

  # If the current state is finalized, then disabling is not possible
  log.status.Print("Checking current redirection status...\n")
  settings = ar_requests.GetProjectSettings(GetProject(args))
  current_status = settings.legacyRedirectionState

  if (current_status == messages.ProjectSettings
      .LegacyRedirectionStateValueValuesEnum.REDIRECTION_FROM_GCR_IO_FINALIZED):
    log.status.Print(
        con.Colorize("FAIL:", "red") + " Redirection has already "
        "been finalized for project {}. Disabling redirection is not possible "
        "once it has been finalized.".format(project))
    return None

  update = console_io.PromptContinue(
      "This action will disable the redirection of Container Registry traffic "
      "to Artifact Registry for project {}"
      .format(project),
      default=False)
  if not update:
    log.status.Print("No changes made.")
    return None
  return ar_requests.DisableUpgradeRedirection(project)


def SanitizeRemoteRepositoryConfig(unused_ref, args, request):
  """Make sure that only one remote source is set at the same time."""
  if args.remote_mvn_repo:
    request.repository.remoteRepositoryConfig.dockerRepository = None
    request.repository.remoteRepositoryConfig.npmRepository = None
    request.repository.remoteRepositoryConfig.pythonRepository = None
    request.repository.remoteRepositoryConfig.aptRepository = None
    request.repository.remoteRepositoryConfig.yumRepository = None
  elif args.remote_docker_repo:
    request.repository.remoteRepositoryConfig.mavenRepository = None
    request.repository.remoteRepositoryConfig.npmRepository = None
    request.repository.remoteRepositoryConfig.pythonRepository = None
    request.repository.remoteRepositoryConfig.aptRepository = None
    request.repository.remoteRepositoryConfig.yumRepository = None
  elif args.remote_npm_repo:
    request.repository.remoteRepositoryConfig.dockerRepository = None
    request.repository.remoteRepositoryConfig.mavenRepository = None
    request.repository.remoteRepositoryConfig.pythonRepository = None
    request.repository.remoteRepositoryConfig.aptRepository = None
    request.repository.remoteRepositoryConfig.yumRepository = None
  elif args.remote_python_repo:
    request.repository.remoteRepositoryConfig.dockerRepository = None
    request.repository.remoteRepositoryConfig.npmRepository = None
    request.repository.remoteRepositoryConfig.mavenRepository = None
    request.repository.remoteRepositoryConfig.aptRepository = None
    request.repository.remoteRepositoryConfig.yumRepository = None
  elif args.remote_apt_repo:
    request.repository.remoteRepositoryConfig.dockerRepository = None
    request.repository.remoteRepositoryConfig.mavenRepository = None
    request.repository.remoteRepositoryConfig.npmRepository = None
    request.repository.remoteRepositoryConfig.pythonRepository = None
    request.repository.remoteRepositoryConfig.yumRepository = None
  elif args.remote_yum_repo:
    request.repository.remoteRepositoryConfig.dockerRepository = None
    request.repository.remoteRepositoryConfig.mavenRepository = None
    request.repository.remoteRepositoryConfig.npmRepository = None
    request.repository.remoteRepositoryConfig.pythonRepository = None
    request.repository.remoteRepositoryConfig.aptRepository = None

  return request


def GetMimetype(path):
  mime_type, _ = mimetypes.guess_type(path)
  return mime_type or "application/octet-stream"
