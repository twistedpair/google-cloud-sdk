# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for describing groups."""
from googlecloudsdk.api_lib.compute import base_classes


class Describe(base_classes.BaseAsyncMutator):
  """Describe a Google Compute Engine group.

  *{command}* displays all data associated with a Google Compute
  Engine group in a project.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'name',
        metavar='NAME',
        help='The name of the group to describe.')

  @property
  def service(self):
    return self.clouduseraccounts.groups

  @property
  def method(self):
    return 'Get'

  @property
  def resource_type(self):
    return 'groups'

  @property
  def messages(self):
    return self.clouduseraccounts.MESSAGES_MODULE

  def CreateRequests(self, args):
    """Returns a list of requests necessary for describing groups."""

    group_ref = self.CreateAccountsReference(
        args.name, resource_type='groups')

    request = self.messages.ClouduseraccountsGroupsGetRequest(
        project=self.project,
        groupName=group_ref.Name())

    return [request]


Describe.detailed_help = {
    'EXAMPLES': """\
        To describe a user, run:

          $ {command} example-user
        """,
}
