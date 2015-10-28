# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for deleting groups."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import utils


class Delete(base_classes.BaseAsyncMutator):
  """Delete Google Compute Engine groups."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'names',
        metavar='NAME',
        nargs='+',
        help='The names of the groups to delete.')

  @property
  def service(self):
    return self.clouduseraccounts.groups

  @property
  def method(self):
    return 'Delete'

  @property
  def resource_type(self):
    return 'groups'

  @property
  def messages(self):
    return self.clouduseraccounts.MESSAGES_MODULE

  def CreateRequests(self, args):

    group_refs = self.CreateAccountsReferences(
        args.names, resource_type='groups')
    utils.PromptForDeletion(group_refs)

    requests = []
    for group_ref in group_refs:
      request = self.messages.ClouduseraccountsGroupsDeleteRequest(
          project=self.project,
          groupName=group_ref.Name())
      requests.append(request)

    return requests

Delete.detailed_help = {
    'brief': 'Delete Google Compute Engine groups',
    'DESCRIPTION': """\
        *{command}* deletes one or more Google Compute Engine groups.
        """,
    'EXAMPLES': """\
        To delete a group, run:

          $ {command} example-group

        To delete multiple groups, run:

          $ {command} example-group-1 example-group-2
        """,
}
