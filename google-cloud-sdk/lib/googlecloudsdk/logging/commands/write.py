# Copyright 2014 Google Inc. All Rights Reserved.

"""'logging write' command."""

import datetime

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base import py as apitools_base

from googlecloudsdk.logging.lib import util


class Write(base.Command):
  """Writes a log entry."""

  SEVERITY_ENUM = ('DEFAULT', 'DEBUG', 'INFO', 'NOTICE', 'WARNING',
                   'ERROR', 'CRITICAL', 'ALERT', 'EMERGENCY')

  PAYLOAD_TYPE = ('text', 'struct')

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'log_name', help=('The name of the log where the log entry will '
                          'be written.'))
    parser.add_argument(
        'message', help=('The message to put in the log entry. It can be '
                         'JSON if you include --payload-type=struct.'))
    parser.add_argument(
        '--payload-type', help='Type of the log entry message: (text|struct).',
        choices=Write.PAYLOAD_TYPE, default='text')
    parser.add_argument(
        '--severity', required=False,
        help=('Severity level of the log entry: '
              '(DEFAULT|DEBUG|INFO|NOTICE|WARNING|ERROR|CRITICAL|'
              'ALERT|EMERGENCY).'),
        choices=Write.SEVERITY_ENUM, default='DEFAULT')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.
    """
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    project = properties.VALUES.core.project.Get(required=True)

    severity_value = getattr(messages.LogEntryMetadata.SeverityValueValuesEnum,
                             args.severity.upper())

    labels = messages.LogEntryMetadata.LabelsValue()
    labels.additionalProperties = [
        messages.LogEntryMetadata.LabelsValue.AdditionalProperty(
            key='compute.googleapis.com/resource_type',
            value='instance'),
        messages.LogEntryMetadata.LabelsValue.AdditionalProperty(
            key='compute.googleapis.com/resource_id',
            value='sent with gcloud'),
    ]
    # Cloud Logging uses RFC 3339 time format.
    rfc3339_format = '%Y-%m-%dT%H:%M:%SZ'
    meta = messages.LogEntryMetadata(
        timestamp=datetime.datetime.utcnow().strftime(rfc3339_format),
        severity=severity_value,
        serviceName='compute.googleapis.com',
        labels=labels)
    entry = messages.LogEntry(metadata=meta)

    if args.payload_type == 'struct':
      json_object = util.ConvertToJsonObject(args.message)
      struct = messages.LogEntry.StructPayloadValue()
      struct.additionalProperties = [
          messages.LogEntry.StructPayloadValue.AdditionalProperty(
              key=json_property.key,
              value=json_property.value)
          for json_property in json_object.properties
      ]
      entry.structPayload = struct
    else:
      entry.textPayload = args.message

    request = messages.WriteLogEntriesRequest(entries=[entry])
    try:
      unused_result = client.projects_logs_entries.Write(
          messages.LoggingProjectsLogsEntriesWriteRequest(
              projectsId=project, logsId=args.log_name,
              writeLogEntriesRequest=request))
      log.status.write('Created log entry.\n')
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))


Write.detailed_help = {
    'DESCRIPTION': """\
        {index}
        If the destination log does not exist, it will be created.
        All log entries written with this command are considered to be from
        the "compute.googleapis.com" log service (Google Compute Engine).
        The log entries will be listed in the Logs Viewer under that service.
    """,
    'EXAMPLES': """\
        To create a log entry in a given log, run:

          $ {command} LOG_NAME "A simple entry"

        To create a high severity log entry, run:

          $ {command} LOG_NAME "Urgent message" --severity=alert

        To create a structured log, run:

          $ {command} LOG_NAME '{"key": "value"}' --payload-type=struct
    """,
}
