# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery tables create.
"""

import time
from googlecloudsdk.api_lib.bigquery import bigquery
from googlecloudsdk.api_lib.bigquery import bigquery_client_helper
from googlecloudsdk.api_lib.bigquery import bigquery_schemas
from googlecloudsdk.api_lib.bigquery import message_conversions
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.surface import bigquery as commands
from googlecloudsdk.third_party.apitools.base.py import exceptions


class TablesCreate(base.Command):
  """Creates a table or view with a specified name.

  A view is a collection of rows selected by a query in a flag, and manipulated
  as a table. The dataset to contain the table or view must already exist, and
  must not contain a table or view with the specified name.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--description',
        help='Description of the table or view.')
    parser.add_argument(
        '--expiration',
        type=int,
        help='Expiration time of the table or view being created, in seconds '
        'from now.')
    parser.add_argument(
        '--if-exists',
        choices=['fail', 'skip'],
        default='fail',
        help='What to do if the table to be created already exists in the '
        'dataset.')

    schema_group = parser.add_mutually_exclusive_group()
    schema_group.add_argument(
        '--schema',
        help='A comma-separated list of entries of the form name[:type], '
        'where type defaults to string if not present, specifying field names '
        'and types for the table being created. Possible types are string, '
        'integer, float, boolean, record, and timestamp. ')
    schema_group.add_argument(
        '--schema-file',
        help='he name of a JSON file containing a single array object, each '
        'element of which is an object with properties name, type, and, '
        'optionally, mode, specifying a schema for the table being created.')

    parser.add_argument(
        '--view',
        help='Create a view with this SQL query. (If this flag is not '
        'specified, a table is created.)')
    parser.add_argument(
        'table', help='Specification of the table or view to be created')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Raises:
      bigquery.DuplicateError: if table already exists.
    Returns:
      None
    """
    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    resource_parser = self.context[commands.BIGQUERY_REGISTRY_KEY]
    resource = resource_parser.Parse(args.table, collection='bigquery.tables')
    reference = message_conversions.TableResourceToReference(
        bigquery_messages, resource)

    table_or_view = 'View' if args.view else 'Table'
    if bigquery_client_helper.TableExists(
        apitools_client, bigquery_messages, reference):
      if args.if_exists == 'skip':
        log.status.Print(
            'Skipping this operation because a table or view named '
            '[{0}] already exists.'.format(reference))
        return
      else:
        message = (
            '{0} [{1}] could not be created; a table with this name '
            'already exists.'.format(table_or_view, reference))
        raise bigquery.DuplicateError(message, None, [])
    if args.schema:
      schema = bigquery_schemas.ReadSchema(args.schema, bigquery_messages)
    elif args.schema_file:
      schema = bigquery_schemas.ReadSchemaFile(
          args.schema_file, bigquery_messages)
    else:
      schema = None

    if args.expiration:
      expiration_instant_seconds = time.time() + args.expiration
      expiration_instant_millis = int(1000 * expiration_instant_seconds)
    else:
      expiration_instant_millis = None

    if args.view:
      view_definition = bigquery_messages.ViewDefinition(query=args.view)
    else:
      view_definition = None

    request = bigquery_messages.BigqueryTablesInsertRequest(
        projectId=reference.projectId,
        datasetId=reference.datasetId,
        table=bigquery_messages.Table(
            tableReference=bigquery_messages.TableReference(
                projectId=reference.projectId,
                datasetId=reference.datasetId,
                tableId=reference.tableId),
            description=args.description,
            expirationTime=expiration_instant_millis,
            schema=schema,
            view=view_definition))

    try:
      apitools_client.tables.Insert(request)
    except exceptions.HttpError as server_error:
      raise bigquery.Error.ForHttpError(server_error)

    log.CreatedResource(resource)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    pass
