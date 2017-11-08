# Copyright 2017 Google Inc. All Rights Reserved.
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
"""A library containing flags used by Cloud Pub/Sub commands."""
from googlecloudsdk.api_lib.pubsub import subscriptions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.pubsub import util


# Maximum number of attributes you can specify for a message.
MAX_ATTRIBUTES = 100


def AddSubscriptionResourceArg(parser, action, plural=False):
  if plural:
    nargs = '+'
    help_text = 'One or more subscriptions {}'
  else:
    nargs = None
    help_text = 'Name of the subscription {}'
  parser.add_argument('subscription', nargs=nargs,
                      help=help_text.format(action))


def AddTopicResourceArg(parser, action, plural=False):
  if plural:
    nargs = '+'
    help_text = 'One or more topics {}'
  else:
    nargs = None
    help_text = 'Name of the topic {}'
  parser.add_argument('topic', nargs=nargs,
                      help=help_text.format(action))


def AddAckIdFlag(parser, action):
  help_text = 'One or more ACK_ID to {}'.format(action)
  parser.add_argument('ack_id', nargs='+', help=help_text)


def AddIamPolicyFileFlag(parser):
  parser.add_argument('policy_file',
                      help='JSON or YAML file with the IAM policy')


def AddSeekFlags(parser):
  """Adds flags for the seek command to the parser."""
  seek_to_group = parser.add_mutually_exclusive_group(required=True)
  seek_to_group.add_argument(
      '--time', type=arg_parsers.Datetime.Parse,
      help="""\
          The time to seek to. Messages in the subscription that
          were published before this time are marked as acknowledged, and
          messages retained in the subscription that were published after
          this time are marked as unacknowledged. See `gcloud topic
          datetimes` for information on time formats.""")
  seek_to_group.add_argument(
      '--snapshot',
      help='The name of the snapshot. The snapshot\'s topic must be the same '
           'as that of the subscription.')
  parser.add_argument(
      '--snapshot-project',
      help="""\
          The name of the project the snapshot belongs to (if seeking to
          a snapshot). If not set, it defaults to the currently selected
          cloud project.""")


def AddPullFlags(parser):
  parser.add_argument(
      '--max-messages', type=int, default=1,
      help='The maximum number of messages that Cloud Pub/Sub can return '
           'in this response.')
  parser.add_argument(
      '--auto-ack', action='store_true', default=False,
      help='Automatically ACK every message pulled from this subscription.')


def AddPushEndpointFlag(parser, required=False):
  parser.add_argument(
      '--push-endpoint', required=required,
      help='A URL to use as the endpoint for this subscription. This will '
           'also automatically set the subscription type to PUSH.')


def AddAckDeadlineFlag(parser, required=False):
  parser.add_argument(
      '--ack-deadline', type=int, required=required,
      help='The number of seconds the system will wait for a subscriber to '
           'acknowledge receiving a message before re-attempting delivery.')


def AddSubscriptionTopicResourceFlags(parser):
  """Adds --topic and --topic-project flags to a parser."""
  parser.add_argument(
      '--topic', required=True,
      help='The name of the topic from which this subscription is receiving '
           'messages. Each subscription is attached to a single topic.')
  parser.add_argument(
      '--topic-project',
      help='The name of the project the provided topic belongs to. '
           'If not set, it defaults to the currently selected cloud project.')


def ParseRetentionDurationWithDefault(value):
  if value == subscriptions.DEFAULT_MESSAGE_RETENTION_VALUE:
    return value
  return util.FormatDuration(arg_parsers.Duration()(value))


def AddSubscriptionSettingsFlags(parser, track, is_update=False):
  AddAckDeadlineFlag(parser)
  AddPushEndpointFlag(parser)
  if track == base.ReleaseTrack.ALPHA:
    if not is_update:
      retention_parser = arg_parsers.Duration()
      retention_default_help = ('The default value is 7 days, the minimum is '
                                '10 minutes, and the maximum is 7 days.')
    else:
      retention_parser = ParseRetentionDurationWithDefault
      retention_default_help = 'Specify "default" to use the default value.'
    retention_parser = retention_parser or arg_parsers.Duration()
    parser.add_argument(
        '--retain-acked-messages',
        action='store_true',
        default=None,
        help="""\
            Whether or not to retain acknowledged messages.  If true,
            messages are not expunged from the subscription's backlog
            until they fall out of the --message-retention-duration
            window.""")
    parser.add_argument(
        '--message-retention-duration',
        type=retention_parser,
        help="""\
            How long to retain unacknowledged messages in the
            subscription's backlog, from the moment a message is
            published.  If --retain-acked-messages is true, this also
            configures the retention of acknowledged messages.  {}
            Valid values are strings of the form INTEGER[UNIT],
            where UNIT is one of "s", "m", "h", and "d" for seconds,
            seconds, minutes, hours, and days, respectively.  If the unit
            is omitted, seconds is assumed.""".format(retention_default_help))


def AddPublishMessageFlags(parser):
  parser.add_argument(
      'message_body', nargs='?', default=None,
      help="""\
          The body of the message to publish to the given topic name.
          Information on message formatting and size limits can be found at:
          https://cloud.google.com/pubsub/docs/publisher#publish""")
  parser.add_argument(
      '--attribute', type=arg_parsers.ArgDict(max_length=MAX_ATTRIBUTES),
      help='Comma-separated list of attributes. Each ATTRIBUTE has the form '
           'name=value". You can specify up to {0} attributes.'.format(
               MAX_ATTRIBUTES))

