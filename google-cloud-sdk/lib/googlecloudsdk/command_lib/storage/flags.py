# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Generic flags that apply to multiple commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers


REQUIRED_INVENTORY_REPORTS_METADATA_FIELDS = ('project', 'bucket', 'name')
OPTIONAL_INVENTORY_REPORTS_METADATA_FIELDS = (
    'location', 'size', 'timeCreated', 'type',
    'updated', 'storageClass', 'etag', 'retentionExpirationTime', 'crc32c',
    'md5Hash', 'generation', 'metageneration', 'contentType',
    'contentEncoding', 'timeStorageClassUpdated')


def add_predefined_acl_flag(parser):
  """Adds predefined ACL flag shared for both buckets and objects."""
  parser.add_argument(
      '-a',
      '--predefined-acl',
      '--canned-acl',
      help='Applies predefined, or "canned," ACLs to a resource. See'
      ' docs for a list of predefined ACL constants: https://cloud.google.com'
      '/storage/docs/access-control/lists#predefined-acl')


def add_object_acl_setter_flags(parser):
  """Adds flags common among commands that modify object ACLs."""
  acl_flags_group = parser.add_group(mutex=True)
  acl_flags_group.add_argument(
      '--preserve-acl',
      '-p',
      action=arg_parsers.StoreTrueFalseAction,
      help='Preserves ACLs when copying in the cloud. This option is Google'
      ' Cloud Storage-only, and you need OWNER access to all copied objects.'
      ' If all objects in the destination bucket should have the same ACL,'
      ' you can also set a default object ACL on that bucket instead of using'
      ' this flag.\nPreserving ACLs is the default behavior for updating'
      ' existing objects.')
  add_predefined_acl_flag(acl_flags_group)


def add_predefined_default_object_acl_flag(parser):
  """Adds predefined default ACL flag shared for buckets."""
  parser.add_argument(
      '--predefined-default-object-acl',
      help='Apply a predefined set of default object access controls to'
      'buckets',
      hidden=True)


def add_precondition_flags(parser):
  """Add flags indicating a precondition for an operation to happen."""
  preconditions_group = parser.add_group(
      category='PRECONDITION',
  )
  preconditions_group.add_argument(
      '--if-generation-match',
      metavar='GENERATION',
      help='Execute only if the generation matches the generation of the'
      ' requested object.')
  preconditions_group.add_argument(
      '--if-metageneration-match',
      metavar='METAGENERATION',
      help='Execute only if the metageneration matches the metageneration of'
      ' the requested object.')


