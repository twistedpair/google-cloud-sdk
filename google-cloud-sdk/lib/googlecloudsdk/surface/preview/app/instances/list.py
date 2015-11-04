# Copyright 2015 Google Inc. All Rights Reserved.

"""The `app instances list` command."""

from googlecloudsdk.api_lib.app import instances_util
from googlecloudsdk.calliope import base


# pylint: disable=invalid-name
AppEngineInstance = instances_util.AppEngineInstance


def _FilterInstances(instances, service=None, version=None):
  """Filter a list of App Engine instances.

  Args:
    instances: list of AppEngineInstance, all App Engine instances
    service: str, the name of the service to filter by or None to match all
      services
    version: str, the name of the version to filter by or None to match all
      versions

  Returns:
    instances matching the given filters
  """
  matching_instances = []
  for instance in instances:
    if ((not service or instance.service == service) and
        (not version or instance.version == version)):
      matching_instances.append(instance)
  return matching_instances


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
    return _FilterInstances(app_engine_instances, args.service, args.version)
