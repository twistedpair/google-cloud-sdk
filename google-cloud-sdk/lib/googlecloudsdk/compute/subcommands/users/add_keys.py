# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for adding public keys to users."""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions

from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import file_utils
from googlecloudsdk.shared.compute import gaia_utils
from googlecloudsdk.shared.compute import time_utils
from googlecloudsdk.shared.compute import user_utils


class AddKeys(base_classes.NoOutputAsyncMutator):
  """Add public keys to a Google Compute Engine user.

  *{command}* adds public keys to a Google Compute Engine user.
  """

  @staticmethod
  def Args(parser):
    user_utils.AddUserArgument(parser, '', custom_help=(
        'If provided, the name of the user to add a public key to. '
        'Else, the default user will be used.'))

    parser.add_argument(
        '--public-key-files',
        required=True,
        type=arg_parsers.ArgList(min_length=1),
        action=arg_parsers.FloatingListValuesCatcher(),
        metavar='LOCAL_FILE_PATH',
        help='The path to a public-key file.')

    parser.add_argument(
        '--description',
        help='A description of the public keys')

    expiration = parser.add_argument(
        '--expire',
        help='How long until the public keys expire, e.g. 7d for 7 days',
        type=arg_parsers.Duration())
    expiration.detailed_help = """\
        Public keys can be configured to expire after a specified amount
        of time. For example, specifying ``12h'' will cause the key to expire
        after 12 hours. Valid units for this flag are ``s'' for seconds, ``m''
        for minutes, ``h'' for hours, and ''d'' for days.
        """

  @property
  def service(self):
    return self.clouduseraccounts.users

  @property
  def method(self):
    return 'AddPublicKey'

  @property
  def resource_type(self):
    return 'users'

  @property
  def messages(self):
    return self.clouduseraccounts.MESSAGES_MODULE

  def CreateRequests(self, args):

    name = args.name
    if not name:
      name = gaia_utils.GetDefaultAccountName(self.http)

    user_ref = self.CreateAccountsReference(
        name, resource_type='users')

    valid_key_types = [
        'ssh-rsa', 'ssh-dss', 'ecdsa-sha2-nistp256', 'ssh-ed25519']

    public_keys = []
    for key_file in args.public_key_files:
      key_text = file_utils.ReadFile(key_file, 'public-key')

      if key_text.split(' ', 1)[0] not in valid_key_types:
        raise exceptions.ToolException(
            'You must specify a public key file that contains a key of a '
            'supported form. Supported forms are {0}.'
            .format(', '.join(valid_key_types))
        )
      public_keys.append(key_text)

    formatted_expiration = time_utils.CalculateExpiration(args.expire)

    requests = []
    for key in public_keys:
      public_key_message = self.messages.PublicKey(
          description=args.description,
          expirationTimestamp=formatted_expiration,
          key=key)

      request = self.messages.ClouduseraccountsUsersAddPublicKeyRequest(
          project=self.project,
          publicKey=public_key_message,
          user=user_ref.Name())
      requests.append(request)

    return requests

AddKeys.detailed_help = {
    'EXAMPLES': """\
        To add a public key to a user, run:

          $ {command} example-user --public-key-files ~/.ssh/pubkey.pub

        Multiple public keys can be specified by providing multiple paths
        to key files on the local machine.
        """,
}
