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
"""Flags for the deploy command group."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import textwrap

from googlecloudsdk.calliope import arg_parsers

_SOURCE_HELP_TEXT = """
The location of the source that contains skaffold.yaml. The location can be a directory on a local disk or a gzipped archive file (.tar.gz) in Google Cloud Storage.
 If the source is a local directory, this command skips the files specified in the --ignore-file. If --ignore-file is not specified, use.gcloudignore file. If a .gcloudignore file is absent and a .gitignore file is present in the local source directory, gcloud will use a generated Git-compatible .gcloudignore file that respects your .gitignored files.
 The global .gitignore is not respected. For more information on .gcloudignore, see gcloud topic gcloudignore.
"""


def AddGcsSourceStagingDirFlag(parser, hidden=False):
  """Adds a Google Cloud Storage directory flag for staging the build."""
  parser.add_argument(
      '--gcs-source-staging-dir',
      hidden=hidden,
      help='A directory in Google Cloud Storage to copy the source used for '
      'staging the build. If the specified bucket does not exist, Cloud '
      'Deploy will create one. If you don\'t set this field, '
      '```gs://[PROJECT_ID]_clouddeploy/source``` is used.')


def AddIgnoreFileFlag(parser, hidden=False):
  """Adds an ignore file flag."""
  parser.add_argument(
      '--ignore-file',
      hidden=hidden,
      help='Override the `.gcloudignore` file and use the specified file '
      'instead.')


def AddToTargetFlag(parser, hidden=False):
  """Adds to-target flag."""
  parser.add_argument(
      '--to-target',
      hidden=hidden,
      help='Specifies a target to deliver into upon release creation')


def AddImagesGroup(parser, hidden=False):
  """Adds Images flag."""
  images_group = parser.add_mutually_exclusive_group()
  images_group.add_argument(
      '--images',
      metavar='NAME=TAG',
      type=arg_parsers.ArgDict(),
      hidden=hidden,
      help=textwrap.dedent("""\
      Reference to a collection of individual image name to image full path replacements.

      For example:

          $ gcloud deploy releases create foo \\
              --images image1=path/to/image1:v1@sha256:45db24
      """))
  images_group.add_argument(
      '--build-artifacts',
      hidden=hidden,
      help='Reference to a Skaffold build artifacts output file from skaffold build --file-output=BUILD_ARTIFACTS. If you aren\'t using Skaffold, use the --images flag below to specify the image-names-to-tagged-image references.'
  )


def AddSourceFlag(parser, hidden=False):
  """Adds source flag."""
  parser.add_argument(
      '--source',
      hidden=hidden,
      default='.',  # By default, the current directory is used.
      help=_SOURCE_HELP_TEXT,
  )


def AddConfigFile(parser, hidden=False):
  """Adds config flag."""
  parser.add_argument(
      '--file',
      hidden=hidden,
      required=True,
      help='Path to yaml file containing Delivery Pipeline(s), Target(s) declarative definitions.',
  )


def AddToTarget(parser, hidden=False):
  """Adds to-target flag."""
  parser.add_argument(
      '--to-target', hidden=hidden, help='Destination target to promote into.')


def AddRolloutID(parser, hidden=False):
  """Adds rollout-id flag."""
  parser.add_argument(
      '--rollout-id',
      hidden=hidden,
      help='ID to assign to the generated rollout for promotion.')


def AddRelease(parser, help_text, hidden=False):
  """Adds release flag."""
  parser.add_argument('--release', hidden=hidden, help=help_text)


def AddForce(parser, help_text, hidden=False):
  """Adds force flag."""
  parser.add_argument(
      '--force',
      hidden=hidden,
      action='store_true',
      help=help_text,
  )


def AddDescription(parser, help_text, name='--description'):
  """Adds description related flag."""
  parser.add_argument(
      name,
      help=help_text,
  )


def AddDeliveryPipeline(parser, required=True):
  """Adds delivery pipeline flag."""
  parser.add_argument(
      '--delivery-pipeline',
      help='The name of the Cloud Deploy delivery pipeline',
      required=required)


def AddAnnotationsFlag(parser, resource_type):
  """Adds --annotations flag."""
  help_text = textwrap.dedent("""\
  Annotations to apply to the %s. Annotations take the form of key/value string pairs.

  Examples:

  Add annotations:

    $ {command} --annotations="from_target=test,status=stable"

  """) % (
      resource_type)

  parser.add_argument(
      '--annotations',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      help=help_text)


def AddLabelsFlag(parser, resource_type):
  """Add --labels flag."""
  help_text = textwrap.dedent("""\
  Labels to apply to the %s. Labels take the form of key/value string pairs.

  Examples:

  Add labels:

    $ {command} --labels="commit=abc123,author=foo"

""") % (
    resource_type)

  parser.add_argument(
      '--labels',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      help=help_text)


def AddSkaffoldVersion(parser):
  """Adds skaffold version flag."""
  parser.add_argument(
      '--skaffold-version', help='Version of the Skaffold binary.')


def AddSkaffoldFileFlag(parser):
  """Add --skaffold-file flag."""
  help_text = textwrap.dedent("""\
  Path of the skaffold file relative to the source directory.

  Examples:

  Use Skaffold file:


    $ {command} --source=/home/user/source --skaffold-file=config/skaffold.yaml

    The skaffold file absolute file path is expected to be:
    /home/user/source/config/skaffold.yaml

""")

  parser.add_argument(
      '--skaffold-file',
      help=help_text)


def AddDescriptionFlag(parser):
  """Add --description flag."""
  parser.add_argument(
      '--description',
      help='Description of rollout created during a rollback.',
      hidden=False,
      default=None,
      required=False)


def AddListAllPipelines(parser):
  """Add --list-all-pipelines flag."""
  help_text = textwrap.dedent("""\
  List all Delivery Pipelines associated with a target.

  Usage:

    $ {command} --list-all-pipelines

""")

  parser.add_argument(
      '--list-all-pipelines', action='store_true', default=None, help=help_text)


def AddSkipPipelineLookup(parser):
  """Add --skip-pipeline-lookup flag."""
  help_text = textwrap.dedent("""\
  If set, skip fetching details of associated pipelines when describing a target.

  Usage:

    $ {command} --skip-pipeline-lookup

""")

  parser.add_argument(
      '--skip-pipeline-lookup',
      action='store_true',
      default=False,
      help=help_text)