def add_object_metadata_flags(parser, allow_patch=False):
  """Add flags that allow setting object metadata."""
  metadata_group = parser.add_group(category='OBJECT METADATA')
  metadata_group.add_argument(
      '--cache-control',
      help='How caches should handle requests and responses.')
  metadata_group.add_argument(
      '--content-disposition',
      help='How content should be displayed.')
  metadata_group.add_argument(
      '--content-encoding', help='How content is encoded (e.g. ``gzip\'\').')
  metadata_group.add_argument(
      '--content-md5',
      metavar='MD5_DIGEST',
      help=('Manually specified MD5 hash digest for the contents of an uploaded'
            ' file. This flag cannot be used when uploading multiple files. The'
            ' custom digest is used by the cloud provider for validation.'))
  metadata_group.add_argument(
      '--content-language',
      help='Content\'s language (e.g. ``en\'\' signifies "English").')
  metadata_group.add_argument(
      '--content-type',
      help='Type of data contained in the object (e.g. ``text/html\'\').')
  metadata_group.add_argument(
      '--custom-time',
      type=arg_parsers.Datetime.Parse,
      help='Custom time for Google Cloud Storage objects in RFC 3339 format.')

  # TODO(b/238631069): Refactor to make use of command_lib/util/args/map_util.py
  custom_metadata_group = metadata_group.add_mutually_exclusive_group()
  custom_metadata_group.add_argument(
      '--custom-metadata',
      metavar='CUSTOM_METADATA_KEYS_AND_VALUES',
      type=arg_parsers.ArgDict(),
      help=(
          'Sets custom metadata on objects. When used with `--preserve-posix`,'
          ' POSIX attributes are also stored in custom metadata.'))

  custom_metadata_group.add_argument(
      '--clear-custom-metadata',
      action='store_true',
      help=(
          'Clears all custom metadata on objects. When used with'
          ' `--preserve-posix`, POSIX attributes will still be stored in custom'
          ' metadata.'))

  update_custom_metadata_group = custom_metadata_group.add_group(
      help=(
          'Flags that preserve unspecified existing metadata cannot be used'
          ' with `--custom-metadata` or `--clear-custom-metadata`, but can be'
          ' specified together:'))
  update_custom_metadata_group.add_argument(
      '--update-custom-metadata',
      metavar='CUSTOM_METADATA_KEYS_AND_VALUES',
      type=arg_parsers.ArgDict(),
      help=(
          'Adds or sets individual custom metadata key value pairs on objects.'
          ' Existing custom metadata not specified with this flag is not'
          ' changed. This flag can be used with `--remove-custom-metadata`.'
          ' When keys overlap with those provided by `--preserve-posix`, values'
          ' specified by this flag are used.'))
  update_custom_metadata_group.add_argument(
      '--remove-custom-metadata',
      metavar='METADATA_KEYS',
      type=arg_parsers.ArgList(),
      help=(
          'Removes individual custom metadata keys from objects. This flag can'
          ' be used with `--update-custom-metadata`. When used with'
          ' `--preserve-posix`, POSIX attributes specified by this flag are not'
          ' preserved.'))

  if allow_patch:
    metadata_group.add_argument(
        '--clear-cache-control',
        action='store_true',
        help='Clears object cache control.')
    metadata_group.add_argument(
        '--clear-content-disposition',
        action='store_true',
        help='Clears object content disposition.')
    metadata_group.add_argument(
        '--clear-content-encoding',
        action='store_true',
        help='Clears content encoding.')
    metadata_group.add_argument(
        '--clear-content-md5',
        action='store_true',
        help='Clears object content MD5.')
    metadata_group.add_argument(
        '--clear-content-language',
        action='store_true',
        help='Clears object content language.')
    metadata_group.add_argument(
        '--clear-content-type',
        action='store_true',
        help='Clears object content type.')
    metadata_group.add_argument(
        '--clear-custom-time',
        action='store_true',
        help='Clears object custom time.')


def add_encryption_flags(parser,
                         allow_patch=False,
                         command_only_reads_data=False,
                         hidden=False):
  """Adds flags for encryption and decryption keys.

  Args:
    parser (parser_arguments.ArgumentInterceptor): Parser passed to surface.
    allow_patch (bool): Adds flags relevant for update operations if true.
    command_only_reads_data (bool): Should be set to true if a command only
        reads data from storage providers (e.g. cat, ls) and false for commands
        that also write data (e.g. cp, rewrite). Hides flags that pertain to
        write operations for read-only commands.
    hidden (bool): Hides encryption flags if true.
  """
  encryption_group = parser.add_group(category='ENCRYPTION', hidden=hidden)
  encryption_group.add_argument(
      '--encryption-key',
      # Flag is hidden for read-only commands and not omitted for parity
      # reasons: gsutil allows supplying decryption keys through the encryption
      # key boto config option, so keeping encryption flags for read-only
      # commands eases translation.
      hidden=hidden or command_only_reads_data,
      help=(
          'The encryption key to use for encrypting target objects. The'
          ' specified encryption key can be a customer-supplied encryption key'
          ' (An RFC 4648 section 4 base64-encoded AES256 string), or a'
          ' customer-managed encryption key of the form `projects/{project}/'
          'locations/{location}/keyRings/ {key-ring}/cryptoKeys/{crypto-key}`.'
          ' The specified key also acts as a decryption key, which is useful'
          ' when copying or moving encryted data to a new location. Using this'
          ' flag in an `objects update` command triggers a rewrite of target'
          ' objects.'))
  encryption_group.add_argument(
      '--decryption-keys',
      type=arg_parsers.ArgList(),
      metavar='DECRYPTION_KEY',
      hidden=hidden,
      help=('A comma-separated list of customer-supplied encryption keys'
            ' (RFC 4648 section 4 base64-encoded AES256 strings) that will'
            ' be used to decrypt Google Cloud Storage objects. Data encrypted'
            ' with a customer-managed encryption key (CMEK) is decrypted'
            ' automatically, so CMEKs do not need to be listed here.'))
  if allow_patch:
    encryption_group.add_argument(
        '--clear-encryption-key',
        action='store_true',
        hidden=hidden or command_only_reads_data,
        help='Clears the encryption key associated with an object. Using this'
             ' flag triggers a rewrite of affected objects, which are then'
             ' encrypted using the default encryption key set on the bucket,'
             ' if one exists, or else with a Google-managed encryption key.')


