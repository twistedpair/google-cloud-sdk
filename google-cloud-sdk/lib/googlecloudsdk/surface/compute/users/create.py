# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for creating users."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import gaia_utils
from googlecloudsdk.api_lib.compute import user_utils


class Create(base_classes.BaseAsyncCreator):
  """Create Google Compute Engine users."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--owner',
        help=('The owner of the user to be created. The owner must be an email '
              'address associated with a Google account'))

    parser.add_argument(
        '--description',
        help='An optional, textual description for the user being created.')

    user_utils.AddUserArgument(parser, 'create')

  @property
  def service(self):
    return self.clouduseraccounts.users

  @property
  def method(self):
    return 'Insert'

  @property
  def resource_type(self):
    return 'users'

  @property
  def messages(self):
    return self.clouduseraccounts.MESSAGES_MODULE

  def CreateRequests(self, args):
    """Returns a list of requests necessary for adding users."""

    owner = args.owner
    if not owner:
      owner = gaia_utils.GetAuthenticatedGaiaEmail(self.http)

    name = args.name
    if not name:
      name = gaia_utils.MapGaiaEmailToDefaultAccountName(owner)

    user_ref = self.CreateAccountsReference(
        name, resource_type='users')

    user = self.messages.User(
        name=user_ref.Name(),
        description=args.description,
        owner=owner,
    )

    request = self.messages.ClouduseraccountsUsersInsertRequest(
        project=self.project,
        user=user)
    return [request]


Create.detailed_help = {
    'brief': 'Create Google Compute Engine users',
    'DESCRIPTION': """\
        *{command}* creates a Google Compute Engine user.
        """,
    'EXAMPLES': """\
        To create a user with the specified name and owner, run:

          $ {command} example-user --owner example-owner@google.com

        To create a user with the currently authenticated Google account as
        owner and a default username mapped from that account's email, run:

          $ {command}

        To create a user with the specified name and the currently
        authenticated Google account as owner, run:

          $ {command} example-user

        To create a user with the specified owner and a default username
        mapped from the owner email, run:

          $ {command} --owner example-owner@google.com

        """,
}
