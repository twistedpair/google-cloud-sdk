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
"""Utils for GKE Hub commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64
import textwrap

from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.core.util import files


def AddCommonArgs(parser):
  """Adds the flags shared between 'hub' subcommands to parser.

  Args:
    parser: an argparse.ArgumentParser, to which the common flags will be added
  """
  parser.add_argument(
      '--kubeconfig',
      type=str,
      help=textwrap.dedent("""\
          The kubeconfig file containing an entry for the cluster. Defaults to
          $KUBECONFIG if it is set in the environment, otherwise defaults to
          to $HOME/.kube/config.
        """),
  )

  parser.add_argument(
      '--context',
      type=str,
      help=textwrap.dedent("""\
        The context in the kubeconfig file that specifies the cluster.
      """),
  )


def UserAccessibleProjectIDSet():
  """Retrieve the project IDs of projects the user can access.

  Returns:
    set of project IDs.
  """
  return set(p.projectId for p in projects_api.List())


def Base64EncodedFileContents(filename):
  """Reads the provided file, and returns its contents, base64-encoded.

  Args:
    filename: The path to the file, absolute or relative to the current working
      directory.

  Returns:
    A string, the contents of filename, base64-encoded.

  Raises:
   files.Error: if the file cannot be read.
  """
  return base64.b64encode(
      files.ReadBinaryFileContents(files.ExpandHomeDir(filename)))


def ReleaseTrackCommandPrefix(release_track):
  """Returns a prefix to add to a gcloud command.

  This is meant for formatting an example string, such as:
    gcloud {}container hub register-cluster

  Args:
    release_track: A ReleaseTrack

  Returns:
   a prefix to add to a gcloud based on the release track
  """

  prefix = release_track.prefix
  return prefix + ' ' if prefix else ''
