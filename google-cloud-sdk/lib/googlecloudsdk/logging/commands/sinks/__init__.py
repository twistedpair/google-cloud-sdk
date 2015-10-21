# Copyright 2014 Google Inc. All Rights Reserved.

"""Cloud logging logs group."""

from googlecloudsdk.calliope import base


class Sinks(base.Group):
  """Manages sinks used to export logs."""

  @staticmethod
  def Args(parser):
    """Add log name and log service name flags, used by sinks subcommands."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--log',
                       help=('The name of a log. Use this argument only '
                             'if the sink applies to a single log.'))
    group.add_argument('--log-service', dest='service',
                       help=('The name of a log service. Use this argument '
                             'only if the sink applies to all logs from '
                             'a log service.'))

  def Filter(self, context, args):
    """Modify the context that will be given to this group's commands when run.

    Args:
      context: The current context.
      args: The argparse namespace given to the corresponding .Run() invocation.

    Returns:
      Updated context, with sink reference added based on args.
    """
    if 'sink_name' not in args:
      return context

    if args.log:
      collection = 'logging.projects.logs.sinks'
      params = {'logsId': args.log}
    elif args.service:
      collection = 'logging.projects.logServices.sinks'
      params = {'logServicesId': args.service}
    else:
      collection = 'logging.projects.sinks'
      params = {}

    context['sink_reference'] = context['logging_resources'].Parse(
        args.sink_name, params=params, collection=collection)
    return context
