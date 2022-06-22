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
import encodings.idna  # pylint: disable=unused-import
import os
import re

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib import artifacts
from googlecloudsdk.api_lib.artifacts import exceptions as ar_exceptions
from googlecloudsdk.api_lib.util import common_args
from googlecloudsdk.calliope import base
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

  request.repository.name = repo_ref.RelativeName()
  request.repositoryId = repo_ref.repositoriesId
  request.repository.format = repo_format
  return request


def AddRepositoryFormatArg():
  """Adds the repository-format flag."""
  # We need to do this because the declarative framework doesn't support
  # hiding an enum from the help text.
  return [
      base.Argument(
          "--repository-format",
          required=True,
          help=_REPO_CREATION_HELP_TEXT)
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
  if repo_args.kms_key:
    # TODO(b/212736659): We try to check if the service account has permission
    # to the kms key but if the user does not have permission to check IAM,
    # we ignore it and continue with the repo creation. The eventual error,
    # if any, should be descriptive enough.
    try:
      project_num = project_util.GetProjectNumber(GetProject(repo_args))
      policy = ar_requests.GetCryptoKeyPolicy(repo_args.kms_key)
    except apitools_exceptions.HttpForbiddenError:
      return request
    service_account = _AR_SERVICE_ACCOUNT.format(project_num=project_num)
    has_permission = False
    for binding in policy.bindings:
      if "serviceAccount:" + service_account in binding.members and (
          binding.role == "roles/cloudkms.cryptoKeyEncrypterDecrypter" or
          binding.role == "roles/owner"):
        has_permission = True
        break
    if not has_permission:
      console_io.PromptContinue(
          prompt_string=(
              "\nGrant the Artifact Registry Service Account "
              "permission to encrypt/decrypt with the selected key [{key_name}]"
              .format(key_name=repo_args.kms_key)),
          cancel_on_no=True,
          cancel_string=(
              "The Artifact Registry Service Account needs permissions to "
              "encrypt/decrypt on the selected key.\n"
              "Learn more: https://cloud.google.com/artifact-registry/docs/cmek"
          ))
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
  return request


def DeleteVersionTags(ver_ref, ver_args, request):
  """Deletes tags associate with the specified version."""
  if not ver_args.delete_tags:
    return request
  client = _GetClientForResource(ver_ref)
  messages = _GetMessagesForResource(ver_ref)
  tag_list = ar_requests.ListTags(client, messages,
                                  ver_ref.Parent().RelativeName())
  for tag in tag_list:
    if tag.version != ver_ref.RelativeName():
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


def SlashEscapePackageName(pkg_ref, unused_args, request):
  """Escapes slashes in package name for ListVersionsRequest."""
  request.parent = "{}/packages/{}".format(
      pkg_ref.Parent().RelativeName(), pkg_ref.packagesId.replace("/", "%2F"))
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
    # Otherwise request gets overriden somewhere down the line.
    ver_args.page_size = ver_args.limit

  return request


def SlashUnescapePackageName(response, unused_args):
  """Unescapes slashes in package name from ListPackagesResponse."""
  ret = []
  for ver in response:
    ver.name = os.path.basename(ver.name)
    ver.name = ver.name.replace("%2F", "/")
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
  messages = ar_requests.GetMessages()
  existing_buckets = GetExistingGCRBuckets(buckets, project)

  def RepoMsg(bucket):
    return messages.Repository(
        name="projects/{}/locations/{}/repositories/{}".format(
            project, bucket["location"], bucket["repository"]),
        format=messages.Repository.FormatValueValuesEnum.DOCKER),

  return map(RepoMsg, existing_buckets)


def GetExistingGCRBuckets(buckets, project):
  """Gets the list of GCR bucket names that exist in the project."""
  existing_buckets = []

  project_id_for_bucket = project
  if ":" in project:
    domain, project_id = project.split(":")
    project_id_for_bucket = "{}.{}.a".format(project_id, domain)
  for bucket in buckets:
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
    repos.extend([repo for repo in sublist])
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

  # Parse fully qualified path in package argument
  if package:
    if re.match(r"projects\/.*\/locations\/.*\/repositories\/.*\/packages\/.*",
                package):
      params = package.replace("projects/", "", 1).replace(
          "/locations/", " ", 1).replace("/repositories/", " ",
                                         1).replace("/packages/", " ",
                                                    1).split(" ")
      project, location, repo, package = [params[i] for i in range(len(params))]

  # Escape slashes in package name
  if package:
    package = package.replace("/", "%2F")

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

  for file in files:
    file.name = resources.REGISTRY.ParseRelativeName(
        file.name,
        collection="artifactregistry.projects.locations.repositories.files"
    ).filesId.replace("%2F", "/")

  return files


def AddEncryptionLogToRepositoryInfo(response, unused_args):
  """Adds encryption info log to repository info."""
  if response.kmsKeyName:
    log.status.Print("Encryption: Customer-managed key")
  else:
    log.status.Print("Encryption: Google-managed key")
  return response


def ConvertBytesToMB(response, unused_args):
  if response.sizeBytes is not None:
    log.status.Print("Repository Size: {0:.3f}MB".format(response.sizeBytes /
                                                         1e6))
  else:
    log.status.Print("Repository Size: {0:.3f}MB".format(0))
  response.sizeBytes = None
  return response


def SlashUnescapePackageNameHook(ref, args, req):
  package = args.package if args.package else ref.packagesId
  if "@" in package:
    escaped_pkg_name = package.replace("/", "%2F")
    req.name = req.name.replace(package, escaped_pkg_name)
  return req


def IssueGetProjectSettingsRequest(unused_ref, args):
  return ar_requests.GetProjectSettings(GetProject(args))


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
  locations = ar_requests.ListLocations(project, 100)

  # Sorting is performed so that Python2 & 3 agree on the order of API calls
  # in scenario tests.
  gcr_repos = GetExistingGCRBuckets(
      sorted(_GCR_BUCKETS.values(), key=lambda x: x["repository"]), project)

  failed_repos = []
  repo_report = []
  report_line = []
  con = console_attr.GetConsoleAttr()

  # For each gcr repo in a location that our environment supports,
  # is there an associated repo in AR?
  for gcr_repo in gcr_repos:
    if gcr_repo["location"] in locations:
      report_line = [gcr_repo["repository"], gcr_repo["location"]]
      ar_repo_name = "projects/{}/locations/{}/repositories/{}".format(
          project, gcr_repo["location"], gcr_repo["repository"])
      try:
        ar_repo = ar_requests.GetRepository(ar_repo_name)
        report_line.append(con.Colorize(ar_repo.name, "green"))
      except apitools_exceptions.HttpNotFoundError:
        report_line.append(con.Colorize("NOT FOUND", "red"))
        failed_repos.append(gcr_repo)
      repo_report.append(report_line)

  log.status.Print("Redirection enablement report:\n")
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
  return failed_repos


def CheckRedirectionPermission(project):
  con = console_attr.GetConsoleAttr()
  authorized = ar_requests.TestRedirectionIAMPermission(project)
  if not authorized:
    log.status.Print(
        con.Colorize("FAIL: ", "red") + "This operation requires "
        "the {} permission(s) on project {}.".format(
            ",".join(ar_requests.REDIRECT_PERMISSIONS), project))
  return authorized


def EnableUpgradeRedirection(unused_ref, args):
  """Enables upgrade redirection for the active project."""
  project = GetProject(args)
  con = console_attr.GetConsoleAttr()
  dry_run = args.dry_run

  log.status.Print("Performing redirection enablement checks...\n")

  if not CheckRedirectionPermission(project):
    return None

  messages = ar_requests.GetMessages()
  settings = ar_requests.GetProjectSettings(project)
  current_status = settings.legacyRedirectionState
  if (current_status == messages.ProjectSettings
      .LegacyRedirectionStateValueValuesEnum.REDIRECTION_FROM_GCR_IO_ENABLED or
      current_status == messages.ProjectSettings):
    log.status.Print(
        "Redirection is already enabled for project {}.".format(project))
  elif (
      current_status == messages.ProjectSettings
      .LegacyRedirectionStateValueValuesEnum.REDIRECTION_FROM_GCR_IO_FINALIZED):
    log.status.Print(
        "Redirection is already enabled (and finalized) for project {}.".format(
            project))
    return None

  failed_repos = GetRedirectionEnablementReport(project)

  if failed_repos:
    log.status.Print(
        con.Colorize("WARNING: ", "yellow") +
        "Not all Container Registry repositories have Artifact Registry repositories created to handle redirected requests."
    )

    for failed_repo in failed_repos:
      log.status.Print(
          "\nContainer Registry repository '{}' should redirect to "
          "an Artifact Registry Docker repository in location '{}' named '{}'. "
          "This repository can be created with:\n".format(
              con.Emphasize(failed_repo["repository"], bold=True),
              con.Emphasize(failed_repo["location"], bold=True),
              con.Emphasize(failed_repo["repository"], bold=True)))

      log.status.Print(
          con.Emphasize(
              "gcloud artifacts repositories create {} --location={} --project={} --repository-format=DOCKER"
              .format(failed_repo["repository"], failed_repo["location"],
                      project)))

    log.status.Print(
        "\nIf Artifact Registry repositories are not created, the following Container Registry repositories will no"
        " longer serve requests:")
    for failed_repo in failed_repos:
      log.status.Print(con.Emphasize(failed_repo["repository"], bold=True))

  else:
    log.status.Print(
        con.Colorize("OK: ", "green") +
        "All Container Registry repositories have equivalent Artifact Registry "
        "repostories.\n")

  if dry_run:
    log.status.Print("Dry run enabled, no changes made.")
    return None

  update = console_io.PromptContinue(
      "\nThis action will redirect all Container Registry traffic to Artifact Registry for project {}."
      " After enabling redirection, you can route traffic back to Container Registry if needed, "
      " or you can finalize redirection to make redirection permanent.".format(
          project),
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
  if not CheckRedirectionPermission(project):
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
      "This action will disable the redirection of Container Registry traffic to Artifact Registry for project {}"
      .format(project),
      default=False)
  if not update:
    log.status.Print("No changes made.")
    return None
  return ar_requests.DisableUpgradeRedirection(project)


def FinalizeUpgradeRedirection(unused_ref, args):
  """Finalizes upgrade redirection for the active project."""
  con = console_attr.GetConsoleAttr()
  project = GetProject(args)
  messages = ar_requests.GetMessages()

  log.status.Print("Finalizing upgrade redirection...\n")
  if not CheckRedirectionPermission(project):
    return None

  # Check the current status is enabled first.
  log.status.Print("Checking current redirection status...\n")
  settings = ar_requests.GetProjectSettings(GetProject(args))
  current_status = settings.legacyRedirectionState
  if (current_status == messages.ProjectSettings
      .LegacyRedirectionStateValueValuesEnum.REDIRECTION_FROM_GCR_IO_FINALIZED):
    log.status.Print(
        "Redirection is already finalized for project {}.".format(project))
    return None
  if (current_status != messages.ProjectSettings
      .LegacyRedirectionStateValueValuesEnum.REDIRECTION_FROM_GCR_IO_ENABLED):
    log.status.Print(
        "Redirection is not currently enabled for project {}.".format(project))
    log.status.Print(
        "Enable redirection using 'gcloud artifacts settings enable-upgrade-redirection'"
    )
    return None

  # Run the same report as enabling in case new repos have been added since.
  failed_repos = GetRedirectionEnablementReport(project)
  if failed_repos:
    log.status.Print(
        con.Colorize("FAIL: ", "red") +
        "Redirection cannot be enabled until all Container Registry repos have equivalent Artifact Registry repositories to redirect to:"
    )
    return None

  update = console_io.PromptContinue(
      "This action permanently redirects gcr.io traffic to Artifact Registry "
      "for project {}.".format(con.Emphasize(project, bold=True)),
      default=False)
  if not update:
    log.status.Print("No changes made.")
    return None
  return ar_requests.FinalizeUpgradeRedirection(GetProject(args))


def SanitizeRemoteRepositoryConfig(unused_ref, args, request):
  """Make sure that only one remote source is set at the same time."""
  if args.remote_mvn_repo:
    request.repository.remoteRepositoryConfig.dockerRepository = None
    request.repository.remoteRepositoryConfig.npmRepository = None
    request.repository.remoteRepositoryConfig.pythonRepository = None
  elif args.remote_docker_repo:
    request.repository.remoteRepositoryConfig.mavenRepository = None
    request.repository.remoteRepositoryConfig.npmRepository = None
    request.repository.remoteRepositoryConfig.pythonRepository = None
  elif args.remote_npm_repo:
    request.repository.remoteRepositoryConfig.dockerRepository = None
    request.repository.remoteRepositoryConfig.mavenRepository = None
    request.repository.remoteRepositoryConfig.pythonRepository = None
  elif args.remote_python_repo:
    request.repository.remoteRepositoryConfig.dockerRepository = None
    request.repository.remoteRepositoryConfig.npmRepository = None
    request.repository.remoteRepositoryConfig.mavenRepository = None

  return request
