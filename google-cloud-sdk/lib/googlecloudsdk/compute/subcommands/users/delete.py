# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for deleting users."""
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import lister
from googlecloudsdk.shared.compute import request_helper
from googlecloudsdk.shared.compute import user_utils
from googlecloudsdk.shared.compute import utils


class Delete(base_classes.BaseAsyncMutator):
  """Delete Google Compute Engine users."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--owners',
        action='store_true',
        help=('The owner of the user to be created. The owner must be an email '
              'address associated with a Google account'))

    parser.add_argument(
        'names',
        metavar='NAME',
        nargs='+',
        help='The names of the users to delete.')

  @property
  def service(self):
    return self.clouduseraccounts.users

  @property
  def method(self):
    return 'Delete'

  @property
  def resource_type(self):
    return 'users'

  @property
  def messages(self):
    return self.clouduseraccounts.MESSAGES_MODULE

  def GetOwnerAccounts(self, owners):
    """Look up all users on the current project owned by the list of owners."""
    requests = []
    for owner in owners:
      requests += lister.FormatListRequests(self.service, self.project,
                                            None, None,
                                            'owner eq ' + owner)
    errors = []
    responses = request_helper.MakeRequests(
        requests=requests,
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None)

    if errors:
      utils.RaiseException(errors, user_utils.UserException, error_message=(
          'Could not get users for owners:'))
    return [response.name for response in responses]

  def CreateRequests(self, args):

    if args.owners:
      names = self.GetOwnerAccounts(args.names)
    else:
      names = args.names

    user_refs = self.CreateAccountsReferences(
        names, resource_type='users')
    utils.PromptForDeletion(user_refs)

    requests = []
    for user_ref in user_refs:
      request = self.messages.ClouduseraccountsUsersDeleteRequest(
          project=self.project,
          user=user_ref.Name())
      requests.append(request)
    return requests

Delete.detailed_help = {
    'brief': 'Delete Google Compute Engine users',
    'DESCRIPTION': """\
        *{command}* deletes one or more Google Compute Engine users.
        """,
    'EXAMPLES': """\
        To delete one or more users by name, run:

          $ {command} example-user-1 example-user-2

        To delete all users for one or more owners, run:

          $ {command} example-owner-1@gmail.com example-owner-2@gmail.com --owners
        """,
}
