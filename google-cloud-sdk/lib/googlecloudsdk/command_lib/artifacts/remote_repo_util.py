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
"""Remote repo utils for Artifact Registry repository commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re
from typing import List

from googlecloudsdk.api_lib.artifacts import exceptions as ar_exceptions
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.artifacts import requests as ar_requests
from googlecloudsdk.command_lib.util.apis import arg_utils

GITHUB_URI = "https://github.com"
GOOGLE_MODULE_PROXY = re.compile(
    r"(http(|s))://proxy\.golang\.org(|/)"
)


def Args():
  """Adds the remote-<facade>-repo flags."""
  # We need to do this because these flags need to be able to accept either a
  # PublicRepository enum or a string registry URI.
  return [
      base.Argument(
          "--remote-mvn-repo",
          help=_RemoteRepoHelpText(facade="Maven", hide_custom_remotes=False),
      ),
      base.Argument(
          "--remote-docker-repo",
          help=_RemoteRepoHelpText(facade="Docker", hide_custom_remotes=False),
      ),
      base.Argument(
          "--remote-npm-repo",
          help=_RemoteRepoHelpText(facade="Npm", hide_custom_remotes=False),
      ),
      base.Argument(
          "--remote-python-repo",
          help=_RemoteRepoHelpText(facade="Python", hide_custom_remotes=False),
      ),
      base.Argument(
          "--remote-apt-repo",
          help=_OsPackageRemoteRepoHelpText(
              facade="Apt", hide_custom_remotes=True
          ),
      ),
      base.Argument(
          "--remote-yum-repo",
          help=_OsPackageRemoteRepoHelpText(
              facade="Yum", hide_custom_remotes=True
          ),
      ),
      base.Argument(
          "--remote-go-repo", help=_GoRemoteRepoHelpText()
      ),
      base.Argument(
          "--remote-username",
          help="Remote Repository upstream registry username.",
      ),
      base.Argument(
          "--remote-password-secret-version",
          help="""\
          Secret Manager secret version that contains password for the
          remote repository upstream.
          """,
      ),
      base.Argument(
          "--service-directory-config", help="""\
          Service Directory config link for using Private Networks. Format:
          projects/<project>/locations/<location>/namespaces/<namespace>/services/<service>
          """, hidden=True
      ),
      base.Argument(
          "--remote-repo",
          help=_CommonRemoteRepoHelpText(), hidden=True
      ),
  ]


def IsRemoteRepoRequest(repo_args) -> bool:
  """Returns whether or not the repo mode specifies a remote repository."""
  return (
      hasattr(repo_args, "mode")
      and arg_utils.ChoiceToEnumName(repo_args.mode) == "REMOTE_REPOSITORY"
  )


def AppendRemoteRepoConfigToRequest(messages, repo_args, request):
  """Adds remote repository config to CreateRepositoryRequest or UpdateRepositoryRequest."""
  remote_cfg = messages.RemoteRepositoryConfig()
  remote_cfg.description = repo_args.remote_repo_config_desc
  # Credentials
  username = repo_args.remote_username
  secret = repo_args.remote_password_secret_version
  if username or secret:
    creds = messages.UpstreamCredentials()
    creds.usernamePasswordCredentials = messages.UsernamePasswordCredentials()
    if username:
      creds.usernamePasswordCredentials.username = username
    if secret:
      creds.usernamePasswordCredentials.passwordSecretVersion = secret
    remote_cfg.upstreamCredentials = creds

  # Disable Remote Validation
  if repo_args.disable_remote_validation:
    remote_cfg.disableUpstreamValidation = True

  # Service Directory config for Private networks
  sd_config = repo_args.service_directory_config
  if sd_config:
    remote_cfg.serviceDirectoryConfig = messages.ServiceDirectoryConfig()
    remote_cfg.serviceDirectoryConfig.service = sd_config

  # MAVEN
  if repo_args.remote_mvn_repo:
    facade, remote_input = "Maven", repo_args.remote_mvn_repo
    enum_message = _ChoiceToRemoteEnum(facade, remote_input)
    if enum_message:  # input is PublicRepository
      remote_cfg.mavenRepository = messages.MavenRepository()
      remote_cfg.mavenRepository.publicRepository = enum_message
    elif _IsRemoteURI(remote_input):  # input is CustomRepository
      remote_cfg.commonRepository = messages.CommonRemoteRepository()
      remote_cfg.commonRepository.uri = remote_input
    elif _IsARRemote(remote_input):  # input is ArtifactRegistryRepository
      remote_cfg.commonRepository = messages.CommonRemoteRepository()
      remote_cfg.commonRepository.uri = remote_input
    else:  # raise error
      _RaiseRemoteRepoUpstreamError(facade, remote_input)

  # DOCKER
  elif repo_args.remote_docker_repo:
    facade, remote_input = "Docker", repo_args.remote_docker_repo
    enum_message = _ChoiceToRemoteEnum(facade, remote_input)
    if enum_message:  # input is PublicRepository
      remote_cfg.dockerRepository = messages.DockerRepository()
      remote_cfg.dockerRepository.publicRepository = enum_message
    elif _IsRemoteURI(remote_input):  # input is CustomRepository
      remote_cfg.commonRepository = messages.CommonRemoteRepository()
      remote_cfg.commonRepository.uri = remote_input
    elif _IsARRemote(remote_input):  # input is ArtifactRegistryRepository
      remote_cfg.commonRepository = messages.CommonRemoteRepository()
      remote_cfg.commonRepository.uri = remote_input
    else:  # raise error
      _RaiseRemoteRepoUpstreamError(facade, remote_input)

  # NPM
  elif repo_args.remote_npm_repo:
    facade, remote_input = "Npm", repo_args.remote_npm_repo
    enum_message = _ChoiceToRemoteEnum(facade, remote_input)
    if enum_message:  # input is PublicRepository
      remote_cfg.npmRepository = messages.NpmRepository()
      remote_cfg.npmRepository.publicRepository = enum_message
    elif _IsRemoteURI(remote_input):  # input is CustomRepository
      remote_cfg.commonRepository = messages.CommonRemoteRepository()
      remote_cfg.commonRepository.uri = remote_input
    elif _IsARRemote(remote_input):  # input is ArtifactRegistryRepository
      remote_cfg.commonRepository = messages.CommonRemoteRepository()
      remote_cfg.commonRepository.uri = remote_input
    else:  # raise error
      _RaiseRemoteRepoUpstreamError(facade, remote_input)

  # PYTHON
  elif repo_args.remote_python_repo:
    facade, remote_input = "Python", repo_args.remote_python_repo
    enum_message = _ChoiceToRemoteEnum(facade, remote_input)
    if enum_message:  # input is PublicRepository
      remote_cfg.pythonRepository = messages.PythonRepository()
      remote_cfg.pythonRepository.publicRepository = enum_message
    elif _IsRemoteURI(remote_input):  # input is CustomRepository
      remote_cfg.commonRepository = messages.CommonRemoteRepository()
      remote_cfg.commonRepository.uri = remote_input
    elif _IsARRemote(remote_input):  # input is ArtifactRegistryRepository
      remote_cfg.commonRepository = messages.CommonRemoteRepository()
      remote_cfg.commonRepository.uri = remote_input
    else:  # raise error
      _RaiseRemoteRepoUpstreamError(facade, remote_input)

  # APT
  elif repo_args.remote_apt_repo:
    facade, remote_base, remote_path = (
        "Apt",
        repo_args.remote_apt_repo,
        repo_args.remote_apt_repo_path,
    )
    enum_message = _ChoiceToRemoteEnum(facade, remote_base)
    if enum_message:  # input is PublicRepository
      remote_cfg.aptRepository = messages.AptRepository()
      remote_cfg.aptRepository.publicRepository = (
          messages.GoogleDevtoolsArtifactregistryV1RemoteRepositoryConfigAptRepositoryPublicRepository()
      )
      remote_cfg.aptRepository.publicRepository.repositoryBase = enum_message
      remote_cfg.aptRepository.publicRepository.repositoryPath = remote_path
    elif _IsRemoteURI(_OsPackageUri(remote_base, remote_path)):
      # input is CustomRepository
      remote_cfg.commonRepository = messages.CommonRemoteRepository()
      remote_cfg.commonRepository.uri = _OsPackageUri(remote_base, remote_path)
    elif _IsARRemote(remote_base):  # input is ArtifactRegistryRepository
      if remote_path:
        raise ar_exceptions.InvalidInputValueError(
            "--remote-apt-repo-path is not supported for Artifact Registry"
            " Repository upstream."
        )
      remote_cfg.commonRepository = messages.CommonRemoteRepository()
      remote_cfg.commonRepository.uri = remote_base
    else:  # raise error
      _RaiseRemoteRepoUpstreamError(facade, remote_base)

  # YUM
  elif repo_args.remote_yum_repo:
    facade, remote_base, remote_path = (
        "Yum",
        repo_args.remote_yum_repo,
        repo_args.remote_yum_repo_path,
    )
    enum_message = _ChoiceToRemoteEnum(facade, remote_base)
    if enum_message:  # input is PublicRepository
      remote_cfg.yumRepository = messages.YumRepository()
      remote_cfg.yumRepository.publicRepository = (
          messages.GoogleDevtoolsArtifactregistryV1RemoteRepositoryConfigYumRepositoryPublicRepository()
      )
      remote_cfg.yumRepository.publicRepository.repositoryBase = enum_message
      remote_cfg.yumRepository.publicRepository.repositoryPath = remote_path
    elif _IsRemoteURI(_OsPackageUri(remote_base, remote_path)):
      # input is CustomRepository
      remote_cfg.commonRepository = messages.CommonRemoteRepository()
      remote_cfg.commonRepository.uri = _OsPackageUri(remote_base, remote_path)
    elif _IsARRemote(remote_base):  # input is ArtifactRegistryRepository
      if remote_path:
        raise ar_exceptions.InvalidInputValueError(
            "--remote-yum-repo-path is not supported for Artifact Registry"
            " Repository upstream."
        )
      remote_cfg.commonRepository = messages.CommonRemoteRepository()
      remote_cfg.commonRepository.uri = remote_base
    else:  # raise error
      _RaiseRemoteRepoUpstreamError(facade, remote_base)

  # GO
  elif repo_args.remote_go_repo:
    facade, remote_input = "Go", repo_args.remote_go_repo
    # Go does not have Public enums
    if _IsRemoteURI(remote_input):  # input is CustomRepository
      if remote_input[-1] == "/":
        remote_input = remote_input[:-1]
      if remote_input != GITHUB_URI and not GOOGLE_MODULE_PROXY.match(
          remote_input
      ):
        _RaiseCustomUpstreamUnsupportedError(
            facade, remote_input, ["https://proxy.golang.org"]
        )
      remote_cfg.commonRepository = messages.CommonRemoteRepository()
      remote_cfg.commonRepository.uri = remote_input
    elif _IsARRemote(remote_input):  # input is ArtifactRegistryRepository
      _RaiseArtifactRegistryUpstreamUnsupportedError(facade)
    else:  # raise error
      _RaiseRemoteRepoUpstreamError(facade, remote_input)

  # COMMON
  elif repo_args.remote_repo:
    remote_input = repo_args.remote_repo
    if _IsRemoteURI(remote_input):  # input is CustomRepository
      remote_cfg.commonRepository = messages.CommonRemoteRepository()
      remote_cfg.commonRepository.uri = remote_input
  else:
    return request

  request.repository.remoteRepositoryConfig = remote_cfg
  return request


def _RemoteRepoHelpText(facade: str, hide_custom_remotes: bool) -> str:
  if hide_custom_remotes:
    return """\
