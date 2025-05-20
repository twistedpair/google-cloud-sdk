# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the Datastream related commands."""


from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


def AddTypeFlag(parser):
  """Adds a --type flag to the given parser."""
  help_text = """Type can be MYSQL, ORACLE, POSTGRESQL, GOOGLE-CLOUD-STORAGE or BIGQUERY"""

  parser.add_argument('--type', help=help_text, required=True)


def AddDisplayNameFlag(parser, required=True):
  """Adds a --display-name flag to the given parser."""
  help_text = """Friendly name for the connection profile."""
  parser.add_argument('--display-name', help=help_text, required=required)


def AddMysqlProfileGroup(parser, required=True):
  """Adds necessary mysql profile flags to the given parser."""
  mysql_profile = parser.add_group()
  mysql_profile.add_argument(
      '--mysql-hostname',
      help="""IP or hostname of the MySQL source database.""",
      required=required)
  mysql_profile.add_argument(
      '--mysql-port',
      help="""Network port of the MySQL source database.""",
      required=required,
      type=int)
  mysql_profile.add_argument(
      '--mysql-username',
      help="""Username Datastream will use to connect to the database.""",
      required=required)
  password_group = mysql_profile.add_group(required=required, mutex=True)
  password_group.add_argument(
      '--mysql-password',
      help="""\
          Password for the user that Datastream will be using to
          connect to the database.
          This field is not returned on request, and the value is encrypted
          when stored in Datastream.""",
      default='')
  password_group.add_argument(
      '--mysql-prompt-for-password',
      action='store_true',
      help='Prompt for the password used to connect to the database.')
  password_group.add_argument(
      '--mysql-secret-manager-stored-password',
      help=(
          'Path to secret manager, storing the password for the user used to'
          ' connect to the database.'
      ),
      default='',
  )
  ssl_config = mysql_profile.add_group()
  ssl_config.add_argument(
      '--ca-certificate',
      help="""\
          x509 PEM-encoded certificate of the CA that signed the source database
          server's certificate. The replica will use this certificate to verify
          it's connecting to the right host.""",
      required=required)
  ssl_config.add_argument(
      '--client-certificate',
      help="""\
          x509 PEM-encoded certificate that will be used by the replica to
          authenticate against the source database server.""",
      required=required)
  ssl_config.add_argument(
      '--client-key',
      help="""\
          Unencrypted PKCS#1 or PKCS#8 PEM-encoded private key associated with
          the Client Certificate.""",
      required=required)


def AddOracleProfileGroup(parser, required=True):
  """Adds necessary oracle profile flags to the given parser."""
  oracle_profile = parser.add_group()
  oracle_profile.add_argument(
      '--oracle-hostname',
      help="""IP or hostname of the oracle source database.""",
      required=required)
  oracle_profile.add_argument(
      '--oracle-port',
      help="""Network port of the oracle source database.""",
      required=required,
      type=int)
  oracle_profile.add_argument(
      '--oracle-username',
      help="""Username Datastream will use to connect to the database.""",
      required=required)
  oracle_profile.add_argument(
      '--database-service',
      help="""Database service for the Oracle connection.""",
      required=required)
  password_group = oracle_profile.add_group(required=required, mutex=True)
  password_group.add_argument(
      '--oracle-password',
      help="""\
          Password for the user that Datastream will be using to
          connect to the database.
          This field is not returned on request, and the value is encrypted
          when stored in Datastream.""",
      default='')
  password_group.add_argument(
      '--oracle-prompt-for-password',
      action='store_true',
      help='Prompt for the password used to connect to the database.')
  password_group.add_argument(
      '--oracle-secret-manager-stored-password',
      help=(
          'Path to secret manager, storing the password for the user used to'
          ' connect to the database.'
      ),
      default='',
  )