def add_continue_on_error_flag(parser):
  """Adds flag to indicate error should be skipped instead of being raised."""
  parser.add_argument(
      '-c',
      '--continue-on-error',
      action='store_true',
      help='If any operations are unsuccessful, the command will exit with'
      ' a non-zero exit status after completing the remaining operations.'
      ' This flag takes effect only in sequential execution mode (i.e.'
      ' processor and thread count are set to 1). Parallelism is default.')


def _get_optional_help_text(require_create_flags, flag_name):
  """Returns a text to be added for create command's help text."""
  optional_text_map = {
      'destination': ' Defaults to <SOURCE_BUCKET_URL>/inventory_reports/.',
      'metadata_fields': ' Defaults to all fields being included.',
      'start_date': ' Defaults to tomorrow.',
      'end_date': ' Defaults to one year from --schedule-starts value.',
      'frequency': ' Defaults to DAILY.'
  }
  return optional_text_map[flag_name] if require_create_flags else ''


def add_inventory_reports_metadata_fields_flag(parser,
                                               require_create_flags=False):
  """Adds the metadata-fields flag."""
  parser.add_argument(
      '--metadata-fields',
      metavar='METADATA_FIELDS',
      default=(list(OPTIONAL_INVENTORY_REPORTS_METADATA_FIELDS)
               if require_create_flags else None),
      type=arg_parsers.ArgList(
          choices=OPTIONAL_INVENTORY_REPORTS_METADATA_FIELDS),
      help=(
          'The metadata fields to be included in the inventory '
          'report. The required fields: "{}" get added automatically. '.format(
              ', '.join(REQUIRED_INVENTORY_REPORTS_METADATA_FIELDS)) +
          _get_optional_help_text(require_create_flags, 'metadata_fields')))


def add_inventory_reports_flags(parser, require_create_flags=False):
  """Adds the flags for the inventory reports create and update commands.

  Args:
    parser (parser_arguments.ArgumentInterceptor): Parser passed to surface.
    require_create_flags (bool): True if create flags should be required.
  """
  parser.add_argument(
      '--csv-separator',
      choices=[r'\n', r'\r\n'],
      type=str,
      metavar='SEPARATOR',
      help='Sets the character used to separate the records in the inventory '
            'report CSV file. For example, ``\\n``')
  parser.add_argument(
      '--csv-delimiter',
      type=str,
      metavar='DELIMITER',
      help='Sets the delimiter that separates the fields in the inventory '
            'report CSV file. For example, ``,``')
  parser.add_argument(
      '--csv-header',
      action=arg_parsers.StoreTrueFalseAction,
      help='Indicates whether or not headers are included in the inventory '
            'report CSV file. Default is None.')
  parser.add_argument(
      '--destination',
      type=str,
      metavar='DESTINATION_URL',
      help=('Sets the URL of the destination bucket and path where generated '
            'reports are stored.' +
            _get_optional_help_text(require_create_flags, 'destination')))
  parser.add_argument(
      '--display-name',
      type=str,
      help='Sets the editable name of the report configuration.')
  parser.add_argument(
      '--schedule-starts',
      type=arg_parsers.Day.Parse,
      metavar='START_DATE',
      help=('Sets the date you want to start generating inventory reports. '
            'For example, 2022-01-30. Should be tomorrow or later based'
            ' on UTC timezone.' +
            _get_optional_help_text(require_create_flags, 'start_date')))
  parser.add_argument(
      '--schedule-repeats',
      choices=['daily', 'weekly'],
      metavar='FREQUENCY',
      default='daily' if require_create_flags else None,
      type=str,
      help=('Sets how often the inventory report configuration will run.' +
            _get_optional_help_text(require_create_flags, 'frequency')))
  parser.add_argument(
      '--schedule-repeats-until',
      type=arg_parsers.Day.Parse,
      metavar='END_DATE',
      help=(
          'Sets date after which you want to stop generating inventory reports. '
          'For example, 2022-03-30.' +
          _get_optional_help_text(require_create_flags, 'end_date')))
  if require_create_flags:
    add_inventory_reports_metadata_fields_flag(parser, require_create_flags)
