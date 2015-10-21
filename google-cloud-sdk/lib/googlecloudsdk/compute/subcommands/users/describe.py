# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for describing users."""
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import gaia_utils
from googlecloudsdk.shared.compute import user_utils


class Describe(base_classes.BaseAsyncMutator):
  """Describe a Google Compute Engine user.

  *{command}* displays all data associated with a Google Compute
  Engine user in a project.
  """

  @staticmethod
  def Args(parser):
    user_utils.AddUserArgument(parser, 'describe')

  @property
  def service(self):
    return self.clouduseraccounts.users

  @property
  def method(self):
    return 'Get'

  @property
  def resource_type(self):
    return 'users'

  @property
  def messages(self):
    return self.clouduseraccounts.MESSAGES_MODULE

  def CreateRequests(self, args):
    """Returns a list of requests necessary for describing users."""

    user = args.name
    if not user:
      user = gaia_utils.GetDefaultAccountName(self.http)

    user_ref = self.CreateAccountsReference(
        user, resource_type='users')

    request = self.messages.ClouduseraccountsUsersGetRequest(
        project=self.project,
        user=user_ref.Name())

    return [request]


Describe.detailed_help = {
    'EXAMPLES': """\
        To describe a user, run:

          $ {command} example-user

        To describe the default user mapped from the currently authenticated
        Google account email, run:

          $ {command}
        """,
}