def AddPostgresqlProfileGroup(parser, required=True):
  """Adds necessary postgresql profile flags to the given parser."""
  postgresql_profile = parser.add_group()
  postgresql_profile.add_argument(
      '--postgresql-hostname',
      help="""IP or hostname of the PostgreSQL source database.""",
      required=required)
  postgresql_profile.add_argument(
      '--postgresql-port',
      help="""Network port of the PostgreSQL source database.""",
      required=required,
      type=int)
  postgresql_profile.add_argument(
      '--postgresql-username',
      help="""Username Datastream will use to connect to the database.""",
      required=required)
  postgresql_profile.add_argument(
      '--postgresql-database',
      help="""Database service for the PostgreSQL connection.""",
      required=required)
  password_group = postgresql_profile.add_group(required=required, mutex=True)
  password_group.add_argument(
      '--postgresql-password',
      help="""\
          Password for the user that Datastream will be using to
          connect to the database.
          This field is not returned on request, and the value is encrypted
          when stored in Datastream.""",
      default='')
  password_group.add_argument(
      '--postgresql-prompt-for-password',
      action='store_true',
      help='Prompt for the password used to connect to the database.')
  password_group.add_argument(
      '--postgresql-secret-manager-stored-password',
      help=(
          'Path to secret manager, storing the password for the user used to'
          ' connect to the database.'
      ),
      default='',
  )

  ssl_config = postgresql_profile.add_group()
  ssl_config.add_argument(
      '--postgresql-ca-certificate',
      help="""\
          x509 PEM-encoded certificate of the CA that signed the source database
          server's certificate. The replica will use this certificate to verify
          it's connecting to the right host.""",
      required=required)

  client_ssl_config = ssl_config.add_group()
  client_ssl_config.add_argument(
      '--postgresql-client-certificate',
      help="""\
          x509 PEM-encoded certificate that will be used by the replica to
          authenticate against the source database server.""",
      required=required)
  client_ssl_config.add_argument(
      '--postgresql-client-key',
      help="""\
          Unencrypted PKCS#1 or PKCS#8 PEM-encoded private key associated with
          the Client Certificate.""",
      required=required)


def AddSqlServerProfileGroup(parser, required=True):
  """Adds necessary sqlserver profile flags to the given parser."""
  sqlserver_profile = parser.add_group()
  sqlserver_profile.add_argument(
      '--sqlserver-hostname',
      help="""IP or hostname of the SQL Server source database.""",
      required=required,
  )
  sqlserver_profile.add_argument(
      '--sqlserver-port',
      help="""Network port of the SQL Server source database.""",
      required=required,
      type=int,
  )
  sqlserver_profile.add_argument(
      '--sqlserver-username',
      help="""Username Datastream will use to connect to the database.""",
      required=required,
  )
  sqlserver_profile.add_argument(
      '--sqlserver-database',
      help="""Database service for the SQL Server connection.""",
      required=required,
  )
  password_group = sqlserver_profile.add_group(required=required, mutex=True)
  password_group.add_argument(
      '--sqlserver-password',
      help="""\
          Password for the user that Datastream will be using to
          connect to the database.
          This field is not returned on request, and the value is encrypted
          when stored in Datastream.""",
      default='',
  )
  password_group.add_argument(
      '--sqlserver-prompt-for-password',
      action='store_true',
      help='Prompt for the password used to connect to the database.',
  )
  password_group.add_argument(
      '--sqlserver-secret-manager-stored-password',
      help=(
          'Path to secret manager, storing the password for the user used to'
          ' connect to the database.'
      ),
      default='',
  )


