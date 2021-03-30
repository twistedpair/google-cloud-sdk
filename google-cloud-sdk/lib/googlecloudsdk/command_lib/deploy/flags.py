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

from googlecloudsdk.calliope import arg_parsers

_SOURCE_HELP_TEXT = """
The location of the source that contains skaffold.yaml. The location can be a directory on a local disk or a gzipped archive file (.tar.gz) in Google Cloud Storage.
 If the source is a local directory, this command skips the files specified in the --ignore-file. If --ignore-file is not specified, use.gcloudignore file. If a .gcloudignore file is absent and a .gitignore file is present in the local source directory, gcloud will use a generated Git-compatible .gcloudignore file that respects your .gitignored files.
 The global .gitignore is not respected. For more information on .gcloudignore, see gcloud topic gcloudignore.
"""


def AddGcsSourceStagingDirFlag(parser, hidden=False):
  """Add a Google Cloud Storage directory flag for staging the build."""
  parser.add_argument(
      '--gcs-source-staging-dir',
      hidden=hidden,
      help='A directory in Google Cloud Storage to copy the source used for '
      'staging the build. If the specified bucket does not exist, Cloud '
      'Build will create one. If you don\'t set this field, '
      '```gs://[PROJECT_ID]_cloudbuild/source``` is used.')


def AddIgnoreFileFlag(parser, hidden=False):
  """Add an ignore file flag."""
  parser.add_argument(
      '--ignore-file',
      hidden=hidden,
      help='Override the `.gcloudignore` file and use the specified file '
      'instead.')


def AddToTargetFlag(parser, hidden=False):
  """Add to-target flag."""
  parser.add_argument(
      '--to-target',
      hidden=hidden,
      help='Specifies a target to deliver into upon release creation')


def AddGcsRenderDirFlag(parser, hidden=False):
  """Add gcs-render-dir flag."""
  parser.add_argument(
      '--gcs-render-dir',
      hidden=hidden,
      help='Specifies the Google Cloud Storage location'
      ' to store the rendered files')


def AddImagesGroup(parser, hidden=False):
  """Add Images flag."""
  images_group = parser.add_mutually_exclusive_group()
  images_group.add_argument(
      '--images',
      metavar='NAME=TAG',
      type=arg_parsers.ArgDict(),
      hidden=hidden,
      help="""\
Reference to a collection of individual image name to image full path replacements.

For example:

    $ gcloud deploy releases create foo \\
        --images image1=path/to/image1:v1@sha256:45db24
      """)
  images_group.add_argument(
      '--build-artifacts',
      hidden=hidden,
      help='Reference to a Skaffold build artifacts output file')


def AddSourceFlag(parser, hidden=False):
  """Add source flag."""
  parser.add_argument(
      '--source',
      hidden=hidden,
      default='.',  # By default, the current directory is used.
      help=_SOURCE_HELP_TEXT,
  )


def AddConfigFile(parser, hidden=False):
  """Add config flag."""
  parser.add_argument(
      '--file',
      hidden=hidden,
      required=True,
      help='Path to yaml file containing Deliver Pipeline(s), Target(s) declarative definitions.',
  )
