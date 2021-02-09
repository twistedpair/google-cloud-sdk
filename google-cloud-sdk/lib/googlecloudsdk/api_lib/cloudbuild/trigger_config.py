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
"""Set up flags for creating triggers."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.cloudbuild import cloudbuild_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions as c_exceptions

_CREATE_FILE_DESC = ('A file that contains the configuration for the '
                     'WorkerPool to be created.')
_UPDATE_FILE_DESC = ('A file that contains updates to the configuration for '
                     'the WorkerPool.')


def AddTriggerArgs(parser):
  """Set up the generic argparse flags for creating or updating a build trigger.

  Args:
    parser: An argparse.ArgumentParser-like object.

  Returns:
    An empty parser group to be populated with flags specific to a trigger-type.
  """

  parser.display_info.AddFormat("""
          table(
            name,
            createTime.date('%Y-%m-%dT%H:%M:%S%Oz', undefined='-'),
            status
          )
        """)

  trigger_config = parser.add_mutually_exclusive_group(required=True)

  # Allow trigger config to be specified on the command line or STDIN.
  trigger_config.add_argument(
      '--trigger-config',
      help=(
          'Path to Build Trigger config file (JSON or YAML format). For more '
          'details, see https://cloud.google.com/cloud-build/docs/api/reference/rest/v1/projects.triggers#BuildTrigger'
      ),
      metavar='PATH',
  )

  # Trigger configuration
  flag_config = trigger_config.add_argument_group(
      help='Flag based trigger configuration')
  flag_config.add_argument('--name', help='Build trigger name.')
  flag_config.add_argument('--description', help='Build trigger description.')

  return flag_config


def ParseTriggerArgs(args, messages):
  """Parses flags generic to all triggers.

  Args:
    args: An argparse arguments object.
    messages: A Cloud Build messages module

  Returns:
    A partially populated build trigger and a boolean indicating whether or not
    the full trigger was loaded from a file.
  """
  if args.trigger_config:
    trigger = cloudbuild_util.LoadMessageFromPath(
        path=args.trigger_config,
        msg_type=messages.BuildTrigger,
        msg_friendly_name='build trigger config',
        skip_camel_case=['substitutions'])
    return trigger, True

  trigger = messages.BuildTrigger()
  trigger.name = args.name
  trigger.description = args.description
  return trigger, False


def AddRepoEventArgs(flag_config):
  """Adds additional argparse flags related to repo events.

  Args:
    flag_config: argparse argument group. Additional flags will be added to this
      group to cover common build configuration settings.
  """

  flag_config.add_argument(
      '--included-files',
      help='Glob filter. Changes affecting at least one included file will trigger builds.',
      type=arg_parsers.ArgList(),
      metavar='GLOB',
  )
  flag_config.add_argument(
      '--ignored-files',
      help='Glob filter. Changes only affecting ignored files won\'t trigger builds.',
      type=arg_parsers.ArgList(),
      metavar='GLOB',
  )


def AddSubstitutions(argument_group):
  """Adds a substituion flag to the given argument group.

  Args:
    argument_group: argparse argument group to which the substitution flag will
      be added.
  """

  argument_group.add_argument(
      '--substitutions',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      help="""\
Parameters to be substituted in the build specification.

For example (using some nonsensical substitution keys; all keys must begin with
an underscore):

  $ gcloud builds triggers create ... --config config.yaml
      --substitutions _FAVORITE_COLOR=blue,_NUM_CANDIES=10

This will result in a build where every occurrence of ```${_FAVORITE_COLOR}```
in certain fields is replaced by "blue", and similarly for ```${_NUM_CANDIES}```
and "10".

Only the following built-in variables can be specified with the
`--substitutions` flag: REPO_NAME, BRANCH_NAME, TAG_NAME, REVISION_ID,
COMMIT_SHA, SHORT_SHA.

For more details, see:
https://cloud.google.com/cloud-build/docs/api/build-requests#substitutions
""")


def AddBuildConfigArgs(flag_config):
  """Adds additional argparse flags to a group for build configuration options.

  Args:
    flag_config: argparse argument group. Additional flags will be added to this
      group to cover common build configuration settings.
  """

  # Build config and inline config support substitutions whereas dockerfile
  # does not. We can't have a flag with the same name in two separate
  # groups so we have to have one flag outside of the config argument group.
  AddSubstitutions(flag_config)

  build_config = AddBuildFileConfigArgs(flag_config)

  inline = build_config.add_argument_group(help='Build configuration file')
  inline.add_argument(
      '--inline-config',
      metavar='PATH',
      help="""\
      Local path to a YAML or JSON file containing a build configuration.
    """)

  docker = build_config.add_argument_group(
      help='Dockerfile build configuration flags')
  docker.add_argument(
      '--dockerfile',
      help="""\
Path of Dockerfile to use for builds in the repository.

If specified, a build config will be generated to run docker
build using the specified file.

The filename is relative to the Dockerfile directory.
""")
  docker.add_argument(
      '--dockerfile-dir',
      default='/',
      help="""\
Location of the directory containing the Dockerfile in the repository.

The directory will also be used as the Docker build context.
""")
  docker.add_argument(
      '--dockerfile-image',
      help="""\
Docker image name to build.

