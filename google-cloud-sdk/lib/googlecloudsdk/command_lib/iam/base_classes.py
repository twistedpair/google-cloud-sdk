# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Base classes for abstracting away common logic."""

import abc
import os

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core.util import files


class BaseIamCommand(base.Command):
  """Base class for all iam subcommands."""

  __metaclass__ = abc.ABCMeta

  def __init__(self, *args, **kwargs):
    self.address = None
    self.key_id = None
    self.data_format = None
    super(BaseIamCommand, self).__init__(*args, **kwargs)

  @property
  def iam_client(self):
    """Specifies the iam client."""
    return self.context['iam-client']

  @property
  def resources(self):
    """Specifies the iam resources namespace."""
    return self.context['iam-resources']

  @property
  def messages(self):
    """Specifies the iam messages namespace."""
    return self.context['iam-messages']

  # TODO(b/36051090): b/25212870
  # We don't yet have support for atomic names in gcloud resources. When we
  # do, this is the code we'll need to invoke.
  def ParseServiceAccount(self, email):
    ref = self.resources.REGISTRY.Parse(
        email,
        collection='iam.projects.serviceAccounts',
        params={'project': '-'})
    return ref

  def ReadFile(self, file_name):
    """Reads a file, automatically handling all relevant errors.

    Args:
      file_name: The file to read

    Returns:
      The contents of the file as a string.

    Raises:
      ToolException: An error occurred when trying to read the file.
    """
    if not os.path.exists(file_name):
      raise exceptions.ToolException(
          'The given file could not be found: {0}'.format(file_name))

    try:
      with open(file_name, 'rb') as handle:
        return handle.read()
    except EnvironmentError:
      raise exceptions.ToolException(
          'The given file could not be read: {0}'.format(file_name))

  def WriteFile(self, file_name, contents, make_private=False):
    """Writes a file, automatically handling all relevant errors.

    Args:
      file_name: The file to write
      contents: The data to write into the file
      make_private: If True, set the permission of the file to user
                    read/write only. Otherwise set it as public.
                    Default to False.

    Raises:
      ToolException: An error occurred when trying to write the file.
    """
    try:
      if make_private:
        with files.OpenForWritingPrivate(file_name, binary=True) as handle:
          handle.write(contents)
      else:
        with open(file_name, 'wb') as handle:
          handle.write(contents)
    except EnvironmentError:
      raise exceptions.ToolException(
          'The given file could not be written: {0}'.format(file_name))
