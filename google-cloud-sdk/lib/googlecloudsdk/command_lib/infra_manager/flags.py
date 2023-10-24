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
"""Flags and helpers for the config-manager command group."""

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

  $ {command} projects/p1/location/us-central1/deployments/my-deployment --gcs-source="gs://my-bucket" --labels="env=prod,team=finance"

Clear labels for an existing deployment:

  $ {command} projects/p1/location/us-central1/deployments/my-deployment --gcs-source="gs://my-bucket" --labels=""

Add a label to an existing deployment:

  First, fetch the current labels using the `describe` command, then follow the
  preceding example for updating labels.
"""

  parser.add_argument(
      '--labels',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      help=help_text,
  )


def AddAsyncFlag(parser):
  """Add --async flag."""
  base.ASYNC_FLAG.AddToParser(parser)


def AddTerraformBlueprintFlag(parser):
  """Add TerraformBlueprint related flags."""

  input_values_help_text = """\
Input variable values for the Terraform blueprint. It only
      accepts (key, value) pairs where value is a scalar value.

Examples:

Pass input values on command line:

  $ {command} projects/p1/location/us-central1/deployments/my-deployment --gcs-source="gs://my-bucket" --input-values=projects=p1,region=r
"""

  inputs_file_help_text = """\
A .tfvars file containing terraform variable values. --inputs-file flag is supported for python version 3.6 and above.

Examples:

Pass input values on the command line:

  $ {command} projects/p1/location/us-central1/deployments/my-deployment --gcs-source="gs://my-bucket" --inputs-file=path-to-tfvar-file.tfvar
"""

  gcs_source_help_text = """\
URI of an object in Google Cloud Storage.
      e.g. `gs://{bucket}/{object}`

Examples:

Create a deployment from a storage my-bucket:

  $ {command} projects/p1/location/us-central1/deployments/my-deployment --gcs-source="gs://my-bucket"
"""

  git_source_repo_help = """\
Repository URL.
Example: 'https://github.com/examples/repository.git'

Use in conjunction with `--git-source-directory` and `--git-source_ref`

Examples:

Create a deployment from the "https://github.com/examples/repository.git" repo, "staging/compute" folder, "mainline" branch:

  $ {command} projects/p1/location/us-central1/deployments/my-deployment --git-source-repo="https://github.com/examples/repository.git"
    --git-source-directory="staging/compute" --git-source-ref="mainline"
"""

  git_source_directory_help = """\
Subdirectory inside the repository.
Example: 'staging/my-package'

Use in conjunction with `--git-source-repo` and `--git-source-ref`

Examples:

Create a deployment from the "https://github.com/examples/repository.git" repo, "staging/compute" folder, "mainline" branch:

  $ {command} projects/p1/location/us-central1/deployments/my-deployment --git-source-repo="https://github.com/examples/repository.git"
    --git-source-directory="staging/compute" --git-source-ref="mainline"
"""

  git_source_ref_help = """\
Subdirectory inside the repository.
Example: 'staging/my-package'

Use in conjunction with `--git-source-repo` and `--git-source-directory`

Examples:

Create a deployment from the "https://github.com/examples/repository.git" repo, "staging/compute" folder, "mainline" branch:

  $ {command} projects/p1/location/us-central1/deployments/my-deployment --git-source-repo="https://github.com/examples/repository.git"
    --git-source-directory="staging/compute" --git-source-ref="mainline"
"""

  local_source_help = """\
Local storage path where config files are stored.
      e.g. `./path/to/blueprint`

Examples:

Create a deployment from a local storage path `./path/to/blueprint`:

  $ {command} projects/p1/location/us-central1/deployments/my-deployment --local-source="./path/to/blueprint"
"""

  stage_bucket_help = """\
Use in conjunction with `--local-source` to specify a destination storage bucket for
uploading local files.

If unspecified, the bucket defaults to `gs://PROJECT_NAME_blueprints`. Uploaded
content will appear in the `source` object under a name comprised of the
timestamp and a UUID. The final output destination looks like this:
`gs://_BUCKET_/source/1615850562.234312-044e784992744951b0cd71c0b011edce/`

Examples:

