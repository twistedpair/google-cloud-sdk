# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the blueprints command group."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.functions.v1 import util as functions_api_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


def AddLabelsFlag(parser):
  """Add --labels flag."""

  help_text = """\
Labels to apply to the deployment. Existing values are overwritten. To retain
the existing labels on a deployment, do not specify this flag.

Examples:

Update labels for an existing deployment:

  $ {command} --source="./blueprint" --labels="env=prod,team=finance" existing-deployment

Clear labels for an existing deployment:

  $ {command} --source="./blueprint" --labels="" existing-deployment

Add a label to an existing deployment:

  First, fetch the current labels using the `describe` command, then follow the
  preceding example for updating labels.
"""

  parser.add_argument(
      '--labels',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      help=help_text)


def AddAsyncFlag(parser):
  """Add --async flag."""
  base.ASYNC_FLAG.AddToParser(parser)


def AddSourceFlag(parser):
  """Add --source and related flags."""

  source_help_text = """\
Source of a blueprint. It can represent one of three locations:

- Local filesystem
- Google Cloud Storage bucket
- Git repository

Local files are uploaded to the storage bucket specified by `--stage-bucket`;
see that flag for more information.

When uploading local files, matches in the `.gcloudignore` file are skipped. For
more information, see `gcloud topic gcloudignore`. By default, `.git` and
`.gitignore` are ignored, meaning they are be uploaded with your blueprint.

Git repositories can either be a Cloud Source Repositories (CSR) repository (in
which case you must have permission to access it) or a public Git repository
(e.g. on GitHub). Each takes the form `_URL_@_REF_`:
  * Example CSR `_URL_`: https://source.cloud.google.com/p/my-project/r/my-csr-repository
  * Example GitHub `_URL_`: https://github.com/google/repository
  * `@` is a literal `@` character. `_REF_` is a commit hash, branch, or tag.

For CSR repositories in the same project as the deployment, no extra permissions
need to be granted. For CSR repositories in separate projects, the 'Cloud Build'
service account must hold the `source.repos.get` permission. The role
`roles/source.reader` contains this permission. Here is an example of how to add
the role to project `project-with-csr-repository` for a project whose project
number is `1234`:

  $ gcloud projects add-iam-policy-binding project-with-csr-repository --member=serviceAccount:1234@cloudbuild.gserviceaccount.com --role=roles/source.reader

See `source-git-subdir` for how to specify a subdirectory within a Git
repository.

`--source` is interpreted as a storage bucket if it begins with `gs://`. It is
interpreted as a Git repository if it begins with `https://` (`http://` is not
allowed). If neither case is met, it is treated as a local path.

Examples:

Create a deployment from local files:

  $ {command} [...] new-deployment --source="./path/to/blueprint"

Create a deployment from a storage bucket:

  $ {command} [...] new-deployment --source="gs://my-bucket"

Update a deployment to use a GitHub repository:

  $ {command} [...] existing-deployment --source="https://github.com/google/repository@mainline"
"""

  stage_bucket_help_text = """\
Use in conjunction with `--source` to specify a destination storage bucket for
uploading local files.

If unspecified, the bucket defaults to `gs://PROJECT_NAME_blueprints`. Uploaded
content will appear in the `source` object under a name comprised of the
timestamp and a UUID. The final output destination looks like this:
`gs://_BUCKET_/source/1615850562.234312-044e784992744951b0cd71c0b011edce/`

Examples:

Create a deployment from local files and specify the staging bucket:

  $ {command} [...] new-deployment --source="./path/to/blueprint" --stage-bucket="gs://my-bucket"
"""

  source_git_subdir_help = """\
Use in conjunction with `--source` to specify which subdirectory to pull
blueprint contents from

This defaults to `./`, meaning the root of the specified given repository is
used.

Examples:

Create a deployment from the "blueprints/compute" folder:

  $ {command} [...] existing-deployment --source="https://github.com/google/repository"
    --source-git-subdir="blueprints/compute"
"""

  parser.add_argument('--source', required=True, help=source_help_text)

  # If the "--source" flag represents a local directory, then "--stage-bucket"
  # can be specified. However, if it represents a Git repository, then
  # "--source-git-subdir" can be specified. Only one such argument should be
  # provided at a time.
  source_details = parser.add_mutually_exclusive_group()

  # Note: we cannot specify a default here since the default value we would WANT
  # to use is dynamic; it includes the project ID.
  source_details.add_argument(
      '--stage-bucket',
      help=stage_bucket_help_text,

      # This will ensure that "--stage-bucket" takes on the form
      # "gs://my-bucket/".
      type=functions_api_util.ValidateAndStandarizeBucketUriOrRaise,
  )

  source_details.add_argument(
      '--source-git-subdir',
      help=source_git_subdir_help,
  )


