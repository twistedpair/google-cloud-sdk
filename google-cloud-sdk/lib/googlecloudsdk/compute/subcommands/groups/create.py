# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for creating groups."""
from googlecloudsdk.api_lib.compute import base_classes


class Create(base_classes.BaseAsyncCreator):
  """Create Google Compute Engine groups."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'names',
        metavar='NAME',
        nargs='+',
        help='The name of the group to create.')

    parser.add_argument(
        '--description',
        help='An optional, textual description for the group being created.')

  @property
  def service(self):
    return self.clouduseraccounts.groups

  @property
  def method(self):
    return 'Insert'

  @property
  def resource_type(self):
    return 'groups'

  @property
  def messages(self):
    return self.clouduseraccounts.MESSAGES_MODULE

  def CreateRequests(self, args):
    """Returns a list of requests necessary for adding users."""

    requests = []
    group_refs = self.CreateAccountsReferences(
        args.names, resource_type='groups')
    for group_ref in group_refs:

      group = self.messages.Group(
          name=group_ref.Name(),
          description=args.description,
      )

      request = self.messages.ClouduseraccountsGroupsInsertRequest(
          project=self.project,
          group=group)
      requests.append(request)

    return requests


Create.detailed_help = {
    'brief': 'Create Google Compute Engine groups',
    'DESCRIPTION': """\
        *{command}* creates Google Compute Engine groups.
        """,
    'EXAMPLES': """\
        To create a group, run:

          $ {command} example-group
        """,
}
