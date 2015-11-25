# Copyright 2015 Google Inc. All Rights Reserved.

"""The `app instances list` command."""

from googlecloudsdk.api_lib.app import instances_util
from googlecloudsdk.calliope import base


# pylint: disable=invalid-name
AppEngineInstance = instances_util.AppEngineInstance


class List(base.Command):
  """List the instances affiliated with the current App Engine project."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To list all App Engine instances, run:

              $ {command}

          To list all App Engine instances for a given service, run:

              $ {command} -s myservice

          To list all App Engine instances for a given version, run:

              $ {command} -v v1
          """,
  }

  @staticmethod
  def Collection(args):
    return 'app.instances'

  @staticmethod
  def Args(parser):
    parser.add_argument('--service', '-s',
                        help=('If specified, only list instances belonging to '
                              'the given service.'))
    parser.add_argument('--version', '-v',
                        help=('If specified, only list instances belonging to '
                              'the given version.'))

  def Run(self, args):
    # `--user-output-enabled=false` needed to prevent Display method from
    # consuming returned generator, and also to prevent this command from
    # causing confusing output
    all_instances = self.cli.Execute(['compute', 'instances', 'list',
                                      '--user-output-enabled', 'false'])
    app_engine_instances = []
    for instance in all_instances:
      if AppEngineInstance.IsInstance(instance):
        gae_instance = AppEngineInstance.FromComputeEngineInstance(instance)
        app_engine_instances.append(gae_instance)
    return instances_util.FilterInstances(app_engine_instances, args.service,
                                          args.version)
