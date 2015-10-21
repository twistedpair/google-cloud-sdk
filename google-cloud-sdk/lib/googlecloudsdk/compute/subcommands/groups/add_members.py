# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for adding a user to a group."""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import user_utils


class AddMembers(base_classes.NoOutputAsyncMutator,
                 user_utils.UserResourceFetcher):
  """Add a user to a Google Compute Engine group.

  *{command}* adds a users to a Google Compute Engine group.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'names',
        metavar='NAME',
        nargs='+',
        help='The names of the groups to add members to.')

    parser.add_argument(
        '--members',
        metavar='USERNAME',
        required=True,
        type=arg_parsers.ArgList(min_length=1),
        action=arg_parsers.FloatingListValuesCatcher(),
        help='The names or fully-qualified URLs of the users to add.')

  @property
  def service(self):
    return self.clouduseraccounts.groups

  @property
  def method(self):
    return 'AddMember'

  @property
  def resource_type(self):
    return 'groups'

  @property
  def messages(self):
    return self.clouduseraccounts.MESSAGES_MODULE

  def CreateRequests(self, args):

    user_refs = self.CreateAccountsReferences(
        args.members, resource_type='users')

    group_refs = self.CreateAccountsReferences(
        args.names, resource_type='groups')

    user_selflinks = [user_ref.SelfLink() for user_ref in user_refs]
    requests = []
    for group_ref in group_refs:
      new_member = self.messages.GroupsAddMemberRequest(
          users=user_selflinks)

      request = self.messages.ClouduseraccountsGroupsAddMemberRequest(
          project=self.project,
          groupsAddMemberRequest=new_member,
          groupName=group_ref.Name())
      requests.append(request)

    return requests


AddMembers.detailed_help = {
    'EXAMPLES': """\
        To add a user to a group, run:

          $ {command} example-group --members example-user

        To add multiple users to multiple groups, run:

          $ {command} example-group-1 example-group-2 --members example-user-1 example-user-2
        """,
}
