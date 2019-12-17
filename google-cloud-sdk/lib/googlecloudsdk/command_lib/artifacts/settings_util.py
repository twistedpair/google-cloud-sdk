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
"""Utility for forming settings for Artifacts Registry repositories."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.artifacts import exceptions as ar_exceptions
from googlecloudsdk.command_lib.artifacts import util as ar_util
from googlecloudsdk.core import properties

_PROJECT_NOT_FOUND_ERROR = """\
Failed to find attribute [project]. \
The attribute can be set in the following ways:
- provide the argument [--project] on the command line
- set the property [core/project]"""

_REPO_NOT_FOUND_ERROR = """\
Failed to find attribute [repository]. \
The attribute can be set in the following ways:
- provide the argument [--repository] on the command line
- set the property [artifacts/repository]"""

_LOCATION_NOT_FOUND_ERROR = """\
Failed to find attribute [location]. \
The attribute can be set in the following ways:
- provide the argument [--location] on the command line
- set the property [artifacts/location]"""


def _GetRequiredProjectValue(args):
  if not args.project and not properties.VALUES.core.project.Get():
    raise ar_exceptions.InvalidInputValueError(_PROJECT_NOT_FOUND_ERROR)
  return ar_util.GetProject(args)


def _GetRequiredRepoValue(args):
  if not args.repository and not properties.VALUES.artifacts.repository.Get():
    raise ar_exceptions.InvalidInputValueError(_REPO_NOT_FOUND_ERROR)
  return ar_util.GetRepo(args)


def _GetRequiredLocationValue(args):
  if not args.location and not properties.VALUES.artifacts.location.Get():
    raise ar_exceptions.InvalidInputValueError(_LOCATION_NOT_FOUND_ERROR)
  return ar_util.GetLocation(args)


def _GetRepoPath(args):
  return _GetRequiredProjectValue(args) + "/" + _GetRequiredRepoValue(args)


def GetNpmSettingsSnippet(args):
  """Forms an npm settings snippet to add to the .npmrc file.

  Args:
    args: an argparse namespace. All the arguments that were provided to this
      command invocation.

  Returns:
    An npm settings snippet.
  """
  repo_path = _GetRepoPath(args)
  registry_path = "{location}-npm.pkg.dev/{repo_path}/".format(**{
      "location": _GetRequiredLocationValue(args),
      "repo_path": repo_path
  })
  configured_registry = "registry"
  if args.scope:
    if not args.scope.startswith("@") or len(args.scope) <= 1:
      raise ar_exceptions.InvalidInputValueError(
          "Scope name must start with '@' and be longer than 1 character.")
    configured_registry = args.scope + ":" + configured_registry

  npm_setting_template = """\
Please insert following snippet into your .npmrc

======================================================
{configured_registry}=https://{registry_path}
//{registry_path}:_password=""
//{registry_path}:username=oauth2accesstoken
//{registry_path}:email=not.valid@email.com
//{registry_path}:always-auth=true
======================================================
"""

  data = {
      "configured_registry": configured_registry,
      "registry_path": registry_path,
      "repo_path": repo_path,
  }
  return npm_setting_template.format(**data)


def GetMavenSnippet(args):
  """Forms a maven snippet to add to the pom.xml file.

  Args:
    args: an argparse namespace. All the arguments that were provided to this
      command invocation.

  Returns:
    A maven snippet.
  """

  repo_path = _GetRepoPath(args)
  mvn_template = """\
Please insert following snippet into your pom.xml

======================================================
<project>
  <distributionManagement>
    <snapshotRepository>
      <id>{server_id}</id>
      <url>artifactregistry://{location}-maven.pkg.dev/{repo_path}</url>
    </snapshotRepository>
    <repository>
      <id>{server_id}</id>
      <url>artifactregistry://{location}-maven.pkg.dev/{repo_path}</url>
    </repository>
  </distributionManagement>

  <repositories>
    <repository>
      <id>{server_id}</id>
      <url>artifactregistry://{location}-maven.pkg.dev/{repo_path}</url>
      <releases>
        <enabled>true</enabled>
      </releases>
      <snapshots>
        <enabled>true</enabled>
      </snapshots>
    </repository>
  </repositories>

  <build>
    <extensions>
      <extension>
        <groupId>com.google.cloud.artifactregistry</groupId>
        <artifactId>artifactregistry-maven-wagon</artifactId>
        <version>{extension_version}</version>
      </extension>
    </extensions>
  </build>
</project>
======================================================
"""

  data = {
      "location": _GetRequiredLocationValue(args),
      "server_id": "artifact-registry",
      "extension_version": "1.2.1",
      "repo_path": repo_path,
  }
  return mvn_template.format(**data)


def GetGradleSnippet(args):
  """Forms a gradle snippet to add to the build.gradle file.

  Args:
    args: an argparse namespace. All the arguments that were provided to this
      command invocation.

  Returns:
    A gradle snippet.
  """

  repo_path = _GetRepoPath(args)
  gradle_template = """\
Please insert following snippet into your build.gradle
see docs.gradle.org/current/userguide/publishing_maven.html

======================================================
plugins {{
  id "maven-publish"
  id "com.google.cloud.artifactregistry.gradle-plugin" version "1.2.1"
}}

publishing {{
  repositories {{
    maven {{
      url "artifactregistry://{location}-maven.pkg.dev/{repo_path}"
    }}
  }}
}}

repositories {{
  maven {{
    url "artifactregistry://{location}-maven.pkg.dev/{repo_path}"
  }}
}}
======================================================
"""

  data = {
      "location": _GetRequiredLocationValue(args),
      "repo_path": repo_path,
  }
  return gradle_template.format(**data)