Create a deployment from a local storage path `./path/to/blueprint` and stage-bucket `gs://my-bucket`:

  $ {command} projects/p1/location/us-central1/deployments/my-deployment --local-source="./path/to/blueprint" --stage-bucket="gs://my-bucket"
"""

  source_group = parser.add_group(mutex=False)

  input_values = source_group.add_mutually_exclusive_group()
  input_values.add_argument(
      '--input-values',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      help=input_values_help_text,
  )

  input_values.add_argument(
      '--inputs-file',
      help=inputs_file_help_text,
  )

  source_details = source_group.add_mutually_exclusive_group()

  source_details.add_argument(
      '--gcs-source',
      help=gcs_source_help_text,
  )

  git_source_group = source_details.add_group(mutex=False)

  git_source_group.add_argument(
      '--git-source-repo',
      help=git_source_repo_help,
  )

  git_source_group.add_argument(
      '--git-source-directory',
      help=git_source_directory_help,
  )

  git_source_group.add_argument(
      '--git-source-ref',
      help=git_source_ref_help,
  )

  local_source_group = source_details.add_group(mutex=False)

  local_source_group.add_argument(
      '--local-source',
      help=local_source_help,
  )

  local_source_group.add_argument(
      '--ignore-file',
      help=(
          'Override the `.gcloudignore` file and use the specified file '
          'instead. See `gcloud topic gcloudignore` for more information.'
      ),
  )

  # Note: we cannot specify a default here since the default value we would WANT
  # to use is dynamic; it includes the project ID.
  local_source_group.add_argument(
      '--stage-bucket',
      help=stage_bucket_help,
      hidden=True,
      # This will ensure that "--stage-bucket" takes on the form
      # "gs://my-bucket/".
      type=functions_api_util.ValidateAndStandarizeBucketUriOrRaise,
  )


def AddServiceAccountFlag(parser, hidden=False):
  """Add --service-account flag."""
  parser.add_argument(
      '--service-account',
      hidden=hidden,
      help=(
          'User-specified Service Account (SA) to be used as credential to'
          ' manage resources. Format:'
          ' `projects/{projectID}/serviceAccounts/{serviceAccount}`'
      ),
  )


def AddImportExistingResourcesFlag(parser, hidden=False):
  """Add --import-existing-resources flag."""
  parser.add_argument(
      '--import-existing-resources',
      hidden=hidden,
      action='store_true',
      help=(
          'By default, Infrastructure Manager will return a failure when'
          ' Terraform encounters a 409 code (resource conflict error) during'
          ' actuation. If this flag is set to true, Infrastructure Manager will'
          ' instead attempt to automatically import the resource into the'
          ' Terraform state (for supported resource types) and continue'
          ' actuation.'
      ),
  )


def AddWorkerPoolFlag(parser, hidden=False):
  """Add --worker-pool flag."""
  parser.add_argument(
      '--worker-pool',
      hidden=hidden,
      help=(
          'User-specified Worker Pool resource in which the Cloud Build job'
          'will execute. Format: '
          'projects/{project}/locations/{location}/workerPools/{workerPoolId}'
      ),
  )


def AddArtifactsGCSBucketFlag(parser, hidden=False):
  """Add --artifacts-gcs-bucket flag."""
  parser.add_argument(
      '--artifacts-gcs-bucket',
      hidden=hidden,
      help=(
          'user-defined location of Cloud Build logs, artifacts, and Terraform'
          ' state files in Google Cloud Storage. Format:'
          ' `gs://{bucket}/{folder}` A default bucket will be bootstrapped if'
          ' the field is not set or empty'
      ),
  )


def AddDraftFlag(parser, hidden=False):
  """Add --draft flag."""
  parser.add_argument(
      '--draft',
      hidden=hidden,
      help=(
          'If this flag is set to true, the exported deployment state file will'
          ' be the draft state'
      ),
      action='store_true',
  )


def AddLockFlag(parser, hidden=False):
  """Add --lock-id flag."""
  parser.add_argument(
      '--lock-id',
      required=True,
      hidden=hidden,
      help='Lock ID of the lock file to verify person importing owns lock.',
  )