If not specified, gcr.io/PROJECT/github.com/REPO_OWNER/REPO_NAME:$COMMIT_SHA will be used.

Use a build configuration (cloudbuild.yaml) file for building multiple images in a single trigger.
""")


def AddBuildFileConfigArgs(flag_config):
  """Adds additional argparse flags to a group for build configuration options.

  Args:
    flag_config: argparse argument group. Additional flags will be added to this
      group to cover common build configuration settings.

  Returns:
    build_config: a build config.
  """

  build_config = flag_config.add_mutually_exclusive_group(required=True)
  build_file_config = build_config.add_argument_group(
      help='Build file configuration flags')
  build_file_config.add_argument(
      '--build-config',
      metavar='PATH',
      help="""\
Path to a YAML or JSON file containing the build configuration in the repository.

For more details, see: https://cloud.google.com/cloud-build/docs/build-config
""")

  return build_config


def ParseRepoEventArgs(trigger, args):
  """Parses repo event related flags.

  Args:
    trigger: The trigger to populate.
    args: An argparse arguments object.
  """
  if args.included_files:
    trigger.includedFiles = args.included_files
  if args.ignored_files:
    trigger.ignoredFiles = args.ignored_files


def ParseBuildConfigArgs(trigger,
                         args,
                         messages,
                         default_image,
                         need_repo=False):
  """Parses build-config flags.

  Args:
    trigger: The trigger to populate.
    args: An argparse arguments object.
    messages: A Cloud Build messages module.
    default_image: The docker image to use if args.dockerfile_image is empty.
    need_repo: Whether or not a repo needs to be included explicitly in flags.
  """
  if args.build_config:
    trigger.filename = args.build_config
    trigger.substitutions = cloudbuild_util.EncodeTriggerSubstitutions(
        args.substitutions, messages)
  if args.dockerfile:

    if args.substitutions:
      raise c_exceptions.ConflictingArgumentsException(
          'Dockerfile and substitutions',
          'Substitutions are not supported with a Dockerfile configuration.')

    image = args.dockerfile_image or default_image
    trigger.build = messages.Build(steps=[
        messages.BuildStep(
            name='gcr.io/cloud-builders/docker',
            dir=args.dockerfile_dir,
            args=['build', '-t', image, '-f', args.dockerfile, '.'],
        )
    ])
  if args.inline_config:
    trigger.build = cloudbuild_util.LoadMessageFromPath(args.inline_config,
                                                        messages.Build,
                                                        'inline build config')
    trigger.substitutions = cloudbuild_util.EncodeTriggerSubstitutions(
        args.substitutions, messages)

  if need_repo:
    # Repo is required if a build config (filename) or dockerfile was provided.
    required = args.build_config or args.dockerfile
    ParseGitRepoSource(trigger, args, messages, required=required)


def AddBranchPattern(parser):
  parser.add_argument(
      '--branch-pattern',
      metavar='REGEX',
      help="""\
A regular expression specifying which git branches to match.

This pattern is used as a regex search for any incoming pushes.
For example, --branch-pattern=foo will match "foo", "foobar", and "barfoo".
Events on a branch that does not match will be ignored.

The syntax of the regular expressions accepted is the syntax accepted by
RE2 and described at https://github.com/google/re2/wiki/Syntax.
""")


def AddTagPattern(parser):
  parser.add_argument(
      '--tag-pattern',
      metavar='REGEX',
      help="""\
A regular expression specifying which git tags to match.

This pattern is used as a regex search for any incoming pushes.
For example, --tag-pattern=foo will match "foo", "foobar", and "barfoo".
Events on a tag that does not match will be ignored.

The syntax of the regular expressions accepted is the syntax accepted by
RE2 and described at https://github.com/google/re2/wiki/Syntax.
""")


def AddGitRepoSource(flag_config):
  """Adds additional argparse flags to a group for git repo source options.

  Args:
    flag_config: argparse argument group. Git repo source flags will be added to
      this group.
  """
  repo_config = flag_config.add_argument_group(
      help='Flags for repository information')
  repo_config.add_argument(
      '--repo',
      required=True,
      help='URI of the repository. Currently only HTTP URIs for GitHub and Cloud Source Repositories are supported.'
  )

  ref_config = repo_config.add_mutually_exclusive_group(required=True)
  ref_config.add_argument('--branch', help='Branch to build.')
  ref_config.add_argument('--tag', help='Tag to build.')


def ParseGitRepoSource(trigger, args, messages, required=False):
  """Parses git repo source flags.

  Args:
    trigger: The trigger to populate.
    args: An argparse arguments object.
    messages: A Cloud Build messages module.
    required: Whether or not the repository info is required.
  """
  repo_source = messages.GitRepoSource()

  if required:
    if not args.repo:
      raise c_exceptions.RequiredArgumentException(
          'REPO',
          '--repo is required when specifying a --dockerfile or --build-config.'
      )
    if not args.branch and not args.tag:
      raise c_exceptions.RequiredArgumentException(
          'BRANCH or TAG',
          'Either --branch or --tag is required when specifying a --dockerfile or --build-config.'
      )

  repo_source.uri = args.repo
  if args.branch:
    repo_source.ref = 'refs/heads/' + args.branch
  else:
    repo_source.ref = 'refs/tags/' + args.tag

  trigger.sourceToBuild = repo_source