def AddSalesforceProfileGroup(parser, required=True):
  """Adds necessary salesforce profile flags to the given parser.

  Args:
    parser: The parser for the command line flags.
    required: Whether or not the flags are required.
  """
  salesforce_profile = parser.add_group()
  salesforce_profile.add_argument(
      '--salesforce-domain',
      help="""Domain of the Salesforce organization. For example, 'myorg.my.salesforce.com'""",
      required=required,
  )

  login_group = salesforce_profile.add_group(required=required, mutex=True)

  user_login_group = login_group.add_group()
  user_login_group.add_argument(
      '--salesforce-username',
      help="""Username Datastream will use to connect to the database.""",
      required=required,
  )

  password_group = user_login_group.add_group(required=required, mutex=True)
  password_group.add_argument(
      '--salesforce-password',
      help="""\
          Password for the user that Datastream will be using to
          connect to Salesforce.
          This field is not returned on request, and the value is encrypted
          when stored in Datastream.""",
      default='',
  )
  password_group.add_argument(
      '--salesforce-prompt-for-password',
      action='store_true',
      help='Prompt for the password used to connect to Salesforce.',
  )
  password_group.add_argument(
      '--salesforce-secret-manager-stored-password',
      help=(
          'Path to secret manager, storing the password for the user used to'
          ' connect to Salesforce.'
      ),
      default='',
  )

  security_token_group = user_login_group.add_group(
      required=required, mutex=True
  )
  security_token_group.add_argument(
      '--salesforce-security-token',
      help="""\
          Security token for the user that Datastream will be using to
          connect to Salesforce.""",
      default='',
  )
  security_token_group.add_argument(
      '--salesforce-prompt-for-security-token',
      action='store_true',
      help='Prompt for the security token used to connect to Salesforce.',
  )
  security_token_group.add_argument(
      '--salesforce-secret-manager-stored-security-token',
      help=(
          'Path to secret manager, storing the security token used to connect'
          ' to Salesforce.'
      ),
      default='',
  )

  oauth2_login_group = login_group.add_group()
  oauth2_login_group.add_argument(
      '--salesforce-oauth2-client-id',
      help="""OAuth 2.0 Client ID used to connect to Salesforce.""",
      required=required,
  )
  client_secret_group = oauth2_login_group.add_group(
      required=required, mutex=True
  )

  client_secret_group.add_argument(
      '--salesforce-oauth2-client-secret',
      help="""\
          OAuth 2.0 Client secret used to connect to Salesforce.""",
      default='',
  )
  client_secret_group.add_argument(
      '--salesforce-prompt-for-oauth2-client-secret',
      action='store_true',
      help=(
          'Prompt for the OAuth 2.0 Client secret used to connect to'
          ' Salesforce.'
      ),
  )
  client_secret_group.add_argument(
      '--salesforce-secret-manager-stored-oauth2-client-secret',
      help=(
          'Path to secret manager, storing the OAuth 2.0 Client secret used to'
          ' connect to Salesforce.'
      ),
      default='',
  )


def AddGcsProfileGroup(parser, release_track, required=True):
  """Adds necessary GCS profile flags to the given parser."""
  gcs_profile = parser.add_group()

  bucket_field_name = '--bucket'
  if release_track == base.ReleaseTrack.BETA:
    bucket_field_name = '--bucket-name'

  gcs_profile.add_argument(
      bucket_field_name,
      help="""The full project and resource path for Cloud Storage
      bucket including the name.""",
      required=required)

  gcs_profile.add_argument(
      '--root-path',
      help="""The root path inside the Cloud Storage bucket.""",
      required=False)


