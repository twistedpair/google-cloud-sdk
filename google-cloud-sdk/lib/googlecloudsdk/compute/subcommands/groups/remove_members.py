# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for removing a user from a group."""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import user_utils


class RemoveMembers(base_classes.NoOutputAsyncMutator,
                    user_utils.UserResourceFetcher):
  """Remove a user from a Google Compute Engine group.

  *{command}* removes a user from a Google Compute Engine group.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'names',
        metavar='NAME',
        type=arg_parsers.ArgList(min_length=1),
        action=arg_parsers.FloatingListValuesCatcher(),
        help='The names of the groups to remove members from.')

    parser.add_argument(
        '--members',
        metavar='USERNAME',
        required=True,
        type=arg_parsers.ArgList(min_length=1),
        action=arg_parsers.FloatingListValuesCatcher(),
        help='The names or fully-qualified URLs of the users to remove.')

  @property
  def service(self):
    return self.clouduseraccounts.groups

  @property
  def method(self):
    return 'RemoveMember'

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

    requests = []
    for group_ref in group_refs:
      for user_ref in user_refs:
        remove_member = self.messages.GroupsRemoveMemberRequest(
            users=[user_ref.SelfLink()])

        request = self.messages.ClouduseraccountsGroupsRemoveMemberRequest(
            project=self.project,
            groupsRemoveMemberRequest=remove_member,
            groupName=group_ref.Name())
        requests.append(request)

    return requests

RemoveMembers.detailed_help = {
    'EXAMPLES': """\
        To remove a user from a group, run:

          $ {command} example-group --members example-user

        To remove multiple users from multiple groups with
        one command, run

          $ {command} example-group-1 example-group-2 \\
              --members example-user-1 example-user-2
        """,
}
