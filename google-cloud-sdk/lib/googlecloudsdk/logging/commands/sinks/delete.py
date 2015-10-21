# Copyright 2014 Google Inc. All Rights Reserved.

"""'logging sinks delete' command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.third_party.apitools.base import py as apitools_base

from googlecloudsdk.logging.lib import util


class Delete(base.Command):
  """Deletes a sink."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('sink_name', help='The name of the sink to delete.')

  def DeleteLogSink(self):
    """Deletes a log sink specified by the arguments."""
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    sink_ref = self.context['sink_reference']
    return client.projects_logs_sinks.Delete(
        messages.LoggingProjectsLogsSinksDeleteRequest(
            projectsId=sink_ref.projectsId, logsId=sink_ref.logsId,
            sinksId=sink_ref.sinksId))

  def DeleteLogServiceSink(self):
    """Deletes a log service sink specified by the arguments."""
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    sink_ref = self.context['sink_reference']
    return client.projects_logServices_sinks.Delete(
        messages.LoggingProjectsLogServicesSinksDeleteRequest(
            projectsId=sink_ref.projectsId,
            logServicesId=sink_ref.logServicesId, sinksId=sink_ref.sinksId))

  def DeleteProjectSink(self):
    """Deletes a project sink specified by the arguments."""
    client = self.context['logging_client']
    messages = self.context['logging_messages']
    sink_ref = self.context['sink_reference']
    return client.projects_sinks.Delete(
        messages.LoggingProjectsSinksDeleteRequest(
            projectsId=sink_ref.projectsId, sinksId=sink_ref.sinksId))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.
    """
    sink_ref = self.context['sink_reference']

    if args.log:
      sink_description = 'log sink [%s] from [%s]' % (
          sink_ref.sinksId, sink_ref.logsId)
    elif args.service:
      sink_description = 'log-service sink [%s] from [%s]' % (
          sink_ref.sinksId, sink_ref.logServicesId)
    else:
      sink_description = 'project sink [%s]' % sink_ref.sinksId

    if not console_io.PromptContinue('Really delete %s?' % sink_description):
      raise exceptions.ToolException('action canceled by user')

    try:
      if args.log:
        self.DeleteLogSink()
      elif args.service:
        self.DeleteLogServiceSink()
      else:
        self.DeleteProjectSink()
      log.DeletedResource(sink_ref)
    except apitools_base.HttpError as error:
      project_sink = not args.log and not args.service
      # Suggest the user to add --log or --log-service flag.
      if project_sink and error.status_code == 404:
        log.Print(('Project sink was not found. '
                   'Did you forget to add --log or --log-service flag?'))
      raise exceptions.HttpException(util.GetError(error))


Delete.detailed_help = {
    'DESCRIPTION': """\
        Deletes a sink and halts the export of log entries associated
        with that sink.
        If you don't include one of the *--log* or *--log-service* flags,
        this command deletes a project sink.
        Deleting a sink does not affect log entries already exported
        through the deleted sink, and will not affect other sinks that are
        exporting the same log(s).
     """,
}
