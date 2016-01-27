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
import os.path

from googlecloudsdk.api_lib.iam import utils
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resource_printer
from googlecloudsdk.core.console import console_io


class BaseIamCommand(base.Command):
  """Base class for all iam subcommands."""

  __metaclass__ = abc.ABCMeta

  def __init__(self, *args, **kwargs):
    self.address = None
    self.key_id = None
    self.data_format = None
    super(BaseIamCommand, self).__init__(*args, **kwargs)

  @property
  def http(self):
    """Specifies the http client to be used for requests."""
    return self.context['http']

  @property
  def project(self):
    """Specifies the user's project."""
    return properties.VALUES.core.project

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

  def Display(self, args, resources):
    """Prints the given resources; uses a list printer if Run gave us a list."""
    if not resources:
      return

    if isinstance(resources, list):
      console_io.PrintExtendedList(resources, self.data_format)
    else:
      resource_printer.Print(resources=resources,
                             print_format='yaml',
                             out=log.out)

  def SetAddress(self, address):
    """Sets the IAM address for error handling.

    Args:
      address: An IAM email address.

    Raises:
      ValueError: The given address was not a valid email.
    """
    if not utils.ValidateEmail(address):
      raise ValueError('IAM address must be an email, given [{0}]'.format(
          address))
    self.address = address

  def SetAddressAndKey(self, address, key_id):
    """Sets the IAM address and key for error handling.

    Args:
      address: An IAM email address.
      key_id: A key id.

    Raises:
      ValueError: The given address was not a valid email.
    """
    self.SetAddress(address)
    if not utils.ValidateKeyId(key_id):
      raise ValueError('[{0}] is not a valid key'.format(address))
    self.key_id = key_id

  # TODO(user): b/25212870
  # We don't yet have support for atomic names in gcloud resources. When we
  # do, this is the code we'll need to invoke.
  def ParseServiceAccount(self, email):
    ref = self.resources.Parse(
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
      ValueError: An error occurred when trying to read the file.
    """
    if not os.path.exists(file_name):
      raise ValueError('The given file could not be found: {0}'.format(
          file_name))

    try:
      with open(file_name, 'rb') as handle:
        return handle.read()
    except EnvironmentError:
      raise ValueError('The given file could not be read: {0}'.format(
          file_name))

  def WriteFile(self, file_name, contents):
    """Writes a file, automatically handling all relevant errors.

    Args:
      file_name: The file to write
      contents: The data to write into the file

    Raises:
      ValueError: An error occurred when trying to write the file.
    """
    try:
      with open(file_name, 'wb') as handle:
        handle.write(contents)
    except EnvironmentError:
      raise ValueError('The given file could not be written: {0}'.format(
          file_name))