({facade} only) Repo upstream for {facade_lower} remote repository.
REMOTE_{command}_REPO must be one of: [{enums}].
""".format(
        facade=facade,
        facade_lower=facade.lower(),
        command=_LanguagePackageCommandName(facade),
        enums=_EnumsStrForFacade(facade),
    )
  return """\
({facade} only) Repo upstream for {facade_lower} remote repository.
REMOTE_{command}_REPO can be either:
  - one of the following enums: [{enums}].
  - an http/https custom registry uri (ex: https://my.{facade_lower}.registry)
""".format(
      facade=facade,
      facade_lower=facade.lower(),
      command=_LanguagePackageCommandName(facade),
      enums=_EnumsStrForFacade(facade),
  )


def _GoRemoteRepoHelpText() -> str:
  return (
      '(Go only) Repo upstream for Go remote repository. '
      '"https://proxy.golang.org/" is the only valid value.'
  )


def _CommonRemoteRepoHelpText() -> str:
  return (
      'An upstream for a given remote repository. Ex: "https://github.com"'
      ', "https://docker.io/v2/" are valid values for their given formats of'
      ' Go and Docker respectively.'
  )


def _OsPackageRemoteRepoHelpText(facade: str, hide_custom_remotes: bool) -> str:
  if hide_custom_remotes:
    return """\
({facade} only) Repository base for {facade_lower} remote repository.
REMOTE_{facade_upper}_REPO must be one of: [{enums}].
""".format(
        facade=facade,
        facade_lower=facade.lower(),
        facade_upper=facade.upper(),
        enums=_EnumsStrForFacade(facade),
    )
  return """\
({facade} only) Repository base for {facade_lower} remote repository.
REMOTE_{facade_upper}_REPO can be either:
  - one of the following enums: [{enums}].
  - an http/https custom registry uri (ex: https://my.{facade_lower}.registry)
""".format(
      facade=facade,
      facade_lower=facade.lower(),
      facade_upper=facade.upper(),
      enums=_EnumsStrForFacade(facade),
  )


def _LanguagePackageCommandName(facade: str) -> str:
  if facade == "Maven":
    return "MVN"
  return facade.upper()


def _ChoiceToRemoteEnum(facade: str, remote_input: str):
  """Converts the remote repo input to a PublicRepository Enum message or None."""
  enums = _EnumsMessageForFacade(facade)
  name = arg_utils.ChoiceToEnumName(remote_input)
  try:
    return enums.lookup_by_name(name)
  except KeyError:
    return None


def _EnumsMessageForFacade(facade: str):
  """Returns the PublicRepository enum messages for a facade."""
  facade_to_enum = {
      "Maven": (
          ar_requests.GetMessages()
          .MavenRepository()
          .PublicRepositoryValueValuesEnum
      ),
      "Docker": (
          ar_requests.GetMessages()
          .DockerRepository()
          .PublicRepositoryValueValuesEnum
      ),
      "Npm": (
          ar_requests.GetMessages()
          .NpmRepository()
          .PublicRepositoryValueValuesEnum
      ),
      "Python": (
          ar_requests.GetMessages()
          .PythonRepository()
          .PublicRepositoryValueValuesEnum
      ),
      "Apt": (
          ar_requests.GetMessages()
          .GoogleDevtoolsArtifactregistryV1RemoteRepositoryConfigAptRepositoryPublicRepository()
          .RepositoryBaseValueValuesEnum
      ),
      "Yum": (
          ar_requests.GetMessages()
          .GoogleDevtoolsArtifactregistryV1RemoteRepositoryConfigYumRepositoryPublicRepository()
          .RepositoryBaseValueValuesEnum
      ),
      "Ruby": (
          ar_requests.GetMessages()
          .CommonRemoteRepository()
      ),
  }
  if facade not in facade_to_enum:
    return None
  return facade_to_enum[facade]


def _EnumsStrForFacade(facade: str) -> str:
  """Returns the human-readable PublicRepository enum strings for a facade."""
  return _EnumsMessageToStr(_EnumsMessageForFacade(facade))


def _EnumsMessageToStr(enums) -> str:
  """Returns the human-readable PublicRepository enum strings."""
  if enums is None:
    return ""
  return ", ".join(
      arg_utils.EnumNameToChoice(name)
      for name, number in sorted(enums.to_dict().items())
      if number != 0  # Ignore UNSPECIFIED enum values.
  )


def _OsPackageUri(remote_base, remote_path):
  # Don't concatenate if remote_path not given.
  if not remote_path:
    return remote_base
  # Add '/' to end of remote_base if not already present.
  if remote_base[-1] != "/":
    remote_base = remote_base + "/"
  return remote_base + remote_path


def _IsRemoteURI(remote_input: str) -> bool:
  return remote_input.startswith("https://") or remote_input.startswith(
      "http://"
  )


def _IsARRemote(remote_input: str) -> bool:
  return remote_input.startswith("projects/")


def _RaiseRemoteRepoUpstreamError(facade: str, remote_input: str):
  """Raises an error for a remote repo upstream error."""
  well_known_enum_requirement = ""
  if _EnumsStrForFacade(facade):
    enums = _EnumsMessageForFacade(facade)
    well_known_enum_requirement = (
        " If you intended to enter a well known upstream repo, valid choices"
        f" are: [{enums}]."
    )

  custom_uri_requirement = (
      " If you intended to enter a custom upstream URI, this value must start"
      " with 'https://' or 'http://'."
  )
  raise ar_exceptions.InvalidInputValueError(
      "Invalid repo upstream for remote repository:"
      f" '{remote_input}'.{well_known_enum_requirement}{custom_uri_requirement}"
  )


def _RaiseArtifactRegistryUpstreamUnsupportedError(facade: str):
  raise ar_exceptions.InvalidInputValueError(
      f"Artifact Registry upstream is not supported for {facade}."
  )


def _RaiseCustomUpstreamUnsupportedError(
    facade: str, remote_input: str, allowed: List[str]
):
  allowed_choices = ", ".join(allowed)
  raise ar_exceptions.InvalidInputValueError(
      f"Custom upstream {remote_input} is not supported for {facade}. Valid"
      f" choices are [{allowed_choices}].\n"
  )