# TODO(b/202192430): Consider consolidating this with --config-controller into
# a single --target flag.
def AddGitTargetFlag(parser, hidden=True):
  """Add --target-git and --target-git-subdir flags."""
  target_git_subdir_help = """\
Use in conjunction with `--target-git` to specify which subdirectory to push
blueprint contents to.

This defaults to `./`, meaning the root of the specified repository is used.

Examples:

Push blueprint artifacts to the "blueprints/compute" folder:

  $ {command} [...] my-deployment --target-git="https://source.cloud.google.com/p/my-project/r/my-csr-repository"
    --target-git-subdir="blueprints/compute"
"""

  target_git_help_text = """\
The Git repository to which a blueprint will be uploaded after the pipeline
is run.

The Git repository must be a Cloud Source Repositories (CSR)
repository:
  * Example CSR `_URL_`: https://source.cloud.google.com/p/my-project/r/my-csr-repository

The 'Cloud Build' service account must hold the `source.repos.update`
permission. The role `roles/source.writer` contains this permission. Here is an
example of how to add the role to project `project-with-csr-repository` for a
project whose project number is `1234`:

  $ gcloud projects add-iam-policy-binding project-with-csr-repository --member=serviceAccount:1234@cloudbuild.gserviceaccount.com --role=roles/source.writer

See `target-git-subdir` for how to specify a subdirectory within a Git
repository.

Examples:

Create a deployment to use a CSR repository:

  $ {command} [...] new-deployment --target-git="https://source.cloud.google.com/p/my-project/r/my-csr-repository"
"""
  target_details = parser.add_group(hidden=hidden)
  target_details.add_argument(
      '--target-git',
      help=target_git_help_text,
  )
  target_details.add_argument(
      '--target-git-subdir',
      help=target_git_subdir_help,
  )


def AddIgnoreFileFlag(parser, hidden=False):
  """Add --ignore-file flag."""
  parser.add_argument(
      '--ignore-file',
      hidden=hidden,
      help='Override the `.gcloudignore` file and use the specified file '
      'instead. See `gcloud topic gcloudignore` for more information.')


def AddTimeoutFlag(parser):
  """Adds --reconcile-timeout flag."""

  help_text = ('Set a reconcile timeout for the deployment. If the resources '
               'fail to reconcile within the timeout, the deployment will fail.'
               '\n\n'
               'If unspecified, a timeout of 5 minutes will be used. If '
               'specified as 0, the deployment will not timeout waiting to '
               'reconcile resources.'
               '\n\n'
               'See $ gcloud topic datetimes for information about absolute '
               'duration formats.')

  parser.add_argument(
      '--reconcile-timeout',
      type=arg_parsers.Duration(default_unit='s', parsed_unit='s'),
      default=5*60,
      help=help_text)


def AddPreviewFlags(parser):
  """Add preview flags."""
  preview_details = parser.add_mutually_exclusive_group(required=True)
  preview_details.add_argument(
      '--delete',
      default=False,
      action='store_true',
      help='Whether or not to preview deployment delete operation')
  # TODO(b/200083256): Refactor these flags to reuse the same help text as
  # deployment commands.
  source_group = preview_details.add_group()
  source_group.add_argument(
      '--source', required=True, help='Source of a blueprint')
  source_details = source_group.add_mutually_exclusive_group()
  source_details.add_argument(
      '--stage-bucket',
      help='Destination storage bucket',
      type=functions_api_util.ValidateAndStandarizeBucketUriOrRaise,
  )
  source_details.add_argument(
      '--source-git-subdir',
      help='Subdirectory for blueprints contents',
  )


def AddPreviewFormatFlag(parser):
  """Add --preview-format flag."""
  parser.add_argument(
      '--preview-format',
      choices=['text', 'json'],
      default='text',
      help='Preview results output format')


def AddClusterlessFlag(parser):
  """Adds --clusterless flag."""
  parser.add_argument(
      '--clusterless',
      default=True,
      action='store_true',
      help='Whether or not to use clusterless actuation',
  )