def AddMongodbProfileGroup(parser, required=True):
  """Adds necessary mongodb profile flags to the given parser."""
  mongodb_profile = parser.add_group()
  mongodb_profile.add_argument(
      '--mongodb-host-addresses',
      help="""IP or hostname and port of the MongoDB source database.""",
      type=arg_parsers.ArgList(min_length=1),
      metavar='IPv4_ADDRESS_OR_HOSTNAME:PORT',
      required=required,
  )
  mongodb_profile.add_argument(
      '--mongodb-replica-set',
      help="""Replica set of the MongoDB source database.""",
  )
  mongodb_profile.add_argument(
      '--mongodb-username',
      help="""Username Datastream will use to connect to the database.""",
      required=required,
  )
  password_group = mongodb_profile.add_group(required=required, mutex=True)
  password_group.add_argument(
      '--mongodb-password',
      help="""\
          Password for the user that Datastream will be using to
          connect to the database.
          This field is not returned on request, and the value is encrypted
          when stored in Datastream.""",
      default='',
  )
  password_group.add_argument(
      '--mongodb-prompt-for-password',
      action='store_true',
      help='Prompt for the password used to connect to the database.',
  )
  password_group.add_argument(
      '--mongodb-secret-manager-stored-password',
      help=(
          'Path to secret manager, storing the password for the user used to'
          ' connect to the database.'
      ),
      default='',
  )
  connection_format_group = mongodb_profile.add_group(
      required=required, mutex=True
  )
  connection_format_group.add_argument(
      '--mongodb-srv-connection-format',
      help="""SRV Connection format for the MongoDB source database.""",
      action='store_true',
      default=False,
  )
  connection_format_group.add_argument(
      '--mongodb-standard-connection-format',
      help="""Standard connection format for the MongoDB source database.""",
      action='store_true',
      default=False,
  )
  mongodb_profile.add_argument(
      '--mongodb-direct-connection',
      help="""Connect to the mongodb hosts directly and do not try to resolve
      any of the replicas from the replica set.""",
      action='store_true',
      default=False,
  )


def AddDepthGroup(parser):
  """Adds necessary depth flags for discover command parser."""
  depth_parser = parser.add_group(mutex=True)
  depth_parser.add_argument(
      '--recursive',
      help="""Whether to retrieve the full hierarchy of data objects (TRUE) or only the current level (FALSE).""",
      action=actions.DeprecationAction(
          '--recursive',
          warn=(
              'The {flag_name} option is deprecated; use `--full-hierarchy`'
              ' instead.'
          ),
          removed=False,
          action='store_true',
      ),
  )
  depth_parser.add_argument(
      '--recursive-depth',
      help="""The number of hierarchy levels below the current level to be retrieved.""",
      action=actions.DeprecationAction(
          '--recursive-depth',
          warn=(
              'The {flag_name} option is deprecated; use `--hierarchy-depth`'
              ' instead.'
          ),
          removed=False,
      ),
  )


def AddHierarchyGroup(parser):
  """Adds necessary hierarchy flags for discover command parser."""
  hierarchy_parser = parser.add_group(mutex=True)
  hierarchy_parser.add_argument(
      '--full-hierarchy',
      help="""Whether to retrieve the full hierarchy of data objects (TRUE) or only the current level (FALSE).""",
      action='store_true',
  )

  hierarchy_parser.add_argument(
      '--hierarchy-depth',
      help="""The number of hierarchy levels below the current level to be retrieved.""",
  )


def AddRdbmsGroup(parser):
  """Adds necessary RDBMS params for discover command parser."""
  rdbms_parser = parser.add_group(mutex=True)
  rdbms_parser.add_argument(
      '--mysql-rdbms-file',
      help="""Path to a YAML (or JSON) file containing the MySQL RDBMS to enrich with child data objects and metadata. If you pass - as the value of the flag the file content will be read from stdin. """
  )
  rdbms_parser.add_argument(
      '--oracle-rdbms-file',
      help="""Path to a YAML (or JSON) file containing the Oracle RDBMS to enrich with child data objects and metadata. If you pass - as the value of the flag the file content will be read from stdin."""
  )
  rdbms_parser.add_argument(
      '--postgresql-rdbms-file',
      help="""Path to a YAML (or JSON) file containing the PostgreSQL RDBMS to enrich with child data objects and metadata. If you pass - as the value of the flag the file content will be read from stdin."""
  )
  rdbms_parser.add_argument(
      '--sqlserver-rdbms-file',
      help="""Path to a YAML (or JSON) file containing the SQL Server RDBMS to enrich with child data objects and metadata. If you pass - as the value of the flag the file content will be read from stdin.""",
  )


def AddValidationGroup(parser, verb):
  """Adds a --force flag to the given parser."""
  validation_group = parser.add_group(mutex=True)
  validation_group.add_argument(
      '--force',
      help="""%s the connection profile without validating it.""" % verb,
      action='store_true',
      default=False)
