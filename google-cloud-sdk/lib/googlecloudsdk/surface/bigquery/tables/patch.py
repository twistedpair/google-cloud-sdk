# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud bigquery tables patch.
"""

from googlecloudsdk.api_lib.bigquery import bigquery
from googlecloudsdk.api_lib.bigquery import bigquery_schemas
from googlecloudsdk.api_lib.bigquery import message_conversions
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.surface import bigquery as commands
from googlecloudsdk.third_party.apitools.base.py import exceptions


class TablesPatch(base.Command):
  """Updates one or more attributes of a table or view.

  The attributes that may be updated are the description, expiration time,
  friendly name, and schema. A schema may be updated only for a table,
  not a view. The new schema is specified by exactly one of the --schema or
  --schema-file flags.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--description', help='Description of the table or view.')
    parser.add_argument(
        '--expiration',
        type=int,
        help='Expiration time, in seconds from now, of a table or view.')
    parser.add_argument(
        '--friendly-name', help='Friendly name of the table.')

    schema_group = parser.add_mutually_exclusive_group()
    schema_group.add_argument(
        '--schema',
        help='A comma-separated list of entries of the form name[:type], '
        'where type defaults to string if not present, specifying field names '
        'and types in the new schema for the table. Possible types are string, '
        'integer, float, boolean, record, and timestamp. ')
    schema_group.add_argument(
        '--schema-file',
        help='The name of a JSON file containing a single array object, each '
        'element of which is an object with properties name, type, and, '
        'optionally, mode, specifying a new schema for the table. '
        'Possible types are string, integer, float, boolean, record, and '
        'timestamp.  Possible modes are NULLABLE, REQUIRED, and REPEATED.')

    parser.add_argument(
        'table_or_view',
        help='The table or view whose attributes are to be updated.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespeace, All the arguments that were provided to this
        command invocation.

    Returns:
      Some value that we want to have printed later.
    """
    apitools_client = self.context[commands.APITOOLS_CLIENT_KEY]
    bigquery_messages = self.context[commands.BIGQUERY_MESSAGES_MODULE_KEY]
    resource_parser = self.context[commands.BIGQUERY_REGISTRY_KEY]
    resource = resource_parser.Parse(
        args.table_or_view, collection='bigquery.tables')
    reference = message_conversions.TableResourceToReference(
        bigquery_messages, resource)

    if args.expiration:
      expiration_instant_in_millis = int(
          (bigquery.CurrentTimeInSec() + args.expiration) * 1000)
    else:
      expiration_instant_in_millis = None

    if args.schema:
      new_schema = bigquery_schemas.ReadSchema(args.schema, bigquery_messages)
    elif args.schema_file:
      new_schema = bigquery_schemas.ReadSchemaFile(
          args.schema_file, bigquery_messages)
    else:
      new_schema = None

    request = bigquery_messages.BigqueryTablesPatchRequest(
        projectId=reference.projectId,
        datasetId=reference.datasetId,
        tableId=reference.tableId,
        table=bigquery_messages.Table(
            tableReference=reference,
            description=args.description,
            expirationTime=expiration_instant_in_millis,
            friendlyName=args.friendly_name,
            schema=new_schema))

    try:
      apitools_client.tables.Patch(request)
    except exceptions.HttpError as e:
      raise bigquery.Error.ForHttpError(e)
    log.UpdatedResource(reference)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    pass
